"""合并 sbb_rs 来源：重新采集 7 天数据（含 Travel XP）更新快照，重写数据文件。"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from epg_tool.models import Programme, read_jsonl, write_jsonl
from epg_tool.sources import collect_sbb_eurosport
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
    # 1. 重新采集 SBB 7 天数据（含 Travel XP）
    fresh = collect_sbb_eurosport(days=7)
    print(f"SBB fresh records: {len(fresh)}", flush=True)
    channels = sorted({(r.channel_id, r.channel_name) for r in fresh})
    print(f"SBB channels: {len(channels)}", flush=True)
    for cid, name in channels:
        print(f"  {cid}: {name}", flush=True)

    # 2. 与现有快照合并：替换全部 sbb_rs 记录
    previous_rows = read_jsonl(SNAPSHOT)
    previous = [dict_to_programme(r) for r in previous_rows]
    kept = [r for r in previous if r.provider != "sbb_rs"]

    records = kept + fresh

    # 3. 写数据文件
    count = write_jsonl(records, SNAPSHOT)
    channel_count, programme_count = write_xmltv(records, DATA / "epg.xml", DATA / "epg.xml.gz")

    # 4. 更新 status.json：只动 sbb_rs 与 xmltv
    retrieved_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    status = json.loads(STATUS.read_text(encoding="utf-8"))
    status["sbb_rs"] = {"status": "ok", "records": len(fresh)}
    status["xmltv"] = {
        "status": "ok",
        "channels": channel_count,
        "programmes": programme_count,
        "xml_file": str(DATA / "epg.xml"),
        "gzip_file": str(DATA / "epg.xml.gz"),
    }
    status["generated_at"] = retrieved_at
    status["total_records"] = count
    STATUS.write_text(json.dumps(status, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"total: {count} records, {channel_count} channels", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
