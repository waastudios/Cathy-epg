"""仅调用运营商官网或官方子域的节目表采集器。"""

from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path
import json
import re
import time
from typing import Any
from zoneinfo import ZoneInfo

from bs4 import BeautifulSoup
import requests

from .models import Programme, utc_now_iso

USER_AGENT = "official-epg-search/0.1 (+https://github.com; official-source-only research tool)"
ASTRO_API = "https://contenthub-api.eco.astro.com.my/api/v2/search-linear"
ASTRO_GUIDE = "https://www.astro.com.my/content/channels"
NOW_GUIDE = "https://nowplayer.now.com/tvguide?filterType=all"
NOW_EPG = "https://nowplayer.now.com/tvguide/epglist"
STARHUB_GUIDE = "https://www.starhubtvplus.com/guide"


class SourceUnavailable(RuntimeError):
    """官网无法在当前合规访问范围内读取时抛出。"""


def _session() -> requests.Session:
    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT, "Accept": "application/json,text/html;q=0.9,*/*;q=0.8"})
    return session


def collect_astro(days: int = 7, page_size: int = 40, pause_seconds: float = 0.25) -> list[Programme]:
    """读取 Astro 官网 TV Schedule 所使用的公开接口。"""
    session = _session()
    zone = ZoneInfo("Asia/Kuala_Lumpur")
    today = datetime.now(zone).date()
    retrieved_at = utc_now_iso()
    records: list[Programme] = []

    for day_offset in range(days):
        schedule_date = (today + timedelta(days=day_offset)).isoformat()
        page = 1
        while True:
            params = {
                "channelGuide": "true",
                "platform": "acm",
                "channelOrderBy": "stbNumber,asc",
                "scheduleDate": schedule_date,
                "channelLimit": str(page_size),
                "channelPage": str(page),
            }
            response = session.get(ASTRO_API, params=params, timeout=30)
            response.raise_for_status()
            payload = response.json().get("response", {})
            channels = payload.get("channels", {})
            data = channels.get("data", [])
            pagination = channels.get("pagination", {})
            for channel in data:
                schedule = channel.get("schedule", [])
                for item in schedule:
                    start = item.get("eventStartMyt")
                    end = item.get("eventEndMyt")
                    title = (item.get("title") or "").strip()
                    if not (start and end and title):
                        continue
                    records.append(
                        Programme(
                            provider="astro",
                            country="MY",
                            timezone="Asia/Kuala_Lumpur",
                            channel_id=str(channel.get("id", "")),
                            channel_number=str(channel.get("stbNumber", "")),
                            channel_name=(channel.get("title") or "").strip(),
                            title=title,
                            start_at=start,
                            end_at=end,
                            source_url=ASTRO_GUIDE,
                            retrieved_at=retrieved_at,
                        )
                    )
            current_page = int(pagination.get("page", page) or page)
            total_pages = int(pagination.get("totalPages", current_page) or current_page)
            if current_page >= total_pages:
                break
            page += 1
            time.sleep(pause_seconds)
        time.sleep(pause_seconds)
    return _deduplicate(records)


def _now_channel_ids(session: requests.Session) -> list[str]:
    """从 NOW TV 官方 TV Guide 页面提取其公开频道编号。"""
    response = session.get(NOW_GUIDE, timeout=30)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")
    found: set[str] = set()
    for link in soup.select("a[href]"):
        matched = re.search(r"/tvguide/channeldetail/(\d+)/", link.get("href", ""))
        if matched:
            found.add(matched.group(1))
    if not found:
        raise SourceUnavailable("NOW TV 官方 TV Guide 页面未返回可识别的频道编号。")
    return sorted(found, key=lambda item: int(item))


def collect_now_hk(days: int = 7, chunk_size: int = 25, pause_seconds: float = 0.25) -> list[Programme]:
    """读取 NOW TV 官方 TV Guide 页面脚本调用的 EPG 列表端点。"""
    session = _session()
    zone = ZoneInfo("Asia/Hong_Kong")
    channels = _now_channel_ids(session)
    retrieved_at = utc_now_iso()
    records: list[Programme] = []

    for day in range(1, days + 1):
        for start_index in range(0, len(channels), chunk_size):
            group = channels[start_index : start_index + chunk_size]
            # jQuery 对数组的传统序列化方式；该参数形状来自 NOW TV 的官方页面脚本。
            params: list[tuple[str, str]] = [("channelIdList[]", channel) for channel in group]
            params.append(("day", str(day)))
            response = session.get(NOW_EPG, params=params, timeout=30)
            response.raise_for_status()
            try:
                payload: Any = response.json()
            except ValueError as exc:
                raise SourceUnavailable("NOW TV 官方 EPG 端点未返回 JSON。") from exc
            if not isinstance(payload, list):
                raise SourceUnavailable("NOW TV 官方 EPG 响应格式发生变化。")
            for index, channel_programmes in enumerate(payload):
                channel_number = group[index] if index < len(group) else ""
                if not isinstance(channel_programmes, list):
                    continue
                for item in channel_programmes:
                    title = (item.get("name") or "").strip()
                    start_ms = item.get("start")
                    end_ms = item.get("end")
                    if not (title and isinstance(start_ms, (int, float)) and isinstance(end_ms, (int, float))):
                        continue
                    start = datetime.fromtimestamp(start_ms / 1000, tz=zone).isoformat()
                    end = datetime.fromtimestamp(end_ms / 1000, tz=zone).isoformat()
                    records.append(
                        Programme(
                            provider="now_hk",
                            country="HK",
                            timezone="Asia/Hong_Kong",
                            channel_id=channel_number,
                            channel_number=channel_number,
                            channel_name=f"CH {channel_number}",
                            title=title,
                            start_at=start,
                            end_at=end,
                            source_url=NOW_GUIDE,
                            retrieved_at=retrieved_at,
                        )
                    )
            time.sleep(pause_seconds)
    return _deduplicate(records)


def import_starhub_authorized_export(export_path: Path) -> list[Programme]:
    """导入由用户自行从已授权 StarHub TV+ 会话导出的官方 JSON。

    该函数刻意不处理登录、Cookie、绕过地域或订阅限制。导出文件须为对象列表，
    每项至少有 channel_number、channel_name、title、start_at、end_at 字段。
    """
    with export_path.open(encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, list):
        raise ValueError("StarHub 授权导出必须是 JSON 对象列表。")
    retrieved_at = utc_now_iso()
    records: list[Programme] = []
    for item in payload:
        required = ["channel_number", "channel_name", "title", "start_at", "end_at"]
        if not isinstance(item, dict) or any(not item.get(field) for field in required):
            continue
        records.append(
            Programme(
                provider="starhub",
                country="SG",
                timezone="Asia/Singapore",
                channel_id=str(item.get("channel_id", item["channel_number"])),
                channel_number=str(item["channel_number"]),
                channel_name=str(item["channel_name"]),
                title=str(item["title"]),
                start_at=str(item["start_at"]),
                end_at=str(item["end_at"]),
                source_url=STARHUB_GUIDE,
                retrieved_at=retrieved_at,
            )
        )
    return _deduplicate(records)


def _deduplicate(records: list[Programme]) -> list[Programme]:
    unique: dict[tuple[str, str, str, str, str], Programme] = {}
    for record in records:
        key = (record.provider, record.channel_id, record.start_at, record.end_at, record.title)
        unique[key] = record
    return list(unique.values())
