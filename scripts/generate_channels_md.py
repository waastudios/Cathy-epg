"""Regenerate CHANNELS.md and CHANNELS-CN.md from the currently published data/epg.xml.

Every row mirrors an actual XMLTV <channel> node. Channels are sorted by
tvg-id numerically within each section; section order is unchanged. Run after
a full collect:
    python scripts/generate_channels_md.py
"""
from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
XML_PATH = ROOT / "data" / "epg.xml"

HEADER_EN = """# Published channel list

This inventory is generated directly from the currently published `data/epg.xml`. Every row is an actual XMLTV `<channel>` node: **tvg-id** is `channel/@id` and **tvg-name** is `display-name`.

The current XMLTV output contains **{count} channels**.

> **Note:** `(T)` means **Translated**. The channel's schedule originates in a non-English market and programme titles are translated into English before publication. This marker appears **only in this inventory**; it is never written to `data/epg.xml`, `data/epg.xml.gz`, or the programme snapshot. XMLTV `display-name` values remain the official provider names.
"""

HEADER_CN = """# 已发布频道清单

本清单直接由当前发布的 `data/epg.xml` 生成。每一行均为实际 XMLTV `<channel>` 节点：**tvg-id** 对应 `channel/@id`，**tvg-name** 对应 `display-name`。

当前 XMLTV 输出包含 **{count} 个频道**。

> **注：**频道名称后的 **`(T)`** 表示 **Translated**：该频道的节目表来自非英语地区，原始节目标题已转换为英文后发布。此标记**仅用于本清单展示**，绝不会写入 `data/epg.xml`、`data/epg.xml.gz` 或节目快照；XMLTV 的官方 `display-name` 保持不变。
"""

# tvg-id prefix -> (english section title, chinese section title, translated marker)
SECTIONS: list[tuple[str, str, str, bool]] = [
    ("astro.", "Astro Malaysia", "🇲🇾马来西亚 Astro", False),
    ("now_hk.", "now TV Hong Kong", "🇭🇰香港 now TV", False),
    ("sky_de.", "Sky Germany", "🇩🇪德国 Sky Sport", True),
    ("ee_uk.", "Sky Sports", "🇬🇧英国体育类频道", False),  # refined below into sports / entertainment
    ("virgin_uk.", "Virgin Media UK", "🇬🇧英国Virgin Media", False),
    ("canal+.fr", "France Canal+", "🇫🇷法国 Canal+", True),
    ("foot+.fr", "France Canal+", "🇫🇷法国 Canal+", True),
    ("eurosport.", "🇷🇸 Serbia SBB", "🇷🇸塞尔维亚 SBB", True),
    ("travelxp.eu", "🇷🇸 Serbia SBB", "🇷🇸塞尔维亚 SBB", True),
    ("digi4k_ro", "Digi 4K", "🇷🇴罗马尼亚 Digi 4K", True),
    ("allente_se.", "Allente Sweden", "🇸🇪瑞典 Allente", True),
    ("allente_no.", "Allente Norway", "🇳🇴挪威 Allente", True),
    ("eurosport1.pl", "🇵🇱 Poland Player.pl", "🇵🇱波兰 Player.pl", True),
    ("eurosport2.pl", "🇵🇱 Poland Player.pl", "🇵🇱波兰 Player.pl", True),
    ("eurosport3.pl", "🇵🇱 Poland Player.pl", "🇵🇱波兰 Player.pl", True),
    ("eurosport4.pl", "🇵🇱 Poland Player.pl", "🇵🇱波兰 Player.pl", True),
    ("ElevenSp.1", "🇵🇱 Poland Player.pl", "🇵🇱波兰 Player.pl", True),
]

# ee_uk channel numbers that belong to the "Sky Sports" section; the rest go
# to "Sky Entertainment" / "🇬🇧英国综合类频道".
EE_SKY_SPORTS_NUMBERS = {
    "408", "409", "410", "411", "418", "419", "420", "421", "422", "423",
    "424", "425", "426", "427", "428", "429", "433", "450", "451", "452",
    "453", "454", "455", "494",
}
EE_SPORTS_EN = "Sky Sports"
EE_SPORTS_CN = "🇬🇧英国体育类频道"
EE_ENT_EN = "Sky Entertainment"
EE_ENT_CN = "🇬🇧英国综合类频道"

# Section order is fixed; "Other" (unmatched) goes last.
SECTION_ORDER_EN = [
    "Astro Malaysia", "now TV Hong Kong", "Sky Germany", "Sky Sports",
    "Virgin Media UK", "Sky Entertainment", "France Canal+",
    "🇷🇸 Serbia SBB", "Digi 4K", "🇵🇱 Poland Player.pl",
    "Allente Sweden", "Allente Norway", "Other",
]
CN_TITLE = {
    "Astro Malaysia": "🇲🇾马来西亚 Astro",
    "now TV Hong Kong": "🇭🇰香港 now TV",
    "Sky Germany": "🇩🇪德国 Sky Sport",
    "Sky Sports": "🇬🇧英国体育类频道",
    "Virgin Media UK": "🇬🇧英国Virgin Media",
    "Sky Entertainment": "🇬🇧英国综合类频道",
    "France Canal+": "🇫🇷法国 Canal+",
    "🇷🇸 Serbia SBB": "🇷🇸塞尔维亚 SBB",
    "Digi 4K": "🇷🇴罗马尼亚 Digi 4K",
    "Allente Sweden": "🇸🇪瑞典 Allente",
    "Allente Norway": "🇳🇴挪威 Allente",
    "🇵🇱 Poland Player.pl": "🇵🇱波兰 Player.pl",
    "Other": "其他",
}


def sort_key(channel_id: str) -> tuple[int, int, str]:
    """Sort tvg-ids numerically by their suffix; non-numeric suffixes sort after."""
    suffix = channel_id.split(".", 1)[1] if "." in channel_id else ""
    try:
        return (0, int(suffix), "")
    except ValueError:
        return (1, 0, suffix.lower())


def main() -> None:
    root = ET.parse(XML_PATH).getroot()
    channels: list[tuple[str, str]] = []
    for node in root.findall("channel"):
        channel_id = node.get("id") or ""
        name_node = node.find("display-name")
        name = (name_node.text or "").strip() if name_node is not None else ""
        if channel_id:
            channels.append((channel_id, name))

    groups: dict[str, list[tuple[str, str, bool]]] = {}

    def add_row(section: str, channel_id: str, name: str, translated: bool) -> None:
        groups.setdefault(section, []).append((channel_id, name, translated))

    for channel_id, name in channels:
        matched = False
        for prefix, section_en, _section_cn, translated in SECTIONS:
            if channel_id == prefix or channel_id.startswith(prefix):
                if prefix == "ee_uk.":
                    number = channel_id.split(".", 1)[1]
                    section = EE_SPORTS_EN if number in EE_SKY_SPORTS_NUMBERS else EE_ENT_EN
                    add_row(section, channel_id, name, False)
                else:
                    add_row(section_en, channel_id, name, translated)
                matched = True
                break
        if not matched:
            add_row("Other", channel_id, name, False)

    for rows in groups.values():
        rows.sort(key=lambda item: sort_key(item[0]))

    def render(header: str, order: list[str], title_map: dict[str, str]) -> str:
        lines = [header.format(count=len(channels)).rstrip(), ""]
        for section in order:
            if section not in groups:
                continue
            lines.append(f"## {title_map.get(section, section)}")
            lines.append("")
            lines.append("| tvg-id | tvg-name |")
            lines.append("| --- | --- |")
            for channel_id, name, translated in groups[section]:
                marker = " (T)" if translated else ""
                lines.append(f"| `{channel_id}` | {name}{marker} |")
            lines.append("")
        return "\n".join(lines)

    en_path = ROOT / "CHANNELS.md"
    cn_path = ROOT / "CHANNELS-CN.md"
    en_path.write_text(render(HEADER_EN, SECTION_ORDER_EN, {}), encoding="utf-8")
    # 中文版沿用英文分组键的顺序，仅标题经 CN_TITLE 映射为中文。
    cn_path.write_text(render(HEADER_CN, SECTION_ORDER_EN, CN_TITLE), encoding="utf-8")
    print(f"Wrote {en_path.name} and {cn_path.name}: {len(channels)} channels, {len(groups)} sections")


if __name__ == "__main__":
    main()
