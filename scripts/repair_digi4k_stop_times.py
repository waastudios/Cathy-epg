"""Repair legacy Digi 4K XMLTV records that were published without a stop time.

The repair uses only the subsequent published programme from the same official Digi 4K
source. If no later programme is available, the incomplete horizon-edge record is removed
instead of inventing a duration. The production collector now enforces the same invariant.
"""

from __future__ import annotations

import json
from dataclasses import replace
from datetime import datetime
from pathlib import Path

from epg_tool.models import Programme, read_jsonl, write_jsonl
from epg_tool.xmltv import write_xmltv

DATA = Path("data/current_week.jsonl")
STATUS = Path("data/status.json")
XML = Path("data/epg.xml")
GZIP = Path("data/epg.xml.gz")
PROVIDER = "digi4k_ro"


def parse(value: str) -> datetime:
    return datetime.fromisoformat(value)


def main() -> None:
    programmes = [Programme(**row) for row in read_jsonl(DATA)]
    digi = sorted((item for item in programmes if item.provider == PROVIDER), key=lambda item: item.start_at)
    other = [item for item in programmes if item.provider != PROVIDER]
    repaired: list[Programme] = []
    filled = 0
    dropped = 0

    for index, item in enumerate(digi):
        if item.end_at:
            repaired.append(item)
            continue
        next_item = digi[index + 1] if index + 1 < len(digi) else None
        if next_item and parse(next_item.start_at) > parse(item.start_at):
            repaired.append(replace(item, end_at=next_item.start_at))
            filled += 1
        else:
            dropped += 1

    records = other + repaired
    if any(item.provider == PROVIDER and item.end_at is None for item in records):
        raise RuntimeError("Digi 4K repair invariant failed: a published record still lacks stop time")

    write_jsonl(records, DATA)
    channels, programmes_count = write_xmltv(records, XML, GZIP)
    status = json.loads(STATUS.read_text(encoding="utf-8"))
    status["digi4k_ro"]["records"] = len(repaired)
    status["xmltv"]["channels"] = channels
    status["xmltv"]["programmes"] = programmes_count
    status["total_records"] = programmes_count
    status["digi4k_ro"]["integrity_repair"] = {
        "filled_stop_times": filled,
        "dropped_horizon_edge_records": dropped,
        "rule": "only publish programmes with an official next-programme boundary",
    }
    STATUS.write_text(json.dumps(status, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"filled_stop_times={filled}")
    print(f"dropped_horizon_edge_records={dropped}")
    print(f"digi4k_records={len(repaired)}")
    print(f"xmltv_programmes={programmes_count}")


if __name__ == "__main__":
    main()
