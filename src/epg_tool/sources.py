"""仅调用运营商官网或官方电视提供商页面的节目表采集器。"""

from __future__ import annotations

from datetime import date, datetime, time as clock_time, timedelta, timezone
import json
import re
import time
from typing import Any
import xml.etree.ElementTree as ET
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
ALLENTE_NO_GUIDE = "https://www.allente.no/tv-guide/"
ALLENTE_NO_EPG = "https://www.allente.no/api/epg/refetch-epg-data"
# Allente Norway 官方 TV Guide 的标准频道；不收录同节目流的字幕／音频描述镜像。
ALLENTE_NO_CHANNEL_IDS = frozenset({"10009", "10010", "10011", "10022"})
EE_TV_PLAYER_GUIDE = "https://player.ee.co.uk/#/livetv/schedule"
EE_TV_SCHEDULE = "https://api.youview.tv/metadata/linear/v2/schedule/by-servicelocator"
# 以下映射来自 EE TV Player 匿名公开的线性频道目录；仅保留每个实际频道的 SD 行。
# 同一节目流的 HD、+1、字幕／音频描述镜像明确排除，防止跨馈源重复频道。
EE_UK_CHANNELS: tuple[tuple[str, str, str], ...] = (
    ("408", "TNT Sports 1", "http://bds.tv/services/BT_763997"),
    ("409", "TNT Sports 2", "http://bds.tv/services/BT_764001"),
    ("410", "TNT Sports 3", "http://bds.tv/services/BT_768612"),
    ("411", "TNT Sports 4", "http://bds.tv/services/BT_758465"),
    ("418", "Sky Sports News", "http://bds.tv/services/BT_631679_1314_SD"),
    ("419", "Sky Sports Main Event", "http://bds.tv/services/BT_503_1301_SD"),
    ("420", "Sky Sports Premier League", "http://bds.tv/services/BT_768064_1303_SD"),
    ("421", "Sky Sports Football", "http://bds.tv/services/BT_771052_3838_SD"),
    ("422", "Sky Sports Cricket", "http://bds.tv/services/BT_223160_1302_SD"),
    ("423", "Sky Sports Golf", "http://bds.tv/services/BT_750598_1322_SD"),
    ("424", "Sky Sports F1", "http://bds.tv/services/BT_759963_1306_SD"),
    ("425", "Sky Sports Tennis", "http://bds.tv/services/BT_RBM63515_1284_SD"),
    ("426", "Sky Sports Action", "http://bds.tv/services/BT_397065_1333_SD"),
    ("427", "Sky Sports +", "http://bds.tv/services/BT_771051_3839_SD"),
    ("428", "Sky Sports Racing", "http://bds.tv/services/BT_751621_1354_SD"),
    ("429", "Sky Sports Mix", "http://bds.tv/services/BT_770332_4091_SD"),
    # BBC、ITV、Channel 4 与 Sky 娱乐频道：频道名和逻辑频道号均来自 EE Player 公开目录。
    ("1", "BBC One London", "dvb://233a..1044"),
    ("2", "BBC Two", "dvb://233a..10bf"),
    ("3", "ITV1 London", "dvb://233a..2045"),
    ("4", "Channel 4", "dvb://233a..20c0"),
    ("6", "ITV2", "dvb://233a..2085"),
    ("9", "BBC Four", "dvb://233a..11c0"),
    ("10", "ITV3", "dvb://233a..2066"),
    ("23", "BBC Three", "dvb://233a..10c0"),
    ("26", "ITV4", "dvb://233a..208a"),
    ("28", "ITV Quiz", "dvb://233a..2094"),
    ("231", "BBC News", "dvb://233a..1100"),
    ("232", "BBC Parliament", "dvb://233a..1280"),
    ("342", "Sky Atlantic", "http://bds.tv/services/BT_759409_1412_SD"),
    ("346", "Sky One", "http://bds.tv/services/BT_255_1402_SD"),
    ("349", "Sky Crime", "http://bds.tv/services/BT_753644_1212_SD"),
)
DIGI4K_GUIDE = "https://www.digi4k.ro/"
TVPLUS_EUROSPORT_1_GUIDE = "https://tvplus.com.tr/canli-tv/yayin-akisi/eurosport-1-hd--77"
TVPLUS_EUROSPORT_2_GUIDE = "https://tvplus.com.tr/canli-tv/yayin-akisi/eurosport-2-hd--106"
# Virgin Media TV Go Guide 在普通匿名页面会话中加载以下官方频道目录与 EPG 时间片。
VIRGIN_UK_GUIDE = "https://virgintvgo.virginmedia.com/en/epg/initial"
VIRGIN_UK_CHANNELS = (
    "https://spark-prod-gb.gnp.cloud.virgintvgo.virginmedia.com/eng/web/linear-service/v2/channels"
)
VIRGIN_UK_EPG_SEGMENT = (
    "https://staticqbr-prod-gb.gnp.cloud.virgintvgo.virginmedia.com/eng/web/epg-service-lite/gb/en/events/segments/{segment}"
)
# 频道目录自报的正式频道名与内部 ID；不收录隐藏的 Duplicate 镜像（2321、2322）。
VIRGIN_UK_ULTRA_CHANNELS: dict[str, str] = {
    "2258": "Sky Sports Ultra HD 1",
    "2265": "Sky Sports Ultra HD 2",
}


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


def collect_allente_no(days: int = 7, pause_seconds: float = 0.25) -> list[Programme]:
    """读取 Allente Norway 官方 TV Guide 的 TVNorge、REX、FEM 与 Eurosport Norge。

    仅使用非字幕／非音频描述的标准频道。节目页公开提供精确开始与结束时间。
    """
    session = _session()
    zone = ZoneInfo("Europe/Oslo")
    today = datetime.now(zone).date()
    retrieved_at = utc_now_iso()
    records: list[Programme] = []

    for day_offset in range(days):
        response = session.get(ALLENTE_NO_EPG, params={"Start": (today + timedelta(days=day_offset)).isoformat()}, timeout=60)
        response.raise_for_status()
        payload = response.json()
        channels = [item for item in payload.get("channels", []) if str(item.get("id")) in ALLENTE_NO_CHANNEL_IDS]
        if not channels:
            raise SourceUnavailable("Allente Norway 官方 EPG 响应中未找到预期的 TVNorge、REX、FEM 或 Eurosport Norge。")
        for channel in channels:
            channel_id = str(channel.get("id"))
            channel_name = (channel.get("name") or "").strip()
            if not channel_name:
                continue
            for item in channel.get("programs", []):
                title = (item.get("title") or "").strip()
                start = item.get("eventStart")
                end = item.get("eventEnd")
                if not (title and start and end):
                    continue
                records.append(
                    Programme(
                        provider="allente_no",
                        country="NO",
                        timezone="Europe/Oslo",
                        channel_id=channel_id,
                        channel_number=channel_id,
                        channel_name=channel_name,
                        title=title,
                        start_at=_to_local_iso(start, zone),
                        end_at=_to_local_iso(end, zone),
                        source_url=ALLENTE_NO_GUIDE,
                        retrieved_at=retrieved_at,
                    )
                )
        time.sleep(pause_seconds)
    return _deduplicate(records)


def _ee_interval_starts(today: date, days: int, zone: ZoneInfo) -> list[datetime]:
    """返回覆盖本地连续日期的 EE Player 六小时时间窗起点（统一换算为 UTC）。"""
    intervals: list[datetime] = []
    for day_offset in range(days):
        local_midnight = datetime.combine(today + timedelta(days=day_offset), clock_time.min, tzinfo=zone)
        for hour in range(0, 24, 6):
            intervals.append((local_midnight + timedelta(hours=hour)).astimezone(timezone.utc))
    return intervals


def collect_ee_uk_channels(days: int = 7, pause_seconds: float = 0.02) -> list[Programme]:
    """读取 EE TV Player 匿名公开的目标英国标准清晰度频道节目表。

    EE 的 Live TV Schedule 正常加载 YouView 官方节目端点，公开返回单频道的
    ``publishedStartTime`` 与 ``publishedDuration``。频道列表只使用 EE 的 SD
    逻辑频道号，特意排除同一线性流的 HD、+1 及辅助服务镜像，避免重复。
    """
    if days not in range(1, 8):
        raise ValueError("EE TV Player 采集天数必须为 1–7。")
    session = _session()
    zone = ZoneInfo("Europe/London")
    today = datetime.now(zone).date()
    retrieved_at = utc_now_iso()
    intervals = _ee_interval_starts(today, days, zone)
    records: list[Programme] = []

    for channel_number, channel_name, service_locator in EE_UK_CHANNELS:
        channel_records = 0
        for interval_start in intervals:
            interval_token = interval_start.strftime("%Y-%m-%dT%HZ/PT6H")
            response = session.get(
                EE_TV_SCHEDULE,
                params={"serviceLocator": service_locator, "interval": interval_token},
                timeout=30,
            )
            response.raise_for_status()
            payload = response.json()
            items = payload.get("items", [])
            if not isinstance(items, list):
                raise SourceUnavailable("EE TV Player 官方节目表响应未返回 items 列表。")
            for item in items:
                if not isinstance(item, dict):
                    continue
                title = (item.get("title") or "").strip()
                published_start = item.get("publishedStartTime")
                duration = item.get("publishedDuration")
                service_name = ((item.get("serviceSummary") or {}).get("fullName") or "").strip()
                if not (title and isinstance(published_start, str)):
                    continue
                if service_name and service_name != channel_name:
                    raise SourceUnavailable(
                        f"EE TV Player 服务定位符 {service_locator} 返回了意外频道名 {service_name!r}。"
                    )
                try:
                    start = datetime.fromisoformat(published_start.replace("Z", "+00:00")).astimezone(zone)
                except ValueError:
                    continue
                end_at: str | None = None
                if isinstance(duration, (int, float)) and duration > 0:
                    end_at = (start + timedelta(seconds=duration)).isoformat()
                records.append(
                    Programme(
                        provider="ee_uk",
                        country="GB",
                        timezone="Europe/London",
                        channel_id=channel_number,
                        channel_number=channel_number,
                        channel_name=channel_name,
                        title=title,
                        start_at=start.isoformat(),
                        end_at=end_at,
                        source_url=EE_TV_PLAYER_GUIDE,
                        retrieved_at=retrieved_at,
                    )
                )
                channel_records += 1
            time.sleep(pause_seconds)
        if not channel_records:
            raise SourceUnavailable(f"EE TV Player 未返回 {channel_name}（CH {channel_number}）的公开节目条目。")

    return _deduplicate(records)


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
                    channel_id="digi4k_ro",
                    # 用户指定 XMLTV ID 为 `digi4k_ro`；单频道来源不附加旧的 `digi-4k` 后缀。
                    channel_number="",
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


_TVPLUS_EUROSPORT_TITLE_EXACT: dict[str, str] = {
    "Wuhan Açık": "Wuhan Open",
    "Tırmanış Dünya Serisi": "Climbing World Series",
    "Dünya Motocross Şampiyonası": "Motocross World Championship",
    "2026 Avrupa BMX Şampiyonası": "2026 European BMX Championship",
    "Dünya Formula E Şampiyonası": "Formula E World Championship",
    "Dünya Binicilik Şampiyonası": "Equestrian World Championship",
    "UCI Dağ Bisikleti Dünya Serisi": "UCI Mountain Bike World Series",
}


def _translate_tvplus_eurosport_title(title: str) -> str:
    """将 TV+ 官方土耳其语 Eurosport 标题转换成赛事语义准确的英文。

    该转换在每次 TV+ 刷新时逐条执行。它只翻译公开标题中可明确识别的
    赛事、运动项目与阶段，不补充选手、比分、场地或未由官方页面提供的细节。
    已是英语或国际赛事正式名称的内容保持原样。
    """
    normalised = re.sub(r"\s*,\s*", ", ", title.strip())
    normalised = re.sub(r"\s+", " ", normalised)
    if normalised in _TVPLUS_EUROSPORT_TITLE_EXACT:
        return _TVPLUS_EUROSPORT_TITLE_EXACT[normalised]

    stage_match = re.fullmatch(r"(.+?),?\s*(\d+)\.\s*Etap", normalised, flags=re.IGNORECASE)
    if stage_match:
        event = stage_match.group(1).strip()
        # 官方标题偶有不带重音的 España；统一为国际赛事常用英文拼写。
        event = re.sub(r"La Vuelta a Espana", "La Vuelta a España", event, flags=re.IGNORECASE)
        return f"{event}, Stage {stage_match.group(2)}"

    replacements = (
        ("UCI Dağ Bisikleti Dünya Serisi", "UCI Mountain Bike World Series"),
        ("Dağ Bisikleti Dünya Serisi", "Mountain Bike World Series"),
        ("Dünya Formula E Şampiyonası", "Formula E World Championship"),
        ("Dünya Binicilik Şampiyonası", "Equestrian World Championship"),
        ("Avrupa BMX Şampiyonası", "European BMX Championship"),
        ("Dünya Superbike Şampiyonası", "Superbike World Championship"),
        ("Dünya Ralli Şampiyonası", "World Rally Championship"),
        ("Dünya Dayanıklılık Şampiyonası", "World Endurance Championship"),
        ("Dünya Şampiyonası", "World Championship"),
        ("Avrupa Şampiyonası", "European Championship"),
        ("Tırmanış Dünya Serisi", "Climbing World Series"),
        ("Dünya Motocross Şampiyonası", "Motocross World Championship"),
        ("Yarı Final", "Semi-final"),
        ("Final", "Final"),
        ("Erkekler", "Men"),
        ("Kadınlar", "Women"),
        ("Açık", "Open"),
        ("Etap", "Stage"),
        ("Tur", "Round"),
    )
    translated = normalised
    for source, target in replacements:
        translated = translated.replace(source, target)
    # 不能保证语义准确的残余土耳其语不能静默进入 XMLTV；让来源在状态中明确失败，
    # 而不是发布用户无法使用的原文标题。已覆盖赛事会通过此门槛。
    untranslated = re.search(
        r"[çğıöşüÇĞİÖŞÜ]|\\b(?:Açık|Avrupa|Binicilik|Bisikleti|Bölüm|Canlı|Dağ|Dünya|Erkekler|Etap|Kadınlar|Sezon|Serisi|Şampiyonası|Tekrar|Tırmanış|Tur|Yarı|Özet)\\b",
        translated,
    )
    if untranslated:
        raise SourceUnavailable(f"TV+ Eurosport 标题未获得可验证的英文转换：{title!r}")
    return translated


def collect_tvplus_eurosport(days: int = 7) -> list[Programme]:
    """读取土耳其 TV+（官方电视提供商）公开的 Eurosport 1/2 节目页。

    TV+ 的后续日期在匿名网页会话中动态加载。公开 SSR 页稳定提供当日完整
    `starttime`/`endtime` 表；当匿名会话接口无法由普通 HTTP 客户端合规重放时，
    本采集器仅发布已公开的当日条目，不伪造未来节目。每个官方土耳其语标题都
    经过赛事语义英文转换后写入 XMLTV。
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
            source_title = (item.get("name") or "").strip()
            title = _translate_tvplus_eurosport_title(source_title) if source_title else ""
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


def _virgin_uk_segment_starts(today: date, days: int, zone: ZoneInfo) -> list[datetime]:
    """计算覆盖英国本地连续日期的 Virgin 官方六小时时间片（按 UTC 边界请求）。"""
    first_local = datetime.combine(today, clock_time.min, tzinfo=zone)
    last_local = datetime.combine(today + timedelta(days=days), clock_time.min, tzinfo=zone)
    start_utc = first_local.astimezone(timezone.utc)
    end_utc = last_local.astimezone(timezone.utc)
    # 官方静态 EPG 按 UTC 的 00/06/12/18 点分片；向前／后取整以覆盖夏令时边界。
    start_utc = start_utc.replace(hour=(start_utc.hour // 6) * 6, minute=0, second=0, microsecond=0)
    end_hour = ((end_utc.hour + 5) // 6) * 6
    end_utc = end_utc.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(hours=end_hour)
    starts: list[datetime] = []
    cursor = start_utc
    while cursor < end_utc:
        starts.append(cursor)
        cursor += timedelta(hours=6)
    return starts


def collect_virgin_uk_ultra(days: int = 7, pause_seconds: float = 0.02) -> list[Programme]:
    """读取 Virgin Media TV Go 正常 Guide 页面加载的 Sky Sports Ultra HD 1／2 EPG。

    两台仅采用频道目录中可见的标准内部 ID ``2258``／``2265``；明确排除目录中
    标记为 hidden 的 ``Duplicate`` 镜像。节目事件来自同一官方 Guide 正常请求的
    静态六小时时间片，返回 Unix 秒级 start/end，因此不会推断节目时间。
    """
    if days not in range(1, 8):
        raise ValueError("Virgin Media TV Guide 采集天数必须为 1–7。")
    session = _session()
    channel_response = session.get(
        VIRGIN_UK_CHANNELS,
        params={"cityId": "40980", "language": "en", "productClass": "Orion-DASH", "platform": "web"},
        timeout=30,
    )
    channel_response.raise_for_status()
    try:
        channel_payload = channel_response.json()
    except ValueError as exc:
        raise SourceUnavailable("Virgin Media TV Guide 官方频道目录未返回 JSON。") from exc
    if not isinstance(channel_payload, list):
        raise SourceUnavailable("Virgin Media TV Guide 官方频道目录格式发生变化。")

    channel_names: dict[str, str] = {}
    for channel in channel_payload:
        if not isinstance(channel, dict):
            continue
        channel_id = str(channel.get("id") or "")
        name = (channel.get("name") or "").strip()
        if channel_id in VIRGIN_UK_ULTRA_CHANNELS and not channel.get("isHidden"):
            expected_name = VIRGIN_UK_ULTRA_CHANNELS[channel_id]
            if name != expected_name:
                raise SourceUnavailable(
                    f"Virgin Media 官方频道目录中 {channel_id} 的名称为 {name!r}，与预期的 {expected_name!r} 不一致。"
                )
            channel_names[channel_id] = name
    if set(channel_names) != set(VIRGIN_UK_ULTRA_CHANNELS):
        raise SourceUnavailable("Virgin Media 官方频道目录未同时返回可见的 Sky Sports Ultra HD 1／2。")

    zone = ZoneInfo("Europe/London")
    today = datetime.now(zone).date()
    last_day = today + timedelta(days=days)
    retrieved_at = utc_now_iso()
    records: list[Programme] = []
    for segment_start in _virgin_uk_segment_starts(today, days, zone):
        token = segment_start.strftime("%Y%m%d%H%M%S")
        response = session.get(VIRGIN_UK_EPG_SEGMENT.format(segment=token), timeout=30)
        response.raise_for_status()
        try:
            payload = response.json()
        except ValueError as exc:
            raise SourceUnavailable(f"Virgin Media 官方 EPG 时间片 {token} 未返回 JSON。") from exc
        entries = payload.get("entries") if isinstance(payload, dict) else None
        if not isinstance(entries, list):
            raise SourceUnavailable(f"Virgin Media 官方 EPG 时间片 {token} 格式发生变化。")
        for channel_schedule in entries:
            if not isinstance(channel_schedule, dict):
                continue
            channel_id = str(channel_schedule.get("channelId") or "")
            if channel_id not in channel_names:
                continue
            events = channel_schedule.get("events")
            if not isinstance(events, list):
                continue
            for event in events:
                if not isinstance(event, dict):
                    continue
                title = (event.get("title") or "").strip()
                start_seconds = event.get("startTime")
                end_seconds = event.get("endTime")
                if not (title and isinstance(start_seconds, (int, float)) and isinstance(end_seconds, (int, float))):
                    continue
                start = datetime.fromtimestamp(start_seconds, tz=timezone.utc).astimezone(zone)
                end = datetime.fromtimestamp(end_seconds, tz=timezone.utc).astimezone(zone)
                if end <= start or not (today <= start.date() < last_day):
                    continue
                records.append(
                    Programme(
                        provider="virgin_uk",
                        country="GB",
                        timezone="Europe/London",
                        channel_id=channel_id,
                        channel_number=channel_id,
                        channel_name=channel_names[channel_id],
                        title=title,
                        start_at=start.isoformat(),
                        end_at=end.isoformat(),
                        source_url=VIRGIN_UK_GUIDE,
                        retrieved_at=retrieved_at,
                    )
                )
        time.sleep(pause_seconds)
    records = _deduplicate(records)
    if not records:
        raise SourceUnavailable("Virgin Media 官方 EPG 未返回 Sky Sports Ultra HD 1／2 的目标日期节目记录。")
    return records


def _deduplicate(records: list[Programme]) -> list[Programme]:
    unique: dict[tuple[str, str, str, str, str], Programme] = {}
    for record in records:
        key = (record.provider, record.channel_id, record.start_at, record.end_at or "", record.title)
        unique[key] = record
    return list(unique.values())
