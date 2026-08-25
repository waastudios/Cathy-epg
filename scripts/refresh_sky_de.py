#!/usr/bin/env python3
"""只刷新 MagentaTV 官方 Sky Germany 记录，避免不必要地慢速重跑其他来源。"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path

from epg_tool.models import Programme, read_jsonl, write_jsonl
from epg_tool.sources import collect_magenta_tv_sky_de
from epg_tool.xmltv import write_xmltv


ROOT = Path(__file__).resolve().parents[1]
EXPECTED_SKY_NUMBERS = {str(number) for number in [201, 202, 203, 204, 205, 206, 207, 209, 210, *range(211, 221), *range(221, 231)]}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Refresh only the official MagentaTV Sky Germany XMLTV records")
    parser.add_argument("--days", type=int, default=7, choices=range(1, 8), metavar="1..7")
    parser.add_argument("--dataset", type=Path, default=ROOT / "data/current_week.jsonl")
    parser.add_argument("--status", type=Path, default=ROOT / "data/status.json")
    parser.add_argument("--xml", type=Path, default=ROOT / "data/epg.xml")
    parser.add_argument("--gzip", type=Path, default=ROOT / "data/epg.xml.gz")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    fresh_sky = collect_magenta_tv_sky_de(days=args.days)
    actual_numbers = {record.channel_number for record in fresh_sky}
    if actual_numbers != EXPECTED_SKY_NUMBERS:
        raise RuntimeError(
            "Sky Germany 官方数据未覆盖预期频道号："
            f"missing={sorted(EXPECTED_SKY_NUMBERS - actual_numbers, key=int)}, "
            f"extra={sorted(actual_numbers - EXPECTED_SKY_NUMBERS, key=int)}"
        )
    if any(record.channel_name.endswith(" HD") for record in fresh_sky):
        raise RuntimeError("Sky Germany 导出频道名错误地保留了末尾 HD。")

    retained = [Programme(**row) for row in read_jsonl(args.dataset) if row.get("provider") != "sky_de"]
    merged = retained + fresh_sky
    record_count = write_jsonl(merged, args.dataset)
    channel_count, programme_count = write_xmltv(merged, args.xml, args.gzip)

    status: dict[str, object] = {}
    if args.status.exists():
        loaded = json.loads(args.status.read_text(encoding="utf-8"))
        if isinstance(loaded, dict):
            status = loaded
    status["sky_de"] = {"status": "ok", "records": len(fresh_sky)}
    status["xmltv"] = {
        "status": "ok",
        "channels": channel_count,
        "programmes": programme_count,
        "xml_file": str(args.xml.relative_to(ROOT) if args.xml.is_relative_to(ROOT) else args.xml),
        "gzip_file": str(args.gzip.relative_to(ROOT) if args.gzip.is_relative_to(ROOT) else args.gzip),
    }
    status["generated_at"] = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    status["total_records"] = record_count
    args.status.parent.mkdir(parents=True, exist_ok=True)
    args.status.write_text(json.dumps(status, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(
        json.dumps(
            {
                "sky_de_channels": len(actual_numbers),
                "sky_de_records": len(fresh_sky),
                "total_channels": channel_count,
                "total_records": record_count,
                "xmltv_programmes": programme_count,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
