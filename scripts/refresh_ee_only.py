"""只刷新 ee_uk 来源：用修复后的代码重新采集 7 天，与现有快照合并后重写数据文件。"""
from __future__ import annotations

import json
import sys
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from epg_tool.models import Programme, read_jsonl, write_jsonl
from epg_tool.sources import collect_ee_uk_channels, drain_notes, note
from epg_tool.xmltv import write_xmltv

DATA = ROOT / "data"
SNAPSHOT = DATA / "current_week.jsonl"
STATUS = DATA / "status.json"


def dict_to_programme(row: dict) -> Programme:
    return Programme(
        provider=row["provider"],
        country=row["country"],
        timezone=row["timezone"],
        channel_id=row["channel_id"],
        channel_number=row["channel_number"],
        channel_name=row["channel_name"],
        title=row["title"],
        start_at=row["start_at"],
        end_at=row.get("end_at"),
        source_url=row["source_url"],
        retrieved_at=row["retrieved_at"],
        image_url=row.get("image_url"),
        image_source_url=row.get("image_source_url"),
    )


def main() -> int:
    days = int(sys.argv[1]) if len(sys.argv) > 1 else 7

    # 1. 用修复后的代码重新采集 EE
    fresh = collect_ee_uk_channels(days)
    notes = drain_notes()
    print(f"EE fresh records: {len(fresh)}", flush=True)
    channels = sorted({(r.channel_number, r.channel_name) for r in fresh})
    print(f"EE channels: {len(channels)}", flush=True)
    for num, name in channels:
        print(f"  {num}: {name}", flush=True)

    # 2. 与现有快照合并：替换全部 ee_uk 记录
    previous_rows = read_jsonl(SNAPSHOT)
    previous = [dict_to_programme(r) for r in previous_rows]
    kept = [r for r in previous if r.provider != "ee_uk"]

    # 3. 保留未变化节目的图片链接（与 cli.py 逻辑一致）
    previous_images = {
        (r.provider, r.channel_id, r.start_at, r.title): (r.image_url, r.image_source_url)
        for r in previous
        if r.provider == "ee_uk" and r.image_url
    }
    if previous_images:
        fresh = [
            replace(
                r,
                image_url=previous_images[(r.provider, r.channel_id, r.start_at, r.title)][0],
                image_source_url=previous_images[(r.provider, r.channel_id, r.start_at, r.title)][1],
            )
            if not r.image_url and (r.provider, r.channel_id, r.start_at, r.title) in previous_images
            else r
            for r in fresh
        ]

    records = kept + fresh

    # 4. 写数据文件
    count = write_jsonl(records, SNAPSHOT)
    channel_count, programme_count = write_xmltv(records, DATA / "epg.xml", DATA / "epg.xml.gz")

    # 5. 更新 status.json：只动 ee_uk 与 xmltv
    status = json.loads(STATUS.read_text(encoding="utf-8"))
    entry: dict = {"status": "ok", "records": len(fresh)}
    if notes:
        entry["notes"] = notes
    status["ee_uk"] = entry
    status["xmltv"] = {
        "status": "ok",
        "channels": channel_count,
        "programmes": programme_count,
        "xml_file": str(DATA / "epg.xml"),
        "gzip_file": str(DATA / "epg.xml.gz"),
    }
    status["generated_at"] = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    status["total_records"] = count
    STATUS.write_text(json.dumps(status, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(json.dumps(status["ee_uk"], ensure_ascii=False, indent=2), flush=True)
    print(f"total: {count} records, {channel_count} channels", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
