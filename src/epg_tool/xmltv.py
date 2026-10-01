"""将统一节目表记录导出为 XMLTV 与 gzip 压缩文件。"""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime
import gzip
import html
from pathlib import Path
from zoneinfo import ZoneInfo
import xml.etree.ElementTree as ET
from typing import Iterable

from .models import Programme
from .richmeta import build_description, infer_category


# XMLTV 输出统一使用的时区：北京时间。NanoTV 经实测不解析时间中的时区偏移
# （按设备本地时间直接理解时间戳），因此所有来源的时间都转换为 +0800 输出，
# 保证"正在播出"与实际一致。对正确解析偏移的播放器而言，转换前后是同一时刻，无影响。
_XMLTV_OUTPUT_ZONE = ZoneInfo("Asia/Shanghai")


# 用户指定：TV+ Türkiye 的官方 Eurosport 频道号 77／106 使用跨来源稳定的
# XMLTV ID，而非默认的 ``tvplus_tr.<channel-number>`` 形式。
# （2026-09 起 TV+ 采集器已移除，Eurosport 1/2 改由 SBB Public EPG 提供；
# 此映射保留用于历史快照的 ID 兼容。）
_TVPLUS_EUROSPORT_XMLTV_IDS = {
    "77": "eurosport.1",
    "106": "eurosport.2",
}
_ALLENTE_SE_XMLTV_IDS = {
    "20092": "allente_se.vextra",
    "50048": "allente_se.vmotor",
    "50049": "allente_se.vvin",
    "50056": "allente_se.vfoot",
    "50077": "allente_se.vgolf",
    "50078": "allente_se.vpre",
    "50079": "allente_se.v1",
    "50105": "allente_se.vultra",
    "50125": "allente_se.vl1",
    "50126": "allente_se.vl2",
    "50127": "allente_se.vl3",
    "50128": "allente_se.vl4",
    "50129": "allente_se.vl5",
}
_ALLENTE_NO_XMLTV_IDS = {
    "10009": "allente_no.tvn",
    "10010": "allente_no.fem",
    "10011": "allente_no.rex",
    "10022": "allente_no.euron",
    "10091": "allente_no.euro1",
}
# EE 的官方公开节目接口以 `sky-doc` 作为该服务的内部标记；用户指定导出时
# 使用数字稳定 ID，以便客户端统一识别 Sky Documentaries。
_EE_XMLTV_IDS = {
    "sky-doc": "ee_uk.352",
}
_SBB_XMLTV_IDS = {
    "84": "eurosport.1",
    "85": "eurosport.2",
    "1082": "eurosport.4k",
    "2143": "travelxp.eu",
}
_CANALPLUS_FR_XMLTV_IDS = {
    "301": "canal+.fr",
    "19": "foot+.fr",
}
# Player.pl 的 tvg-id 由用户直接指定（channel_id 即最终 ID）。
_PLAYER_PL_XMLTV_IDS = {
    "eurosport1.pl": "eurosport1.pl",
    "eurosport2.pl": "eurosport2.pl",
    "eurosport3.pl": "eurosport3.pl",
    "eurosport4.pl": "eurosport4.pl",
    "ElevenSp.1": "ElevenSp.1",
}


def _xmltv_channel_id(record: Programme) -> str:
    """构造稳定且跨来源不冲突的 XMLTV 频道标识。

    通常使用 `<provider>.<channel-number>`；没有公开频道号的单频道来源可将
    `channel_number` 留空，此时精确使用 `<provider>`，例如 `digi4k_ro`。
    """
    if record.provider == "tvplus_tr":
        configured_id = _TVPLUS_EUROSPORT_XMLTV_IDS.get(record.channel_id)
        if configured_id:
            return configured_id
    if record.provider == "allente_se":
        configured_id = _ALLENTE_SE_XMLTV_IDS.get(record.channel_id)
        if configured_id:
            return configured_id
    if record.provider == "allente_no":
        configured_id = _ALLENTE_NO_XMLTV_IDS.get(record.channel_id)
        if configured_id:
            return configured_id
    if record.provider == "ee_uk":
        configured_id = _EE_XMLTV_IDS.get(record.channel_number)
        if configured_id:
            return configured_id
    if record.provider == "sbb_rs":
        configured_id = _SBB_XMLTV_IDS.get(record.channel_id)
        if configured_id:
            return configured_id
    if record.provider == "canalplus_fr":
        configured_id = _CANALPLUS_FR_XMLTV_IDS.get(record.channel_number)
        if configured_id:
            return configured_id
    if record.provider == "player_pl":
        configured_id = _PLAYER_PL_XMLTV_IDS.get(record.channel_id)
        if configured_id:
            return configured_id
    if record.provider == "canalplus_pl_4k":
        # channel_id 即用户指定的 tvg-id（canal+4k.pl）
        return record.channel_id
    return record.provider if not record.channel_number else f"{record.provider}.{record.channel_number}"


def _xmltv_timestamp(value: str) -> str:
    """把 ISO 8601 含时区时间转换为 XMLTV 的时间格式（统一转为北京时间 +0800 输出）。"""
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        raise ValueError(f"XMLTV 时间必须带时区：{value}")
    return parsed.astimezone(_XMLTV_OUTPUT_ZONE).strftime("%Y%m%d%H%M%S %z")


def write_xmltv(records: Iterable[Programme], xml_path: Path, gzip_path: Path) -> tuple[int, int]:
    """写入 XMLTV 与 gzip 文件，返回频道数和节目数。"""
    programmes = sorted(
        records,
        key=lambda item: (item.provider, item.channel_number, item.start_at, item.end_at or "", item.title),
    )
    channels: dict[str, list[Programme]] = defaultdict(list)
    for programme in programmes:
        channels[_xmltv_channel_id(programme)].append(programme)

    root = ET.Element("tv", {"generator-info-name": "none", "generator-info-url": "none"})
    for channel_id in sorted(channels):
        first = channels[channel_id][0]
        channel = ET.SubElement(root, "channel", {"id": channel_id})
        # 节点顺序与 epgshare01 对齐：url -> display-name（epgshare 的 icon 在最前，
        # 但我们没有频道级台标数据，只对齐我们有的节点顺序）。
        ET.SubElement(channel, "url").text = first.source_url
        ET.SubElement(channel, "display-name", {"lang": "en"}).text = first.channel_name

    for programme in programmes:
        # 属性顺序与 epgshare01 对齐（channel, start, stop）：标准 XML 解析器
        # 不在乎顺序，但某些客户端用正则/顺序敏感方式解析，先写 channel 最稳妥。
        attributes = {
            "channel": _xmltv_channel_id(programme),
            "start": _xmltv_timestamp(programme.start_at),
        }
        if programme.end_at:
            attributes["stop"] = _xmltv_timestamp(programme.end_at)
        item = ET.SubElement(root, "programme", attributes)
        # 子节点严格顺序（对齐 EPGShare / XMLTV DTD）：
        # title -> sub-title -> desc -> category -> icon -> episode-num -> rating。
        # 严禁乱序；所有文本标签统一 lang="en"。
        title_el = ET.SubElement(item, "title", {"lang": "en"})
        # 源站/翻译接口（如 Google 翻译）可能返回 HTML 实体（&#39; 之类）：
        # 先解一次再交由 ElementTree 统一转义，避免出现 &amp;#39; 双重转义。
        title_el.text = html.unescape(programme.title)
        # 副标题（上游有则输出）。
        sub_title = getattr(programme, "sub_title", None)
        if sub_title and sub_title.strip():
            sub_el = ET.SubElement(item, "sub-title", {"lang": "en"})
            sub_el.text = html.unescape(sub_title.strip())
        # 简介：有上游简介用之，否则生成语义化基础描述；
        # 严禁输出 "-" 占位符（播放器会因此折叠海报面板）。
        category = getattr(programme, "category", None) or infer_category(
            programme.channel_name, programme.title, programme.provider
        )
        desc_el = ET.SubElement(item, "desc", {"lang": "en"})
        desc_el.text = build_description(
            html.unescape(programme.title),
            programme.channel_name,
            category,
            getattr(programme, "description", None),
        )
        # 分类标签。
        ET.SubElement(item, "category", {"lang": "en"}).text = category
        if programme.image_url:
            # NanoTV template-compatible programme-level poster reference.
            # programme 下不输出 <url>：NanoTV 作者确认其不需要，保持与 epgshare01 一致。
            ET.SubElement(item, "icon", {"src": programme.image_url})

    tree = ET.ElementTree(root)
    ET.indent(tree, space="  ")
    xml_path.parent.mkdir(parents=True, exist_ok=True)
    # XML 声明与 epgshare01 逐字节对齐：双引号、大写 UTF-8，?> 前有空格。
    # 不输出 DOCTYPE：epgshare01（WebGrab+Plus 生成、NanoTV 实测可显示背景图）
    # 没有 DOCTYPE 行，完全仿照它以避免顺序敏感的解析器误判。
    with xml_path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write('<?xml version="1.0" encoding="UTF-8" ?>\n')
        handle.write(ET.tostring(root, encoding="unicode"))
    _write_gzip_verified(xml_path, gzip_path)
    return len(channels), len(programmes)


def _write_gzip_verified(xml_path: Path, gzip_path: Path) -> None:
    """将 XML 压缩为 .gz，写入完成前做合法性校验。

    防坏包三件套：
    1. XML 为空或不存在直接抛异常，严禁生成空压缩包；
    2. 先写临时文件，校验通过后再原子替换目标文件；
    3. 校验 .gz 可正常解压且解压内容与源 XML 逐字节一致。
    任何一步失败都抛异常，调用方不得提交损坏文件。
    """
    if not xml_path.is_file():
        raise ValueError(f"XML 源文件不存在，拒绝生成 gzip：{xml_path}")
    xml_bytes = xml_path.read_bytes()
    if not xml_bytes:
        raise ValueError(f"XML 源文件为空，拒绝生成 gzip：{xml_path}")
    tmp_path = gzip_path.with_suffix(gzip_path.suffix + ".tmp")
    try:
        with tmp_path.open("wb") as raw:
            # mtime=0：确定性输出，同一内容每次生成字节一致。
            with gzip.GzipFile(filename="epg.xml", mode="wb", fileobj=raw, mtime=0) as f:
                f.write(xml_bytes)
                f.flush()
        # 校验：可解压且内容与源一致。
        with gzip.open(tmp_path, "rb") as f:
            roundtrip = f.read()
        if roundtrip != xml_bytes:
            raise ValueError("gzip 回读校验失败：解压内容与源 XML 不一致")
        if tmp_path.stat().st_size == 0:
            raise ValueError("生成的 gzip 文件为 0 字节")
        tmp_path.replace(gzip_path)
    except Exception:
        tmp_path.unlink(missing_ok=True)
        raise
