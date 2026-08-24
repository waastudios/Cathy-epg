"""仅调用运营商官网或官方电视提供商页面的节目表采集器。"""

from __future__ import annotations

from datetime import date, datetime, time as clock_time, timedelta
import json
import re
import time
from typing import Any
from zoneinfo import ZoneInfo

from bs4 import BeautifulSoup
import requests

from .models import Programme, utc_now_iso

USER_AGENT = "Cathy-epg/0.2 (+https://github.com/waastudios/Cathy-epg; official-source-only research tool)"
ASTRO_API = "https://contenthub-api.eco.astro.com.my/api/v2/search-linear"
ASTRO_GUIDE = "https://www.astro.com.my/content/channels"
NOW_HK_GUIDE = "https://nowplayer.now.com/tvguide?filterType=all"
NOW_HK_CHANNELS_ZH = "https://nowplayer.now.com/channels?lang=zh&filterType=all"
NOW_HK_EPG = "https://nowplayer.now.com/tvguide/epglist"
ALLENTE_GUIDE = "https://www.allente.se/tv-guide/"
ALLENTE_EPG = "https://www.allente.se/api/epg/refetch-epg-data"
ALLENTE_V_SPORT_IDS = frozenset({"20092", "50048", "50049", "50056", "50077", "50078", "50079", "50105", "50125", "50126", "50127", "50128", "50129"})
SKY_SPORTS_GUIDE = "https://www.sky.com/watch/channel/sky-sports"
SKY_SPORTS_MORE = "https://www.skysports.com/watch/liveonsky/more/{token}"
DIGI4K_GUIDE = "https://www.digi4k.ro/"
TVPLUS_EUROSPORT_1_GUIDE = "https://tvplus.com.tr/canli-tv/yayin-akisi/eurosport-1-hd--77"
TVPLUS_EUROSPORT_2_GUIDE = "https://tvplus.com.tr/canli-tv/yayin-akisi/eurosport-2-hd--106"


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
                for item in channel.get("schedule", []):
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


def _now_hk_channels_zh(session: requests.Session) -> dict[str, str]:
    """从 NOW TV 香港官方中文频道页读取频道号与中文显示名。"""
    response = session.get(NOW_HK_CHANNELS_ZH, timeout=30)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")
    channels: dict[str, str] = {}
    for link in soup.select("a[href]"):
        matched = re.search(r"/tvguide/channeldetail/(\d+)/", link.get("href", ""))
        if not matched:
            continue
        number = matched.group(1)
        name = link.get_text(" ", strip=True)
        name = re.sub(rf"\s*CH\s*{re.escape(number)}\s*$", "", name, flags=re.IGNORECASE).strip()
        if name:
            channels[number] = name
    if not channels:
        raise SourceUnavailable("NOW TV 香港官方中文频道页未返回可识别的频道名称映射。")
    return channels


def collect_now_hk(days: int = 7, chunk_size: int = 25, pause_seconds: float = 0.25) -> list[Programme]:
    """读取 NOW TV 香港官网 EPG，并将频道显示名规范化为官方中文名称。"""
    session = _session()
    zone = ZoneInfo("Asia/Hong_Kong")
    channel_names = _now_hk_channels_zh(session)
    channels = sorted(channel_names, key=int)
    retrieved_at = utc_now_iso()
    records: list[Programme] = []

    for day in range(1, days + 1):
        for start_index in range(0, len(channels), chunk_size):
            group = channels[start_index : start_index + chunk_size]
            # 参数形状来自 NOW TV 官方 TV Guide 页面脚本的 jQuery 数组序列化。
            params: list[tuple[str, str]] = [("channelIdList[]", channel) for channel in group]
            params.append(("day", str(day)))
            response = session.get(NOW_HK_EPG, params=params, timeout=30)
            response.raise_for_status()
            try:
                payload: Any = response.json()
            except ValueError as exc:
                raise SourceUnavailable("NOW TV 香港官方 EPG 端点未返回 JSON。") from exc
            if not isinstance(payload, list):
                raise SourceUnavailable("NOW TV 香港官方 EPG 响应格式发生变化。")
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
                    records.append(
                        Programme(
                            provider="now_hk",
                            country="HK",
                            timezone="Asia/Hong_Kong",
                            channel_id=channel_number,
                            channel_number=channel_number,
                            channel_name=channel_names.get(channel_number, f"CH {channel_number}"),
                            title=title,
                            start_at=datetime.fromtimestamp(start_ms / 1000, tz=zone).isoformat(),
                            end_at=datetime.fromtimestamp(end_ms / 1000, tz=zone).isoformat(),
                            source_url=NOW_HK_GUIDE,
                            retrieved_at=retrieved_at,
                        )
                    )
            time.sleep(pause_seconds)
    return _deduplicate(records)


def _to_local_iso(value: str, zone: ZoneInfo) -> str:
    """将运营商返回的含时区时间转换成来源市场的本地 ISO 时间。"""
    return datetime.fromisoformat(value).astimezone(zone).isoformat()


def collect_allente_v_sport(days: int = 7, pause_seconds: float = 0.25) -> list[Programme]:
    """读取 Allente 瑞典官方 EPG 中全部可公开识别的 V Sport 体育频道节目表。"""
    session = _session()
    zone = ZoneInfo("Europe/Stockholm")
    today = datetime.now(zone).date()
    retrieved_at = utc_now_iso()
    records: list[Programme] = []

    for day_offset in range(days):
        response = session.get(ALLENTE_EPG, params={"Start": (today + timedelta(days=day_offset)).isoformat()}, timeout=60)
        response.raise_for_status()
        payload = response.json()
        channels = [item for item in payload.get("channels", []) if str(item.get("id")) in ALLENTE_V_SPORT_IDS]
        if not channels:
            raise SourceUnavailable("Allente 官方 EPG 响应中未找到任何预期的 V Sport 体育频道。")
        for channel in channels:
            channel_id = str(channel.get("id"))
            channel_name = (channel.get("name") or f"V sport {channel_id}").strip()
            for item in channel.get("programs", []):
                title = (item.get("title") or "").strip()
                start = item.get("eventStart")
                end = item.get("eventEnd")
                if not (title and start and end):
                    continue
                records.append(
                    Programme(
                        provider="allente_se",
                        country="SE",
                        timezone="Europe/Stockholm",
                        channel_id=channel_id,
                        channel_number=channel_id,
                        channel_name=channel_name,
                        title=title,
                        start_at=_to_local_iso(start, zone),
                        end_at=_to_local_iso(end, zone),
                        source_url=ALLENTE_GUIDE,
                        retrieved_at=retrieved_at,
                    )
                )
        time.sleep(pause_seconds)
    return _deduplicate(records)


def collect_allente_v_sport_ultrahd(days: int = 7, pause_seconds: float = 0.25) -> list[Programme]:
    """兼容旧接口：仅保留 V sport ultra HD（50105）记录。"""
    return [record for record in collect_allente_v_sport(days, pause_seconds) if record.channel_id == "50105"]


def _parse_sky_date(label: str, reference: date) -> date | None:
    """解析 Sky Sports 页面如 `Mon 24th August` 的日期标题。"""
    matched = re.search(r"(\d{1,2})(?:st|nd|rd|th)\s+([A-Za-z]+)", label)
    if not matched:
        return None
    day_number, month_name = matched.groups()
    try:
        parsed = datetime.strptime(f"{day_number} {month_name} {reference.year}", "%d %B %Y").date()
    except ValueError:
        return None
    if parsed < reference - timedelta(days=7):
        parsed = parsed.replace(year=parsed.year + 1)
    return parsed


def _sky_channel_slug(name: str) -> str:
    """把官方 Sky Sports 频道名转换为稳定的 XMLTV 频道号部分。"""
    slug = re.sub(r"[^a-z0-9]+", "-", name.casefold().replace("+", " plus ")).strip("-")
    return slug or "sky-sports"


def _parse_sky_events(html: str, reference: date, retrieved_at: str) -> list[Programme]:
    """从 Sky 官方 sport-on-sky 页面解析按日直播活动和频道开播时间。"""
    soup = BeautifulSoup(html, "html.parser")
    zone = ZoneInfo("Europe/London")
    records: list[Programme] = []
    for event in soup.select("div.event-group"):
        date_heading = event.find_previous("h3", class_=re.compile(r"text-h4"))
        event_date = _parse_sky_date(date_heading.get_text(" ", strip=True), reference) if date_heading else None
        title_node = event.select_one("strong")
        detail_node = event.select_one("p.event-detail")
        title = title_node.get_text(" ", strip=True) if title_node else ""
        detail = detail_node.get_text(" ", strip=True) if detail_node else ""
        if not (event_date and title and detail):
            continue
        for channel_name, start_text in re.findall(r"([^,(]+?)\s*\((\d{2}:\d{2})\)", detail):
            channel_name = channel_name.strip()
            try:
                start_time = datetime.strptime(start_text, "%H:%M").time()
            except ValueError:
                continue
            start = datetime.combine(event_date, start_time, tzinfo=zone).isoformat()
            records.append(
                Programme(
                    provider="now_uk",
                    country="GB",
                    timezone="Europe/London",
                    channel_id=_sky_channel_slug(channel_name),
                    channel_number=_sky_channel_slug(channel_name),
                    channel_name=channel_name,
                    title=title,
                    start_at=start,
                    # Sky 官方 Live Sports 页面只公开开播时间，不推测或伪造结束时间。
                    end_at=None,
                    source_url=SKY_SPORTS_GUIDE,
                    retrieved_at=retrieved_at,
                )
            )
    return records


def collect_now_uk_sports(days: int = 7, pause_seconds: float = 0.25) -> list[Programme]:
    """读取 Sky 官方直播体育列表，作为英国 NOW Sports 可观看 Sky Sports 的官方活动表。

    这不是英国 NOW 全部娱乐频道的完整全天 EPG；只包含 Sky 官方明确列出的
    Sky Sports 直播活动及其频道和开播时间。
    """
    session = _session()
    zone = ZoneInfo("Europe/London")
    today = datetime.now(zone).date()
    target_end = today + timedelta(days=days - 1)
    retrieved_at = utc_now_iso()
    response = session.get(SKY_SPORTS_GUIDE, timeout=30)
    response.raise_for_status()
    records = _parse_sky_events(response.text, today, retrieved_at)

    soup = BeautifulSoup(response.text, "html.parser")
    loader = soup.select_one("div[data-fn='load-more'][data-current-page]")
    token = loader.get("data-current-page") if loader else None
    visited: set[str] = set()
    while token and token not in visited:
        visited.add(token)
        more = session.get(SKY_SPORTS_MORE.format(token=token), timeout=30)
        more.raise_for_status()
        page_records = _parse_sky_events(more.text, today, retrieved_at)
        records.extend(page_records)
        page_dates = [date.fromisoformat(record.start_at[:10]) for record in page_records]
        if page_dates and min(page_dates) > target_end:
            break
        more_soup = BeautifulSoup(more.text, "html.parser")
        more_loader = more_soup.select_one("div[data-fn='load-more'][data-current-page]")
        token = more_loader.get("data-current-page") if more_loader else None
        time.sleep(pause_seconds)

    return _deduplicate([record for record in records if date.fromisoformat(record.start_at[:10]) <= target_end])


def _digi4k_time(value: str) -> clock_time | None:
    """解析 Digi 4K 官方页面使用的 `Ora HH:MM` 时间标签。"""
    matched = re.search(r"Ora\s+(\d{1,2}):(\d{2})", value)
    if not matched:
        return None
    try:
        return clock_time(hour=int(matched.group(1)), minute=int(matched.group(2)))
    except ValueError:
        return None


def collect_digi4k(days: int = 7) -> list[Programme]:
    """解析 Digi 4K 罗马尼亚官网首页公开发布的一周节目表。

    官网逐日展示开始时间而不总是发布最后一档的结束时间；最后一档的 XMLTV
    `stop` 将被省略，而不是根据猜测补写。
    """
    session = _session()
    response = session.get(DIGI4K_GUIDE, timeout=30)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")
    day_nodes = soup.select(".schedule-days > .schedule-days-item")
    if len(day_nodes) < days:
        raise SourceUnavailable("Digi 4K 官网未返回足够的连续节目日容器。")

    zone = ZoneInfo("Europe/Bucharest")
    today = datetime.now(zone).date()
    retrieved_at = utc_now_iso()
    records: list[Programme] = []
    for day_offset, day_node in enumerate(day_nodes[:days]):
        raw_items: list[tuple[clock_time, str]] = []
        for mark in day_node.select("mark.schedule-days-item-hour"):
            start_time = _digi4k_time(mark.get_text(" ", strip=True))
            row = mark.find_parent("div", class_=lambda classes: classes and "flex" in classes)
            title_node = row.select_one("h3") if row else None
            title = title_node.get_text(" ", strip=True) if title_node else ""
            if start_time and title:
                raw_items.append((start_time, title))
        if not raw_items:
            continue
        schedule_day = today + timedelta(days=day_offset)
        raw_items.sort(key=lambda item: item[0])
        for index, (start_time, title) in enumerate(raw_items):
            start = datetime.combine(schedule_day, start_time, tzinfo=zone)
            end_at: str | None = None
            if index + 1 < len(raw_items):
                next_time = raw_items[index + 1][0]
                next_day = schedule_day + timedelta(days=1) if next_time <= start_time else schedule_day
                end_at = datetime.combine(next_day, next_time, tzinfo=zone).isoformat()
            records.append(
                Programme(
                    provider="digi4k_ro",
                    country="RO",
                    timezone="Europe/Bucharest",
                    channel_id="digi-4k",
                    channel_number="digi-4k",
                    channel_name="Digi 4K",
                    title=title,
                    start_at=start.isoformat(),
                    end_at=end_at,
                    source_url=DIGI4K_GUIDE,
                    retrieved_at=retrieved_at,
                )
            )
    if not records:
        raise SourceUnavailable("Digi 4K 官网节目容器未返回可识别的时间和节目标题。")
    return _deduplicate(records)


def _tvplus_playbills_from_html(html: str) -> list[dict[str, Any]]:
    """从 TV+ 官方 SSR 页面内嵌的 Next 数据块读取当日节目对象。"""
    matcher = re.compile(r'self\.__next_f\.push\(\[1,("(?:\\.|[^"\\])*")\]\)')
    decoder = json.JSONDecoder()
    marker = '"initialData":{"playbills":'
    for matched in matcher.finditer(html):
        try:
            chunk = json.loads(matched.group(1))
        except json.JSONDecodeError:
            continue
        position = chunk.find(marker)
        if position < 0:
            continue
        try:
            playbills, _ = decoder.raw_decode(chunk[position + len(marker) :])
        except json.JSONDecodeError:
            continue
        if isinstance(playbills, list):
            return [item for item in playbills if isinstance(item, dict)]
    return []


def collect_tvplus_eurosport(days: int = 7) -> list[Programme]:
    """读取土耳其 TV+（官方电视提供商）公开的 Eurosport 1/2 节目页。

    TV+ 的后续日期在匿名网页会话中动态加载。公开 SSR 页稳定提供当日完整
    `starttime`/`endtime` 表；当匿名会话接口无法由普通 HTTP 客户端合规重放时，
    本采集器仅发布已公开的当日条目，不伪造未来节目。
    """
    session = _session()
    zone = ZoneInfo("Europe/Istanbul")
    retrieved_at = utc_now_iso()
    definitions = (
        ("77", "Eurosport 1", TVPLUS_EUROSPORT_1_GUIDE),
        ("106", "Eurosport 2", TVPLUS_EUROSPORT_2_GUIDE),
    )
    records: list[Programme] = []
    for channel_id, channel_name, source_url in definitions:
        response = session.get(source_url, timeout=30)
        response.raise_for_status()
        playbills = _tvplus_playbills_from_html(response.text)
        if not playbills:
            raise SourceUnavailable(f"TV+ 官方 {channel_name} 页面未返回可识别的当日节目数据。")
        for item in playbills:
            title = (item.get("name") or "").strip()
            start_ms = item.get("starttime")
            end_ms = item.get("endtime")
            if not (title and isinstance(start_ms, (int, float)) and isinstance(end_ms, (int, float))):
                continue
            records.append(
                Programme(
                    provider="tvplus_tr",
                    country="TR",
                    timezone="Europe/Istanbul",
                    channel_id=channel_id,
                    channel_number=channel_id,
                    channel_name=channel_name,
                    title=title,
                    start_at=datetime.fromtimestamp(start_ms / 1000, tz=zone).isoformat(),
                    end_at=datetime.fromtimestamp(end_ms / 1000, tz=zone).isoformat(),
                    source_url=source_url,
                    retrieved_at=retrieved_at,
                )
            )
    if not records:
        raise SourceUnavailable("TV+ 官方 Eurosport 1/2 页面没有可发布的节目记录。")
    return _deduplicate(records)


def _deduplicate(records: list[Programme]) -> list[Programme]:
    unique: dict[tuple[str, str, str, str, str], Programme] = {}
    for record in records:
        key = (record.provider, record.channel_id, record.start_at, record.end_at or "", record.title)
        unique[key] = record
    return list(unique.values())
