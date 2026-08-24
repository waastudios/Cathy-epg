"""将统一节目表记录导出为 XMLTV 与 gzip 压缩文件。"""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime
import gzip
from pathlib import Path
import xml.etree.ElementTree as ET
from typing import Iterable

from .models import Programme


def _xmltv_channel_id(record: Programme) -> str:
    """构造稳定且跨来源不冲突的 XMLTV 频道标识。"""
    return f"{record.provider}.{record.channel_number}"


def _xmltv_timestamp(value: str) -> str:
    """把 ISO 8601 含时区时间转换为 XMLTV 的时间格式。"""
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        raise ValueError(f"XMLTV 时间必须带时区：{value}")
    return parsed.strftime("%Y%m%d%H%M%S %z")


def write_xmltv(records: Iterable[Programme], xml_path: Path, gzip_path: Path) -> tuple[int, int]:
    """写入 XMLTV 与 gzip 文件，返回频道数和节目数。"""
    programmes = sorted(
        records,
        key=lambda item: (item.provider, item.channel_number, item.start_at, item.end_at, item.title),
    )
    channels: dict[str, list[Programme]] = defaultdict(list)
    for programme in programmes:
        channels[_xmltv_channel_id(programme)].append(programme)

    root = ET.Element("tv", {"generator-info-name": "official-epg-search", "generator-info-url": "https://github.com/waastudios/official-epg-search"})
    for channel_id in sorted(channels):
        first = channels[channel_id][0]
        channel = ET.SubElement(root, "channel", {"id": channel_id})
        ET.SubElement(channel, "display-name").text = first.channel_name
        ET.SubElement(channel, "display-name").text = f"CH {first.channel_number}"
        ET.SubElement(channel, "url").text = first.source_url

    for programme in programmes:
        item = ET.SubElement(
            root,
            "programme",
            {
                "start": _xmltv_timestamp(programme.start_at),
                "stop": _xmltv_timestamp(programme.end_at),
                "channel": _xmltv_channel_id(programme),
            },
        )
        ET.SubElement(item, "title").text = programme.title
        ET.SubElement(item, "url").text = programme.source_url

    tree = ET.ElementTree(root)
    ET.indent(tree, space="  ")
    xml_path.parent.mkdir(parents=True, exist_ok=True)
    tree.write(xml_path, encoding="utf-8", xml_declaration=True)
    with xml_path.open("rb") as source, gzip_path.open("wb") as destination:
        with gzip.GzipFile(filename="epg.xml", mode="wb", fileobj=destination, mtime=0) as compressed:
            while chunk := source.read(1024 * 1024):
                compressed.write(chunk)
    return len(channels), len(programmes)
