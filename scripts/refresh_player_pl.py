"""合并 player_pl 来源：用已采集的 7 天数据更新快照，重写数据文件。"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from epg_tool.models import Programme, read_jsonl, write_jsonl
from epg_tool.xmltv import write_xmltv

DATA = ROOT / "data"
SNAPSHOT = DATA / "current_week.jsonl"
STATUS = DATA / "status.json"
PLAYER_PL_DATA = Path("/tmp/player_pl_7d.json")


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
    # 1. 读取已采集的 player_pl 数据
    raw = json.loads(PLAYER_PL_DATA.read_text(encoding="utf-8"))
    retrieved_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    fresh = [
        Programme(
            provider="player_pl",
            country="PL",
            timezone="Europe/Warsaw",
            channel_id=r["channel_id"],
            channel_number=r["channel_id"],
            channel_name=r["channel_name"],
            title=r["title"],
            start_at=r["start_at"],
            end_at=r["end_at"],
            source_url="https://player.pl/",
            retrieved_at=retrieved_at,
        )
        for r in raw
    ]
    print(f"Player.pl fresh records: {len(fresh)}", flush=True)
    channels = sorted({(r.channel_id, r.channel_name) for r in fresh})
    print(f"Player.pl channels: {len(channels)}", flush=True)
    for cid, name in channels:
        print(f"  {cid}: {name}", flush=True)

    # 2. 与现有快照合并：替换全部 player_pl 记录
    previous_rows = read_jsonl(SNAPSHOT)
    previous = [dict_to_programme(r) for r in previous_rows]
    kept = [r for r in previous if r.provider != "player_pl"]

    records = kept + fresh

    # 3. 写数据文件
    count = write_jsonl(records, SNAPSHOT)
    channel_count, programme_count = write_xmltv(records, DATA / "epg.xml", DATA / "epg.xml.gz")

    # 4. 更新 status.json：只动 player_pl 与 xmltv
    status = json.loads(STATUS.read_text(encoding="utf-8"))
    status["player_pl"] = {"status": "ok", "records": len(fresh)}
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
    sys.exit(main())
