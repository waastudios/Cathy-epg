"""Regenerate CHANNELS.md from the currently published data/epg.xml.

Every row mirrors an actual XMLTV <channel> node. Run after a full collect:
    python scripts/generate_channels_md.py
"""
from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
XML_PATH = ROOT / "data" / "epg.xml"
OUT_PATH = ROOT / "CHANNELS.md"

HEADER = """# Published channel list

This inventory is generated directly from the currently published `data/epg.xml`. Every row is an actual XMLTV `<channel>` node: **tvg-id** is `channel/@id` and **tvg-name** is `display-name`.

The current XMLTV output contains **{count} channels**.

> **Note:** `(T)` means **Translated**. The channel's schedule originates in a non-English market and programme titles are translated into English before publication. This marker appears **only in this inventory**; it is never written to `data/epg.xml`, `data/epg.xml.gz`, or the programme snapshot. XMLTV `display-name` values remain the official provider names.
"""

# tvg-id prefix -> (section title, translated marker)
SECTIONS: list[tuple[str, str, bool]] = [
    ("astro.", "Astro Malaysia", False),
    ("now_hk.", "now TV Hong Kong", False),
    ("sky_de.", "Sky Germany", True),
    ("ee_uk.", "Sky Sports", False),  # refined below into sports / entertainment
    ("virgin_uk.", "Virgin Media UK", False),
    ("eurosport.", "Serbia SBB Eurosport", True),
    ("digi4k_ro", "Digi 4K", True),
    ("allente_se.", "Allente Sweden", True),
    ("allente_no.", "Allente Norway", True),
]

# ee_uk channel numbers that belong to the "Sky Sports" section; the rest go
# to "Sky Entertainment".
EE_SKY_SPORTS_NUMBERS = {
    "408", "409", "410", "411", "418", "419", "420", "421", "422", "423",
    "424", "425", "426", "427", "428", "429", "433", "450", "451", "452",
    "453", "454", "455", "494",
}


def main() -> None:
    root = ET.parse(XML_PATH).getroot()
    channels: list[tuple[str, str]] = []
    for node in root.findall("channel"):
        channel_id = node.get("id") or ""
        name_node = node.find("display-name")
        name = (name_node.text or "").strip() if name_node is not None else ""
        if channel_id:
            channels.append((channel_id, name))
    channels.sort(key=lambda item: item[0])

    groups: dict[str, list[tuple[str, str, bool]]] = {}
    order: list[str] = []

    def add_row(section: str, channel_id: str, name: str, translated: bool) -> None:
        if section not in groups:
            groups[section] = []
            order.append(section)
        groups[section].append((channel_id, name, translated))

    for channel_id, name in channels:
        matched = False
        for prefix, section, translated in SECTIONS:
            if channel_id.startswith(prefix):
                if prefix == "ee_uk.":
                    number = channel_id.split(".", 1)[1]
                    if number in EE_SKY_SPORTS_NUMBERS:
                        add_row("Sky Sports", channel_id, name, False)
                    else:
                        add_row("Sky Entertainment", channel_id, name, False)
                elif prefix == "eurosport.":
                    add_row("🇷🇸 Serbia SBB Eurosport", channel_id, name, translated)
                else:
                    add_row(section, channel_id, name, translated)
                matched = True
                break
        if not matched:
            add_row("Other", channel_id, name, False)

    # Keep the historical section order: Sky Sports before Virgin, then
    # Sky Entertainment right after Virgin.
    preferred = [
        "Astro Malaysia", "now TV Hong Kong", "Sky Germany", "Sky Sports",
        "Virgin Media UK", "Sky Entertainment", "🇷🇸 Serbia SBB Eurosport",
        "Digi 4K", "Allente Sweden", "Allente Norway", "Other",
    ]
    order = [s for s in preferred if s in groups] + [s for s in order if s not in preferred]

    lines = [HEADER.format(count=len(channels)).rstrip(), ""]
    for section in order:
        lines.append(f"## {section}")
        lines.append("")
        lines.append("| tvg-id | tvg-name |")
        lines.append("| --- | --- |")
        for channel_id, name, translated in groups[section]:
            marker = " (T)" if translated else ""
            lines.append(f"| `{channel_id}` | {name}{marker} |")
        lines.append("")
    OUT_PATH.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote {OUT_PATH} with {len(channels)} channels in {len(order)} sections")


if __name__ == "__main__":
    main()
