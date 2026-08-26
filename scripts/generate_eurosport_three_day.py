from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
XML_PATH = ROOT / "data" / "epg.xml"
OUTPUT = ROOT / "EUROSPORT-3DAY.md"
ZONE = ZoneInfo("Asia/Shanghai")
CHANNEL_IDS = ("eurosport.1", "eurosport.2", "eurosport.4k")


def main() -> None:
    tree = ET.parse(XML_PATH)
    channel_names = {
        channel_id: (tree.findtext(f"./channel[@id='{channel_id}']/display-name") or channel_id)
        for channel_id in CHANNEL_IDS
    }
    if any(name == channel_id for channel_id, name in channel_names.items()):
        missing = [channel_id for channel_id, name in channel_names.items() if name == channel_id]
        raise RuntimeError(f"Missing Eurosport channel nodes in XMLTV: {missing}")

    today = datetime.now(ZONE).date()
    dates = [today + timedelta(days=offset) for offset in range(3)]
    programmes: dict[tuple[str, object], list[tuple[datetime, datetime, str]]] = {
        (channel_id, day): [] for channel_id in CHANNEL_IDS for day in dates
    }
    for item in tree.findall("./programme"):
        channel_id = item.get("channel") or ""
        if channel_id not in CHANNEL_IDS:
            continue
        start = datetime.strptime(item.attrib["start"], "%Y%m%d%H%M%S %z").astimezone(ZONE)
        stop = datetime.strptime(item.attrib["stop"], "%Y%m%d%H%M%S %z").astimezone(ZONE)
        if start.date() in dates:
            programmes[(channel_id, start.date())].append((start, stop, item.findtext("title") or ""))

    lines = [
        "# Eurosport three-day programme guide",
        "",
        "This guide is generated automatically each day from the current published `data/epg.xml`. Times are China Standard Time (UTC+8); programme titles are the published English XMLTV titles.",
        "",
        f"Coverage dates: **{dates[0].isoformat()}**, **{dates[1].isoformat()}**, **{dates[2].isoformat()}**.",
    ]
    for day in dates:
        lines.extend(["", f"## {day.isoformat()} (China Standard Time)"])
        for channel_id in CHANNEL_IDS:
            lines.extend(["", f"### {channel_names[channel_id]} — `{channel_id}`", "", "| Start | End | Programme title |", "| --- | --- | --- |"])
            rows = sorted(programmes[(channel_id, day)])
            if not rows:
                lines.append("| — | — | No published programme record for this date. |")
            else:
                for start, stop, title in rows:
                    lines.append(f"| {start:%H:%M} | {stop:%H:%M} | {title} |")
    lines.extend([
        "",
        "## Coverage note",
        "",
        "Eurosport 1 and Eurosport 2 use TV+ Türkiye’s normal public programme pages. When that official page exposes only its current-day schedule, later dates remain explicitly empty in this guide rather than being inferred. Eurosport 4K uses SBB’s public EPG and can publish its available future records.",
    ])
    OUTPUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print({"output": str(OUTPUT), "dates": [day.isoformat() for day in dates], "programmes": sum(len(rows) for rows in programmes.values())})


if __name__ == "__main__":
    main()
