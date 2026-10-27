"""仅调用运营商官网或官方电视提供商页面的节目表采集器。"""

from __future__ import annotations

from datetime import date, datetime, time as clock_time, timedelta, timezone
import gzip
import io
import json
from importlib.resources import files
import re
import time
import unicodedata
from typing import Any
from urllib.parse import urljoin
import xml.etree.ElementTree as ET
from zoneinfo import ZoneInfo

from bs4 import BeautifulSoup
import requests

from .models import Programme, utc_now_iso
from .f1_titles import adapt_f1_title
from .translation_fallback import TitleUntranslatable, translate_programme_title

# Per-run collector notes (renamed channels, skipped untranslatable programmes,
# …).  Collected sequentially by cli.py, which drains them into status.json
# after each provider so one provider's notes never leak into another's.
_collector_notes: list[str] = []


def note(message: str) -> None:
    """Record a non-fatal observation for the current provider run."""
    _collector_notes.append(message)


def drain_notes() -> list[str]:
    """Return and clear the notes recorded since the previous drain."""
    notes = list(_collector_notes)
    _collector_notes.clear()
    return notes

USER_AGENT = "Cathy-epg/0.2 (+https://github.com/waastudios/Cathy-epg; official-source-only research tool)"
ASTRO_API = "https://contenthub-api.eco.astro.com.my/api/v2/search-linear"
ASTRO_GUIDE = "https://www.astro.com.my/content/channels"
# 用户要求仅保留 Astro 官方体育区当前有排期的频道；不按节目标题猜测体育属性。
ASTRO_SPORT_CHANNEL_NUMBERS = frozenset({"801", "802", "803", "804", "805", "806", "810", "811", "812", "813", "814", "815", "816", "817", "818", "819", "820", "821", "822", "826", "831", "832", "833"})
NOW_HK_GUIDE = "https://nowplayer.now.com/tvguide?filterType=all"
NOW_HK_CHANNELS_ZH = "https://nowplayer.now.com/channels?lang=zh&filterType=all"
NOW_HK_EPG = "https://nowplayer.now.com/tvguide/epglist"
# NOW TV 官方目录的体育区频道号；保留官方中英文频道名称和稳定频道 ID。
NOW_HK_SPORT_CHANNEL_NUMBERS = frozenset({"611", "612", "613", "620", "621", "622", "623", "624", "625", "626", "627", "630", "631", "632", "633", "634", "635", "636", "637", "638", "639", "640", "641", "642", "643", "644", "645", "646", "647", "651", "652", "668", "674", "679", "680", "683", "684"})
ALLENTE_GUIDE = "https://www.allente.se/tv-guide/"
ALLENTE_EPG = "https://www.allente.se/api/epg/refetch-epg-data"
# 用户确认的 Allente Sweden V Sport 显示名及 XMLTV ID 后缀。内部频道 ID 仍只用于
# 官方接口匹配；导出的显示名和 XMLTV ID 严格采用此映射，不保留 HD 或 (S)。
ALLENTE_V_SPORT_CHANNELS: dict[str, tuple[str, str]] = {
    "20092": ("V Sport Extra", "vextra"),
    "50048": ("V Sport Motor", "vmotor"),
    "50049": ("V Sport Vinter", "vvin"),
    "50056": ("V Sport Football", "vfoot"),
    "50077": ("V Sport Golf", "vgolf"),
    "50078": ("V Sport Premium", "vpre"),
    "50079": ("V Sport 1", "v1"),
    "50105": ("V Sport UltraHD", "vultra"),
    "50125": ("V Sport Live 1", "vl1"),
    "50126": ("V Sport Live 2", "vl2"),
    "50127": ("V Sport Live 3", "vl3"),
    "50128": ("V Sport Live 4", "vl4"),
    "50129": ("V Sport Live 5", "vl5"),
}
ALLENTE_V_SPORT_IDS = frozenset(ALLENTE_V_SPORT_CHANNELS)
ALLENTE_NO_GUIDE = "https://www.allente.no/tv-guide/"
ALLENTE_NO_EPG = "https://www.allente.no/api/epg/refetch-epg-data"
# 用户确认的 Allente Norway 标准频道显示名及 XMLTV ID 后缀；不收录同节目流的
# 字幕／音频描述镜像。
ALLENTE_NO_CHANNELS: dict[str, tuple[str, str]] = {
    "10009": ("TV Norge", "tvn"),
    "10010": ("FEM", "fem"),
    "10011": ("REX", "rex"),
    "10022": ("Eurosport Norge", "euron"),
    # Allente Norway 官方 EPG 目录中的 Eurosport 1 HD (N)。
    "10091": ("Eurosport 1", "euro1"),
}
ALLENTE_NO_CHANNEL_IDS = frozenset(ALLENTE_NO_CHANNELS)
EE_TV_PLAYER_GUIDE = "https://player.ee.co.uk/#/livetv/schedule"
EE_TV_SCHEDULE = "https://api.youview.tv/metadata/linear/v2/schedule/by-servicelocator"
# tvguide.co.uk 公开 listings API：节目条目自带 image_url（Press Association CDN），
# 用于给 EE TV 系列频道补节目背景图（YouView/EE 官方接口无图片字段）。
TVGUIDE_UK_LISTINGS = "https://api-2.tvguide.co.uk/listings"
TVGUIDE_UK_GUIDE = "https://www.tvguide.co.uk/"
# EE 频道号 -> tvguide.co.uk 频道标题（精确匹配，2026-10-01 实测）。
# TNT Sports 5-10 为溢出频道，tvguide.co.uk 未收录，仍走 EE 官方接口（无图）。
TVGUIDE_UK_EE_CHANNELS: dict[str, str] = {
    "408": "TNT Sports 1 HD",
    "409": "TNT Sports 2 HD",
    "410": "TNT Sports 3 HD",
    "411": "TNT Sports 4 HD",
    "433": "TNT Sports Ultimate",
    "494": "TNT Sports Box Office",
    "418": "Sky Sports News",
    "419": "Sky Sports Main Event HD",
    "420": "Sky Sports Premier League HD",
    "421": "Sky Sports Football HD",
    "422": "Sky Sports Cricket HD",
    "423": "Sky Sports Golf HD",
    "424": "Sky Sports F1 HD",
    "425": "Sky Sports Tennis HD",
    "426": "Sky Sports NFL HD",
    "427": "Sky Sports + HD",
    "428": "Sky Sports Racing HD",
    "429": "Sky Sports Mix",
    "1": "BBC One London HD",
    "2": "BBC Two HD",
    "3": "ITV1 London",
    "4": "Channel 4",
    "6": "ITV2 HD",
    "9": "BBC Four HD",
    "10": "ITV3 HD",
    "23": "BBC Three HD",
    "26": "ITV4 HD",
    "231": "BBC News HD",
    "232": "BBC Parliament",
    "11": "Sky Mix HD",
    "36": "Sky Arts",
    "341": "Sky Witness",
    "342": "Sky Atlantic",
    "346": "Sky One",
    "347": "Sky Comedy",
    "348": "Sky Sci-Fi",
    "349": "Sky Crime",
    "sky-doc": "Sky Documentaries",
    "353": "Sky History",
    "354": "Sky Nature",
}
# 以下映射来自 EE TV Player 匿名公开的线性频道目录；保留用户指定的 TNT Sports SD/UHD 主频道。
# 同一节目流的 HD、+1、字幕／音频描述镜像明确排除，防止跨馈源重复频道。
EE_UK_CHANNELS: tuple[tuple[str, str, str], ...] = (
    ("408", "TNT Sports 1", "http://bds.tv/services/BT_763997"),
    ("409", "TNT Sports 2", "http://bds.tv/services/BT_764001"),
    ("410", "TNT Sports 3", "http://bds.tv/services/BT_768612"),
    ("411", "TNT Sports 4", "http://bds.tv/services/BT_758465"),
    ("433", "TNT Sports Ultimate", "http://bds.tv/services/BT_768397"),
    ("450", "TNT Sports 5", "http://bds.tv/services/BT_767933"),
    ("451", "TNT Sports 6", "http://bds.tv/services/BT_767934"),
    ("452", "TNT Sports 7", "http://bds.tv/services/BT_767935"),
    ("453", "TNT Sports 8", "http://bds.tv/services/BT_767936"),
    ("454", "TNT Sports 9", "http://bds.tv/services/BT_767937"),
    ("455", "TNT Sports 10", "http://bds.tv/services/BT_767938"),
    # EE TV 当前公开节目接口将 CH 494 的官方服务名标为 TNT Sports Box Office HD。
    ("494", "TNT Sports Box Office HD", "http://bds.tv/services/BT_771276"),
    ("418", "Sky Sports News", "http://bds.tv/services/BT_631679_1314_SD"),
    ("419", "Sky Sports Main Event", "http://bds.tv/services/BT_503_1301_SD"),
    ("420", "Sky Sports Premier League", "http://bds.tv/services/BT_768064_1303_SD"),
    ("421", "Sky Sports Football", "http://bds.tv/services/BT_771052_3838_SD"),
    ("422", "Sky Sports Cricket", "http://bds.tv/services/BT_223160_1302_SD"),
    ("423", "Sky Sports Golf", "http://bds.tv/services/BT_750598_1322_SD"),
    ("424", "Sky Sports F1", "http://bds.tv/services/BT_759963_1306_SD"),
    ("425", "Sky Sports Tennis", "http://bds.tv/services/BT_RBM63515_1284_SD"),
    # 2026-09 起官方服务名由 Sky Sports Action 改为 Sky Sports NFL；定位符未变。
    ("426", "Sky Sports NFL", "http://bds.tv/services/BT_397065_1333_SD"),
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
    ("231", "BBC News", "dvb://233a..1100"),
    ("232", "BBC Parliament", "dvb://233a..1280"),
    # Sky 娱乐：优先采用官方 EE 电视（DVB）版；其余仅收录 SD 主 IP 版并排除 HD 镜像。
    ("11", "Sky Mix", "dvb://233a..56c0"),
    ("36", "Sky Arts", "dvb://233a..5680"),
    ("341", "Sky Witness", "http://bds.tv/services/BT_154279_2201_SD"),
    ("342", "Sky Atlantic", "http://bds.tv/services/BT_759409_1412_SD"),
    ("346", "Sky One", "http://bds.tv/services/BT_255_1402_SD"),
    ("347", "Sky Comedy", "http://bds.tv/services/BT_772057_1177_SD"),
    ("348", "Sky Sci-Fi", "http://bds.tv/services/BT_318488_2505_SD"),
    ("349", "Sky Crime", "http://bds.tv/services/BT_753644_1212_SD"),
    # EE Player 官方线性目录与节目接口已验证该服务；公开 EE 频道指南未列出其逻辑频道号。
    ("sky-doc", "Sky Documentaries", "http://bds.tv/services/BT_772169_1127_SD"),
    ("353", "Sky History", "http://bds.tv/services/BT_772170_1875_SD"),
    ("354", "Sky Nature", "http://bds.tv/services/BT_772168_1194_SD"),
)
DIGI4K_GUIDE = "https://www.digi4k.ro/"
# SBB 是塞尔维亚的授权付费电视服务商；以下端点由其匿名 Public EPG 页面正常加载。
SBB_PUBLIC_EPG_GUIDE = "https://epg.sbb.rs/"
SBB_PUBLIC_API = "https://api-web.ug-be.cdn.united.cloud"
# SBB 节目图的官方 CDN 基址（由其前端 JS 公开配置得出）；事件 images 数组里的
# path 为相对路径，拼接后即为可直接引用的官方节目背景图。图片仅做链接引用，
# 不转存。
SBB_IMAGE_CDN = "https://images-web.ug-be.cdn.united.cloud"
SBB_COMMUNITY_ID = "1"
SBB_LANGUAGE_ID = "404"
# SBB 频道目录实测：Eurosport 1 = 84（"Eurosport 1 HD (RS)"），
# Eurosport 2 = 85（"Eurosport 2 HD (RS)"），Eurosport 4K = 1082。
# 元组：(官方源名, 目录位置, XMLTV ID, 展示名)。
SBB_CHANNELS: dict[str, tuple[str, str, str, str]] = {
    "84": ("Eurosport 1 HD (RS)", "121", "eurosport.1", "Eurosport 1"),
    "85": ("Eurosport 2 HD (RS)", "122", "eurosport.2", "Eurosport 2"),
    "1082": ("Eurosport 4K IPTV", "123", "eurosport.4k", "Eurosport 4K"),
}
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

# Telekom MagentaTV 的公开前端配置引用 ThePlatform 官方频道目录与节目表服务。
# ``source name`` 为目录返回的正式名称；导出时依用户要求移除末尾 HD，而保留 UHD。
MAGENTA_TV_GUIDE = "https://www.magenta.tv/"
MAGENTA_TV_CHANNEL_DIRECTORY = (
    "https://feed.entertainment.tv.theplatform.eu/f/mdeprod/"
    "mdeprod-channel-stations-main"
)
MAGENTA_TV_ALL_CHANNEL_SCHEDULES = (
    "https://feed.entertainment.tv.theplatform.eu/f/mdeprod/"
    "mdeprod-all-channel-schedules"
)
MAGENTA_TV_LOCATION_ID = "245991976396"
MAGENTA_TV_SKY_CHANNELS: dict[str, tuple[str, str]] = {
    "Sky Sport Top Event HD": ("201", "Sky Sport Top Event"),
    "Sky Sport Bundesliga HD": ("202", "Sky Sport Bundesliga"),
    "Sky Sport F1 HD": ("203", "Sky Sport F1"),
    "Sky Sport Premier League HD": ("204", "Sky Sport Premier League"),
    "Sky Sport Mix HD": ("205", "Sky Sport Mix"),
    "Sky Sport Tennis HD": ("206", "Sky Sport Tennis"),
    "Sky Sport Golf HD": ("207", "Sky Sport Golf"),
    "Sky Sport UHD": ("209", "Sky Sport UHD"),
    "Sky Sport Bundesliga UHD": ("210", "Sky Sport Bundesliga UHD"),
    **{
        f"Sky Sport Bundesliga {number} HD": (str(210 + number), f"Sky Sport Bundesliga {number}")
        for number in range(1, 11)
    },
    **{
        f"Sky Sport {number} HD": (str(220 + number), f"Sky Sport {number}")
        for number in range(1, 11)
    },
}

# 该映射由仓库当前 Sky Germany 已发布标题审校后固化。刷新时仅查本地资源，
# 因而标题翻译不会受第三方翻译服务、网络或模型输出变化影响。
SKY_DE_TITLE_TRANSLATIONS: dict[str, str] = json.loads(
    files("epg_tool").joinpath("sky_de_title_translations.json").read_text(encoding="utf-8")
)


class SourceUnavailable(RuntimeError):
    """官网无法在当前合规访问范围内读取时抛出。"""


_SKY_DE_FALLBACK_REPLACEMENTS: tuple[tuple[str, str], ...] = (
    ("Alle Spiele, alle Tore", "All Matches, All Goals"),
    ("Die Vodafone Highlight-Show", "The Vodafone Highlights Show"),
    ("Freitags-Konferenz", "Friday Conference"),
    ("Samstags-Konferenz", "Saturday Conference"),
    ("Sonntags-Konferenz", "Sunday Conference"),
    ("Finaltag", "Final Day"),
    ("Halbfinale", "Semi-final"),
    ("Viertelfinale", "Quarter-final"),
    ("Achtelfinale", "Round of 16"),
    ("Rennen Kompakt", "Race Compact"),
    ("Rennen", "Race"),
    ("Sendepause", "Off Air"),
    ("Es folgt:", "Coming up:"),
    ("Topspiel", "Top Match"),
    ("Konferenz", "Conference"),
    ("Spieltag", "Matchday"),
    ("Spielrunde", "Match Round"),
    ("Spiel", "Match"),
    ("Tore", "Goals"),
    ("Finale", "Final"),
    ("Freitag", "Friday"),
    ("Samstag", "Saturday"),
    ("Sonntag", "Sunday"),
    ("Montag", "Monday"),
    ("Dienstag", "Tuesday"),
    ("Mittwoch", "Wednesday"),
    ("Donnerstag", "Thursday"),
    ("Damen", "Women"),
    ("Herren", "Men"),
    ("Fußball", "Football"),
    ("Frauen", "Women"),
    ("Spezial", "Special"),
    ("Die Analyse", "The Analysis"),
    ("Die Show", "The Show"),
    ("Wiederholung", "Repeat"),
    ("Highlights", "Highlights"),
)
_SKY_DE_UNTRANSLATED = re.compile(
    r"\b(?:Alle|Damen|Die|Ein|Es|Finaltag|Folgt|Frauen|Fußball|Halbfinale|Herren|"
    r"Konferenz|Mit|Rennen|Runde|Samstag|Sendepause|Spezial|Spiel|Spieltag|"
    r"Sonntag|Tag|Tore|Topspiel|Training|Viertelfinale|Wiederholung)\b",
    flags=re.IGNORECASE,
)


def _translate_magenta_tv_sky_de_title(title: str) -> str | None:
    """将已收录 Sky Germany 节目标题稳定转换为英文。

    F1 频道标题优先走专属适配（``f1_titles.adapt_f1_title``）：F1/F2/F3/F1 Academy
    的德语标题句式固定，在线翻译对同一句式会产出多种不一致版本（"Azerbaijan GP"
    vs "GP Azerbaijan"、"1. Race" vs "1st Race"），专属适配保证确定性输出。
    其余标题沿用：精确映射 -> 受控固定替换 -> 翻译记忆／在线翻译。
    返回 None 表示标题未被受控规则覆盖，调用方将转入翻译记忆／在线翻译。
    """
    normalised = unicodedata.normalize("NFC", re.sub(r"\s+", " ", title.strip()))
    if not normalised:
        return None
    f1_adapted = adapt_f1_title(normalised)
    if f1_adapted:
        return f1_adapted
    translated = SKY_DE_TITLE_TRANSLATIONS.get(normalised)
    if translated:
        return translated
    translated = normalised
    for source, target in _SKY_DE_FALLBACK_REPLACEMENTS:
        translated = translated.replace(source, target)
    translated = re.sub(r"\b(\d+)\.\s*Tag\b", r"\1 Day", translated)
    translated = re.sub(r"\b(\d+)\.\s*Runde\b", r"\1 Round", translated)
    translated = re.sub(r"\s+", " ", translated).strip()
    if translated == normalised:
        return None
    if _SKY_DE_UNTRANSLATED.search(translated):
        return None
    return translated


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
                channel_number = str(channel.get("stbNumber", ""))
                if channel_number not in ASTRO_SPORT_CHANNEL_NUMBERS:
                    continue
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
    channel_names = {number: name for number, name in channel_names.items() if number in NOW_HK_SPORT_CHANNEL_NUMBERS}
    if not channel_names:
        raise SourceUnavailable("NOW TV 香港官方频道目录未返回预期的体育频道。")
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


_ALLENTE_SE_TITLE_EXACT: dict[str, str] = {
    "Sändningsuppehåll": "Broadcast Break",
    "Formel 1: F1": "Formula 1: F1",
    "Formel 1: Formel 1 Highlights": "Formula 1: Formula 1 Highlights",
    "Premier League Studio: Efterstudio": "Premier League Studio: Post-match Studio",
    "Premier League Studio: Efterstudio med Stryktipset": "Premier League Studio: Post-match Studio with Football Pool",
    "Premier League Studio: Förstudio": "Premier League Studio: Pre-match Studio",
    "Premier League Studio: Förstudio med Stryktipset": "Premier League Studio: Pre-match Studio with Football Pool",
}


def _translate_allente_se_title(title: str) -> str | None:
    """将 Allente Sweden V Sport 官方节目标题转换为可验证的英文。

    此函数在每次瑞典 V Sport 采集时对每个官方节目对象调用。仅进行受控的
    赛事、演播室节目和官方地名转换；返回 None 表示标题未被受控规则覆盖，
    调用方将转入翻译记忆／在线翻译。瑞典语以外的官方专有名词（例如德国或
    挪威队名）保持原样。
    """
    normalised = unicodedata.normalize("NFC", re.sub(r"\s+", " ", title.strip()))
    if not normalised:
        return None
    if normalised in _ALLENTE_SE_TITLE_EXACT:
        return _ALLENTE_SE_TITLE_EXACT[normalised]

    translated = normalised
    replacements = (
        ("Formel 1:", "Formula 1:"),
        ("Ligacupen:", "League Cup:"),
        ("Fri Träning", "Free Practice"),
        ("Fri träning", "Free Practice"),
        ("Träning", "Practice"),
        ("Kval", "Qualifying"),
        ("Storbritanniens GP", "British Grand Prix"),
        ("Tyska Supercupen:", "German Super Cup:"),
        ("Aten", "Athens"),
        ("Nederländerna", "Netherlands"),
    )
    for source, target in replacements:
        translated = translated.replace(source, target)
    translated = re.sub(r"\s+", " ", translated).strip()

    # Use vocabulary rather than generic Nordic diacritics: Mönchengladbach,
    # Nürnberg and Bodö/Glimt are official foreign proper names, not Swedish residue.
    untranslated = re.search(
        r"\b(?:Aten|Avsnitt|Direkt|Efterstudio|Finalen|Formel|Förstudio|Höjdpunkter|Kval|Ligacupen|Mästerskap|Med|Mot|Nederländerna|Sändningsuppehåll|Säsong|Storbritanniens|Stryktipset|Svenska|Svensk|Träning|Tyska|Världscupen|avsnitt|direkt|efterstudio|finalen|förstudio|höjdpunkter|kval|ligacupen|mästerskap|med|mot|nederländerna|sändningsuppehåll|säsong|storbritanniens|stryk|svenska|svensk|träning|tyska|världscupen)\b",
        translated,
        flags=re.IGNORECASE,
    )
    if untranslated:
        return None
    return translated


def collect_allente_v_sport(days: int = 7, pause_seconds: float = 0.25) -> list[Programme]:
    """读取 Allente 瑞典官方 EPG 中全部可公开识别的 V Sport 体育频道节目表。

    每个官方节目标题在写入 XMLTV 前都会执行确定性英文转换和瑞典语残留检查。
    """
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
            channel_name = ALLENTE_V_SPORT_CHANNELS[channel_id][0]
            for item in channel.get("programs", []):
                source_title = (item.get("title") or "").strip()
                try:
                    title = translate_programme_title(source_title, "sv", _translate_allente_se_title)
                except TitleUntranslatable:
                    note(f"Allente Sweden {channel_id} 跳过无法翻译的标题：{source_title!r}")
                    continue
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


_ALLENTE_NO_TITLE_EXACT: dict[str, str] = {
    "Kongen befaler": "Taskmaster Norway",
    "Neste sommer - tegnspråktolket": "Next Summer — sign-language interpreted",
    "Norske Talenter": "Norway's Got Talent",
    "Svenske hyttedrømmer: Militærbrakkene på Fårö": "Swedish Cottage Dreams: The Military Barracks on Faro Island",
}


def _translate_allente_no_title(title: str) -> str | None:
    """将 Allente Norway 官方节目标题转换成可验证的英文。

    此函数在每一次挪威频道采集时对每个官方节目对象调用。只进行赛事类别、
    节目正式名称和明确节目属性的受控转换，不添加选手、比分、场地或其他原始
    页面未提供的细节。返回 None 表示标题未被受控规则覆盖，调用方将转入
    翻译记忆／在线翻译。
    """
    normalised = re.sub(r"\s+", " ", title.strip())
    if not normalised:
        return None
    if normalised in _ALLENTE_NO_TITLE_EXACT:
        return _ALLENTE_NO_TITLE_EXACT[normalised]

    translated = normalised
    replacements = (
        # Official series titles and recurring Norwegian programme labels.
        ("Lottomillionærenes husjakt:", "My Lottery Dream Home:"),
        ("Mysterier på museet:", "Mysteries at the Museum:"),
        ("Drømmen om et øyliv:", "Island Life:"),
        ("Husdrøm på 100 dager:", "100 Day Dream Home:"),
        ("Renoveringsdrømmer Sverige:", "Renovation Dreams Sweden:"),
        ("Svenske hyttedrømmer:", "Swedish Cottage Dreams:"),
        ("Fanget på politiets kamera Sverige:", "Caught on Camera Sweden:"),
        ("Grensevakten Sverige:", "Border Patrol Sweden:"),
        ("T-banen Stockholm:", "Stockholm Metro:"),
        ("Min nabo er morder:", "My Neighbor Is a Murderer:"),
        ("Veiens helter:", "Road Heroes:"),
        ("Bagasjekrigen:", "Baggage Battles:"),
        ("Hvordan den lages:", "How It's Made:"),
        ("Mor og datter pusser opp:", "Mother and Daughter Renovate:"),
        ("Fabelaktig oppussing:", "Fabulous Renovation:"),
        ("Husfikserne:", "House Fixers:"),
        ("Ditt verste mareritt:", "Your Worst Nightmare:"),
        ("Ringenes herre:", "The Lord of the Rings:"),
        ("Kongen befaler UK:", "Taskmaster UK:"),
        ("Kongen befaler", "Taskmaster Norway"),
        ("Neste sommer", "Next Summer"),
        ("Norske Talenter", "Norway's Got Talent"),
        ("Danskebåten", "The Danish Ferry"),
        ("Først til verdens ende", "First to the End of the World"),
        ("Nå eller aldri", "Now or Never"),
        ("16 ukers helvete", "16 Weeks of Hell"),
        ("48 timer", "48 Hours"),
        ("Alle mot alle", "Everyone Against Everyone"),
        ("Bagasjekrigen", "Baggage Battles"),
        ("Solveig og Johns dolce villa", "Solveig and John's Dolce Villa"),
        # Recurring episode descriptions from the official sample.
        ("Timor mistenker løgner", "Timor Suspects Lies"),
        ("Bløff og bedrageri", "Bluff and Fraud"),
        ("Drapsforsøk og hjertesorg", "Attempted Murder and Heartbreak"),
        ("Viser seg å være etterlyst", "Turns Out to Be Wanted"),
        ("Skyttebanen i Brissund", "The Shooting Range in Brissund"),
        ("Maleverkstedet på Öland", "The Painting Workshop on Öland"),
        ("Militærbrakkene på Fårö", "The Military Barracks on Fårö"),
        ("En uke igjen", "One Week Left"),
        ("Hva synes Oscar?", "What Does Oscar Think?"),
        ("Kan den reddes?", "Can It Be Saved?"),
        ("Katta i sekken", "A Cat in the Bag"),
        ("Bevæpnet mann på buss", "Armed Man on a Bus"),
        ("Farlig MC-jakt", "Dangerous Motorcycle Chase"),
        ("Oppfinnsomme tyver", "Ingenious Thieves"),
        ("Skuddveksling mellom gjenger", "Gunfight Between Gangs"),
        ("Underjordisk ranerliga", "Underground Robbery Gang"),
        ("Voldsom motstand", "Violent Resistance"),
        ("Ordensvaktene havner midt i et gjengoppgjør", "Security Guards Caught in a Gang Clash"),
        ("Ung mann får hjertestans på toget", "Young Man Suffers Cardiac Arrest on the Train"),
        ("Sugerøret i donut-hullet mitt", "The Straw in My Donut Hole"),
        ("Ildere, angrip!", "Ferrets, Attack!"),
        ("Døden på landet", "Death in the Countryside"),
        ("Militærbrakkene", "The Military Barracks"),
        ("på Fårö", "on Fårö"),
        ("Passasjerer må evakueres", "Passengers Must Be Evacuated"),
        ("Militær Rettferdighet", "Military Justice"),
        ("tegnspråktolket", "sign-language interpreted"),
        # Sports and event vocabulary.
        ("24-timersløpet fra Le Mans", "24 Hours of Le Mans"),
        ("Terrengsykkel:", "Mountain Biking:"),
        ("Hestesport:", "Equestrian:"),
        ("Hest:", "Equestrian:"),
        ("Båtsport:", "Boating:"),
        ("Friidrett:", "Athletics:"),
        ("Seiling:", "Sailing:"),
        ("Triatlon:", "Triathlon:"),
        ("Sykkel:", "Cycling:"),
        ("Fotball:", "Football:"),
        ("BMX: EM:", "BMX: European Championship:"),
        ("Formel E:", "Formula E:"),
        ("E-sport:", "Esports:"),
        ("Samveldelekene", "Commonwealth Games"),
        ("Helgens høydepunkter", "Weekend Highlights"),
        ("Dagens høydepunkter", "Today's Highlights"),
        ("FedExCup-kavalkaden", "FedExCup Highlights"),
        ("kvinner", "Women"),
        ("Verdenscupåpning", "World Cup Opening"),
        ("Verdenscup", "World Cup"),
        ("VM Aachen", "World Championship, Aachen"),
        ("VM i ", "World Championship in "),
        ("VM:", "World Championship:"),
        ("VM ", "World Championship "),
        ("OL 2024", "Olympic Games 2024"),
        ("Frankrike", "France"),
        ("Spania", "Spain"),
        ("finale", "final"),
        ("menn", "men"),
        ("spesial", "Special"),
        ("Maraton", "Marathon"),
        ("La Vuelta de Espana", "La Vuelta de España"),
        ("U.S Open", "US Open"),
    )
    for source, target in replacements:
        translated = translated.replace(source, target)
    translated = re.sub(r"\s*—\s*", " — ", translated)
    translated = re.sub(r"\s+", " ", translated).strip()

    # Norwegian letters and common unambiguous Norwegian programme/sport terms must never
    # silently enter XMLTV.  Titles that still carry them fall through to the
    # translation memory / online translation instead of failing the source.
    untranslated = re.search(
        r"[æøåÆØÅ]|\b(?:Alpint|Alle|Angrip|Bagasjekrigen|Danskebåten|Direkte|Ditt|E-sport|EM|Etappe|Fabelaktig|FedExCup-kavalkaden|Først|Fotball|Friidrett|Hest|Hestesport|Husdrøm|Husfikserne|Håndball|Helgens|Hjertesorg|Hvordan|Ildere|Ishockey|Kongen|Kvinner|Langrenn|Lottomillionærenes|Løpet|Maraton|Menn|Mor|Nabo|Norge|Norske|Norsk|Nå|Renoveringsdrømmer|Ringenes|Samveldelekene|Seiling|Skiskyting|Skuddveksling|Svømming|Sykkel|Svenske|Terrengsykkel|Triatlon|Veiens|Verdenscup|Verdenscupåpning|VM|øyliv|spesial|tegnspråktolket|timer|ukers)\b",
        translated,
        flags=re.IGNORECASE,
    )
    if untranslated:
        return None
    return translated


def collect_allente_no(days: int = 7, pause_seconds: float = 0.25) -> list[Programme]:
    """读取 Allente Norway 官方 TV Guide 的 TV Norge、REX、FEM、Eurosport Norge 与 Eurosport 1。

    仅使用非字幕／非音频描述的标准频道。每个官方节目标题在写入 XMLTV 前均
    经过英文转换与挪威语残留检查；节目页公开提供精确开始与结束时间。
    """
    session = _session()
    # Allente 的端点偶发截断分块响应；请求同一官方内容时使用 identity 编码可稳定取得完整 JSON。
    session.headers.update({"Accept-Encoding": "identity"})
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
            raise SourceUnavailable("Allente Norway 官方 EPG 响应中未找到预期的 TV Norge、REX、FEM、Eurosport Norge 或 Eurosport 1。")
        for channel in channels:
            channel_id = str(channel.get("id"))
            channel_name = ALLENTE_NO_CHANNELS[channel_id][0]
            for item in channel.get("programs", []):
                source_title = str(item.get("title") or "")
                try:
                    title = translate_programme_title(source_title, "no", _translate_allente_no_title)
                except TitleUntranslatable:
                    note(f"Allente Norway {channel_id} 跳过无法翻译的标题：{source_title!r}")
                    continue
                start = item.get("eventStart")
                end = item.get("eventEnd")
                if not (title and start and end):
                    continue
                raw_splash = (item.get("splashImageUri") or "").strip() or None
                # Allente 下发的 Akamai 链接自带 ?im=Resize,width=600, height=338
                # 裁剪参数：逗号后的空格被编码成 %20 后 CDN 直接回 400。
                # 去掉裁剪参数，直接输出纯净原图链接。
                splash = raw_splash.split("?")[0] if raw_splash else None
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
                        image_url=splash,
                        image_source_url=ALLENTE_NO_GUIDE if splash else None,
                        source_url=ALLENTE_NO_GUIDE,
                        retrieved_at=retrieved_at,
                    )
                )
        time.sleep(pause_seconds)
    return _deduplicate(records)


def _ee_interval_starts(today: date, days: int, zone: ZoneInfo) -> list[datetime]:
    """返回覆盖本地连续日期的 EE Player 十二小时时间窗起点（统一换算为 UTC）。"""
    intervals: list[datetime] = []
    for day_offset in range(days):
        local_midnight = datetime.combine(today + timedelta(days=day_offset), clock_time.min, tzinfo=zone)
        for hour in range(0, 24, 12):
            intervals.append((local_midnight + timedelta(hours=hour)).astimezone(timezone.utc))
    return intervals


def collect_ee_uk_channels(
    days: int = 7, pause_seconds: float = 0.02, only_numbers: set[str] | None = None
) -> list[Programme]:
    """读取 EE TV Player 匿名公开的目标英国标准清晰度频道节目表。

    EE 的 Live TV Schedule 正常加载 YouView 官方节目端点，公开返回单频道的
    ``publishedStartTime`` 与 ``publishedDuration``。频道列表只使用 EE 的 SD
    逻辑频道号，特意排除同一线性流的 HD、+1 及辅助服务镜像，避免重复。
    ``only_numbers`` 传入时只采集指定频道号（用于 tvguide.co.uk 未收录的
    溢出频道补采）。
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
        if only_numbers is not None and channel_number not in only_numbers:
            continue
        channel_records = 0
        # 官方偶尔会重命名服务；采用接口返回的官方名并记录，避免单个改名
        # 让整个 EE 来源失败。
        resolved_name = channel_name
        for interval_start in intervals:
            interval_token = interval_start.strftime("%Y-%m-%dT%HZ/PT12H")
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
                if service_name and service_name != resolved_name:
                    note(
                        f"EE TV Player 服务定位符 {service_locator} 的官方频道名"
                        f"为 {service_name!r}（配置为 {resolved_name!r}），已采用官方名继续采集。"
                    )
                    resolved_name = service_name
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
                        channel_name=resolved_name,
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


def collect_tvguide_uk(days: int = 7, pause_seconds: float = 0.25) -> list[Programme]:
    """从 tvguide.co.uk 公开 listings API 采集 EE TV 系列频道节目单。

    tvguide.co.uk 的节目条目自带 ``image_url``（Press Association CDN），而
    EE/YouView 官方接口无图片字段，因此 EE TV 系列频道改走 tvguide.co.uk。
    每个请求返回约 6 小时窗口，每天请求 0/6/12/18 四个窗口；频道映射见
    ``TVGUIDE_UK_EE_CHANNELS``（TNT Sports 5-10 未被 tvguide 收录，不在此列）。
    标题本身为英文，无需翻译。``provider`` 保持 ``ee_uk`` 以便快照合并时
    整体替换旧 EE 记录。
    """
    if days not in range(1, 8):
        raise ValueError("tvguide.co.uk 采集天数必须为 1–7。")
    session = _session()
    zone = ZoneInfo("Europe/London")
    today = datetime.now(zone).date()
    retrieved_at = utc_now_iso()
    wanted = set(TVGUIDE_UK_EE_CHANNELS.values())
    ee_names = {num: name for num, name, _ in EE_UK_CHANNELS}
    records: list[Programme] = []
    seen: set[str] = set()
    for day_offset in range(days):
        day = today + timedelta(days=day_offset)
        for hour in (0, 6, 12, 18):
            response = session.get(
                TVGUIDE_UK_LISTINGS,
                params={
                    "platform": "sky",
                    "region": "london",
                    "view": "grid",
                    "date": day.isoformat(),
                    "hour": str(hour),
                    "details": "false",
                },
                timeout=30,
            )
            response.raise_for_status()
            payload = response.json()
            if not isinstance(payload, list):
                raise SourceUnavailable("tvguide.co.uk listings 响应不是频道列表。")
            for channel in payload:
                if not isinstance(channel, dict) or channel.get("title") not in wanted:
                    continue
                tv_title = channel["title"]
                # 反查 EE 频道号与频道名，保持 XMLTV 频道标识不变
                ee_number = next(num for num, t in TVGUIDE_UK_EE_CHANNELS.items() if t == tv_title)
                channel_name = ee_names.get(ee_number, tv_title)
                for item in channel.get("schedules", []):
                    if not isinstance(item, dict):
                        continue
                    pa_id = item.get("pa_id")
                    if not pa_id or pa_id in seen:
                        continue
                    seen.add(pa_id)
                    title = (item.get("title") or "").strip()
                    start_raw = item.get("start_at") or ""
                    try:
                        start = datetime.fromisoformat(start_raw.replace("Z", "+00:00")).astimezone(zone)
                    except ValueError:
                        continue
                    if not title:
                        continue
                    duration = item.get("duration")
                    end_at: str | None = None
                    if isinstance(duration, (int, float)) and duration > 0:
                        end_at = (start + timedelta(minutes=duration)).isoformat()
                    image_url = (item.get("image_url") or "").strip() or None
                    # tvguide 的 type 字段：'movie' -> Movie 分类，其余走标题/频道推断。
                    item_type = (item.get("type") or "").strip().lower()
                    item_category = "Movie" if item_type == "movie" else None
                    records.append(
                        Programme(
                            provider="ee_uk",
                            country="GB",
                            timezone="Europe/London",
                            channel_id=ee_number,
                            channel_number=ee_number,
                            channel_name=channel_name,
                            title=title,
                            start_at=start.isoformat(),
                            end_at=end_at,
                            image_url=image_url,
                            image_source_url=TVGUIDE_UK_GUIDE if image_url else None,
                            category=item_category,
                            source_url=TVGUIDE_UK_GUIDE,
                            retrieved_at=retrieved_at,
                        )
                    )
            time.sleep(pause_seconds)
    if not records:
        raise SourceUnavailable("tvguide.co.uk 未返回任何 EE 频道节目条目。")
    note(f"tvguide.co.uk 采集 {len(records)} 条（{len(seen)} 去重），其中有图 {sum(1 for r in records if r.image_url)} 条。")
    return _deduplicate(records)


def collect_ee_uk_with_tvguide(days: int = 7) -> list[Programme]:
    """ee_uk 来源：tvguide.co.uk 采集 40 个匹配频道（含节目图），EE 官方 API
    只补采 tvguide.co.uk 未收录的 6 个 TNT Sports 溢出频道（无图）。"""
    tvguide_records = collect_tvguide_uk(days)
    unmatched = {num for num, _, _ in EE_UK_CHANNELS if num not in TVGUIDE_UK_EE_CHANNELS}
    ee_records = collect_ee_uk_channels(days, only_numbers=unmatched)
    return _deduplicate(tvguide_records + ee_records)


def _digi4k_time(value: str) -> clock_time | None:
    """解析 Digi 4K 官方页面使用的 `Ora HH:MM` 时间标签。"""
    matched = re.search(r"Ora\s+(\d{1,2}):(\d{2})", value)
    if not matched:
        return None
    try:
        return clock_time(hour=int(matched.group(1)), minute=int(matched.group(2)))
    except ValueError:
        return None


_DIGI4K_TITLE_EXACT: dict[str, str] = {
    "Arome din Yucatan": "Aromas of Yucatán",
    "Balistică în spatele casei": "Backyard Ballistics",
    "Balistica în spatele casei": "Backyard Ballistics",
    "Bali: paradisul culinar": "Bali: Culinary Paradise",
    "Cei mai periculoşi vulcani": "The World's Most Dangerous Volcanoes",
    "Cei mai periculoși vulcani": "The World's Most Dangerous Volcanoes",
    "Cum a intrat sushi în America": "How Sushi Came to America",
    "Cum combatem schimbarea climatului": "How We Fight Climate Change",
    "Fluturii: eroii naturii": "Butterflies: Nature's Heroes",
    "Lucrătorii din sălbăticie": "Wild Workers",
    "Minunile oceanului": "Wonders of the Ocean",
    "Misterele apelor fermecate": "Mysteries of Enchanted Waters",
    "Muzică": "Music",
    "O planetă dinamică": "A Dynamic Planet",
    "O planetǎ de bizarerii": "A Planet of Oddities",
    "O planetă de bizarerii": "A Planet of Oddities",
    "Odiseea insulelor greceşti": "Odyssey of the Greek Islands",
    "Odiseea insulelor grecești": "Odyssey of the Greek Islands",
    "Odiseea sepiei": "Cuttlefish Odyssey",
    "Orașul de corali": "City of Coral",
    "Oraşul de corali": "City of Coral",
    "Poveste cu leneș": "A Sloth Story",
    "Poveste cu leneş": "A Sloth Story",
    "Tabăra puilor de urs": "Bear Cub Camp",
    "Urangutanii: Şcoala e o junglă": "Orangutans: School Is a Jungle",
    "Urangutanii: Școala e o junglă": "Orangutans: School Is a Jungle",
    "Valea Rinului: Reclǎdind natura": "The Rhine Valley: Rebuilding Nature",
    "Valea Rinului: Reclădind natura": "The Rhine Valley: Rebuilding Nature",
    "În Munții Nanling": "In the Nanling Mountains",
    "În Munţii Nanling": "In the Nanling Mountains",
    "Maimuțe și mai mult de atât": "Monkeys and More",
    "Maimute si mai mult de atat": "Monkeys and More",
    "Ştiinţa bate ficţiunea": "Science Beats Fiction",
    "Știința bate ficțiunea": "Science Beats Fiction",
}


def _translate_digi4k_title(title: str) -> str | None:
    """将 Digi 4K 官网的罗马尼亚语节目标题转换为可验证的英文。

    此函数在每次 Digi 4K 采集时对每个官方标题调用。仅使用受控的节目名称、
    集数标签和球队名称转换；返回 None 表示标题未被受控规则覆盖，调用方将
    转入翻译记忆／在线翻译。
    """
    normalised = unicodedata.normalize("NFC", re.sub(r"\s+", " ", title.strip()))
    if not normalised:
        return None

    # The official page appends Romanian episode labels after a vertical bar.
    base, separator, suffix = normalised.partition("|")
    base = base.strip()
    translated = _DIGI4K_TITLE_EXACT.get(base, base)

    # Controlled normalisation of Spanish club names published without accents by Digi 4K.
    replacements = (
        ("Alaves", "Alavés"),
        ("Atletico Madrid", "Atlético Madrid"),
        ("Malaga", "Málaga"),
    )
    for source, target in replacements:
        translated = translated.replace(source, target)

    if separator:
        episode = suffix.strip()
        matched = re.fullmatch(r"s(\d+)\s+ep\.\s*(\d+)", episode, flags=re.IGNORECASE)
        if matched:
            translated = f"{translated} — Season {matched.group(1)}, Episode {matched.group(2)}"
        else:
            matched = re.fullmatch(r"ep\.\s*(\d+)", episode, flags=re.IGNORECASE)
            if not matched:
                return None
            translated = f"{translated} — Episode {matched.group(1)}"

    translated = re.sub(r"\s+", " ", translated).strip()
    untranslated = re.search(
        r"[ăâîșşțţǎĂÂÎȘŞȚŢǍ]|\b(?:Arome|din|paradisul|culinar|Balistică|Balistica|spatele|casei|Cei|mai|periculoși|periculoşi|vulcani|Cum|intrat|combatem|schimbarea|climatului|Fluturii|eroii|naturii|Lucrătorii|sălbăticie|Minunile|oceanului|Misterele|apelor|fermecate|Muzică|planetă|bizarerii|Odiseea|insulelor|grecești|greceşti|sepiei|Orașul|Oraşul|corali|Poveste|leneș|leneş|Tabăra|puilor|urs|Urangutanii|Școala|Şcoala|junglă|Valea|Rinului|Reclădind|Reclǎdind|natura|Munții|Munţii|Știința|Ştiinţa|bate|ficțiunea|ficţiunea)\b",
        translated,
        flags=re.IGNORECASE,
    )
    if untranslated:
        return None
    return translated


def collect_digi4k(days: int = 7) -> list[Programme]:
    """解析 Digi 4K 罗马尼亚官网首页公开发布的一周节目表。

    每个官方节目标题在写入 XMLTV 前都会执行确定性英文转换与罗马尼亚语残留
    检查。官网逐日展示开始时间而不总是发布最后一档的结束时间；最后一档的
    XMLTV `stop` 将被省略，而不是根据猜测补写。
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
        raw_items: list[tuple[clock_time, str, str | None]] = []
        for mark in day_node.select("mark.schedule-days-item-hour"):
            start_time = _digi4k_time(mark.get_text(" ", strip=True))
            row = mark.find_parent("div", class_=lambda classes: classes and "flex" in classes)
            title_node = row.select_one("h3") if row else None
            source_title = title_node.get_text(" ", strip=True) if title_node else ""
            img_node = row.select_one(".col-7 figure img") if row else None
            image_url = (img_node.get("src") or "").strip() or None
            if not (start_time and source_title):
                continue
            try:
                title = translate_programme_title(source_title, "ro", _translate_digi4k_title)
            except TitleUntranslatable:
                note(f"Digi 4K 跳过无法翻译的标题：{source_title!r}")
                continue
            raw_items.append((start_time, title, image_url))
        if not raw_items:
            continue
        schedule_day = today + timedelta(days=day_offset)
        raw_items.sort(key=lambda item: item[0])
        for index, (start_time, title, image_url) in enumerate(raw_items):
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
                    image_url=image_url,
                    image_source_url=DIGI4K_GUIDE if image_url else None,
                    source_url=DIGI4K_GUIDE,
                    retrieved_at=retrieved_at,
                )
            )
    if not records:
        raise SourceUnavailable("Digi 4K 官网节目容器未返回可识别的时间和节目标题。")
    return _deduplicate(records)


_SBB_EUROSPORT_TITLE_EXACT: dict[str, str] = {
    "Discovery Golf": "Discovery Golf",
    "Magazin: Cycling Show": "Magazine: Cycling Show",
    "NFL Hard Knocks": "NFL Hard Knocks",
    "UEC BMX Racing European Championship - Pregled": "UEC BMX Racing European Championship - Highlights",
}


def _translate_sbb_eurosport_title(title: str) -> str | None:
    """把 SBB 公共 EPG 的塞尔维亚语 Eurosport 标题转换为可审计英文。

    三个 Eurosport 频道（Eurosport 1/2/4K）共用同一翻译规则。仅转换明确的
    运动、赛事、地点、性别与阶段标记；返回 None 表示标题未被受控规则覆盖，
    调用方将转入翻译记忆／在线翻译。
    """
    normalised = re.sub(r"\s*,\s*", ", ", title.strip())
    normalised = re.sub(r"\s+", " ", normalised)
    if not normalised:
        return None
    if normalised in _SBB_EUROSPORT_TITLE_EXACT:
        return _SBB_EUROSPORT_TITLE_EXACT[normalised]

    translated = normalised
    replacements = (
        ("Olimpijske igre", "Olympic Games"),
        ("olimpijske igre", "Olympic Games"),
        ("Dom olimpijade", "Home of the Olympics"),
        ("dom olimpijade", "Home of the Olympics"),
        ("Dvorana Slavnih", "Hall of Fame"),
        ("Dvorana slavnih", "Hall of Fame"),
        ("Svetska turneja", "World Tour"),
        ("svetska turneja", "World Tour"),
        ("Pariz", "Paris"),
        ("Rim", "Rome"),
        ("Tokio", "Tokyo"),
        ("Brdski biciklizam", "Mountain Biking"),
        ("Biciklizam", "Cycling"),
        ("Drumska trka", "Road Race"),
        ("drumska trka", "road race"),
        ("Jedrenje", "Sailing"),
        ("Konjički sport", "Equestrian"),
        ("Skakanje", "Jumping"),
        ("Ahen", "Aachen"),
        ("Snuker", "Snooker"),
        ("Tenis", "Tennis"),
        ("Triatlon", "Triathlon"),
        ("Svetsko prvenstvo", "World Championship"),
        ("Svetski Šampionat", "World Championship"),
        ("Svetski kup", "World Cup"),
        ("Tur Portugala", "Tour of Portugal"),
        ("Tur Beneluksa", "Benelux Tour"),
        ("Meksiko Siti", "Mexico City"),
        ("Majami", "Miami"),
        ("Džeda", "Jeddah"),
        ("Endurance auto trka", "Endurance car race"),
        ("auto trka", "car race"),
        ("sati Fudžija", "hours of Fuji"),
        ("Fudžija", "Fuji"),
        ("Le Mana", "Le Mans"),
        ("Etapa", "Stage"),
        ("Pregled", "Highlights"),
        ("pregled", "Highlights"),
        ("Runda", "Round"),
        ("Dubl", "Doubles"),
        ("Mešovito", "Mixed"),
        ("Finale", "Final"),
        ("finala", "finals"),
        ("Spust", "Downhill"),
        ("Muškarci", "Men"),
        ("Žene", "Women"),
        ("(M)", "(Men)"),
        ("(Ž)", "(Women)"),
    )
    for source, target in replacements:
        translated = translated.replace(source, target)
    translated = re.sub(r"\b1\s*4 finals\b", "Quarter-finals", translated)
    translated = re.sub(r"\b1\s*2 finals\b", "Semi-finals", translated)
    # "6 sati" / "24 sata" 都是"小时"的塞尔维亚语形式；用词边界替换避免误伤。
    translated = re.sub(r"\bsati\b", "hours", translated)
    translated = re.sub(r"\bsata\b", "hours", translated)
    translated = re.sub(r"\s+", " ", translated).strip(" ,")
    untranslated = re.search(
        r"[čćđšžČĆĐŠŽ]|\b(?:Ahen|Biciklizam|Brdski|Dubl|Etapa|finala|Jedrenje|Konjički|Majami|Meksiko|Mešovito|Pregled|pregled|Runda|Skakanje|Snuker|Spust|Svetski|Svetsko|Svetska|turneja|Olimpijske|olimpijske|igre|Dvorana|Slavnih|olimpijade|Šampionat|Tenis|Triatlon|Tur|Žene|Muškarci)\b",
        translated,
    )
    if untranslated:
        return None
    return translated


def _sbb_public_epg_session() -> requests.Session:
    """创建一次性 SBB Public EPG 匿名会话，不持久化网页短时令牌或任何用户数据。"""
    session = _session()
    session.headers.update({
        "Accept": "application/json",
        "Origin": "https://epg.sbb.rs",
        "Referer": SBB_PUBLIC_EPG_GUIDE,
    })
    guide_response = session.get(SBB_PUBLIC_EPG_GUIDE, timeout=30)
    guide_response.raise_for_status()
    script_matched = re.search(r'''<script[^>]+src=(["']?)([^"'\s>]*?/static/js/app\.[^"'\s>]+\.js)\1''', guide_response.text)
    if not script_matched:
        raise SourceUnavailable("SBB Public EPG 首页未返回当前前端脚本地址。")
    app_response = session.get(urljoin(SBB_PUBLIC_EPG_GUIDE, script_matched.group(2)), timeout=30)
    app_response.raise_for_status()
    matched = re.search(r'Authorization:"Basic ([^"]+)"', app_response.text)
    if not matched:
        raise SourceUnavailable("SBB Public EPG 前端未公开正常匿名令牌初始化配置。")
    token_response = session.post(
        f"{SBB_PUBLIC_API}/oauth/token",
        params={"grant_type": "client_credentials"},
        headers={"Authorization": f"Basic {matched.group(1)}"},
        timeout=30,
    )
    token_response.raise_for_status()
    try:
        token = token_response.json().get("access_token")
    except ValueError as exc:
        raise SourceUnavailable("SBB Public EPG 匿名令牌端点未返回 JSON。") from exc
    if not isinstance(token, str) or not token:
        raise SourceUnavailable("SBB Public EPG 匿名令牌端点未返回访问令牌。")
    session.headers["Authorization"] = f"Bearer {token}"
    return session


def _sbb_events(payload: Any) -> list[dict[str, Any]]:
    """兼容 SBB Public EPG 的列表和可能的对象包装形式。"""
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    if isinstance(payload, dict):
        for value in payload.values():
            if isinstance(value, list):
                return [item for item in value if isinstance(item, dict)]
    return []


def _sbb_event_image_url(event: dict[str, Any]) -> str | None:
    """从 SBB 事件的 images 数组提取官方节目背景图 URL。

    优先取 XL（1920x1080），没有则依次降级到 L / M / S。返回 None 表示该事件
    无可用图片，调用方应省略 image_url 而非填占位图。
    """
    images = event.get("images")
    if not isinstance(images, list):
        return None
    # 按清晰度从高到低的偏好顺序
    preference = ("XL", "L", "M", "S", "STB_XL", "STB_FHD")
    by_size: dict[str, str] = {}
    for image in images:
        if not isinstance(image, dict):
            continue
        path = str(image.get("path") or "").strip()
        size = str(image.get("size") or "").strip()
        if path.startswith("/") and size and size not in by_size:
            by_size[size] = path
    for size in preference:
        if size in by_size:
            return f"{SBB_IMAGE_CDN}{by_size[size]}"
    return None


def collect_sbb_eurosport(days: int = 7) -> list[Programme]:
    """读取 SBB Public EPG 中 Eurosport 1/2/4K 的匿名公开周排期。

    SBB 的普通 Public EPG 页面为每次页面加载新建匿名应用令牌。本采集器每次
    运行都重新获取该公开页面所需令牌，并只在进程内存使用；不保存、重放或读取
    用户登录、Cookie、订阅或播放权限。

    三个 Eurosport 频道一次采集完成；单个频道目录漂移或单个标题无法翻译只会
    跳过该频道／该节目并记入 notes，不会让整个 SBB 来源失败。
    """
    if days not in range(1, 8):
        raise ValueError("SBB Eurosport 采集天数必须为 1–7。")
    session = _sbb_public_epg_session()
    common_params = {"communityId": SBB_COMMUNITY_ID, "languageId": SBB_LANGUAGE_ID}
    directory_response = session.get(
        f"{SBB_PUBLIC_API}/v1/public/channels",
        params={**common_params, "channelType": "TV", "imageSize": "L"},
        timeout=30,
    )
    directory_response.raise_for_status()
    try:
        directory = directory_response.json()
    except ValueError as exc:
        raise SourceUnavailable("SBB Public EPG 频道目录未返回 JSON。") from exc
    directory_items = directory if isinstance(directory, list) else []

    zone = ZoneInfo("Europe/Belgrade")
    today = datetime.now(zone).date()
    last_day = today + timedelta(days=days)
    window_start = datetime.combine(today, clock_time.min, tzinfo=zone).astimezone(timezone.utc)
    window_end = datetime.combine(last_day, clock_time.min, tzinfo=zone).astimezone(timezone.utc) - timedelta(seconds=1)
    retrieved_at = utc_now_iso()
    records: list[Programme] = []

    for channel_id, (source_name, position, xmltv_id, display_name) in SBB_CHANNELS.items():
        matches = [
            item for item in directory_items
            if isinstance(item, dict) and str(item.get("id")) == channel_id
        ]
        if len(matches) != 1:
            note(f"SBB Public EPG 频道目录未返回唯一的频道 {channel_id}（{display_name}），已跳过该频道。")
            continue
        channel = matches[0]
        actual_name = (channel.get("name") or "").strip()
        if actual_name != source_name:
            note(f"SBB 频道 {channel_id} 的官方名为 {actual_name!r}（配置为 {source_name!r}），已采用官方名继续采集。")
        if str(channel.get("position")) != position:
            note(f"SBB 频道 {channel_id}（{actual_name}）的目录位置发生变化，仍按频道 ID 继续采集。")

        events_response = session.get(
            f"{SBB_PUBLIC_API}/v1/public/events/epg",
            params={
                **common_params,
                "cid": channel_id,
                "fromTime": window_start.isoformat(),
                "toTime": window_end.isoformat(),
            },
            timeout=30,
        )
        events_response.raise_for_status()
        try:
            events = _sbb_events(events_response.json())
        except ValueError as exc:
            raise SourceUnavailable(f"SBB Public EPG 频道 {channel_id}（{display_name}）排期未返回 JSON。") from exc
        if not events:
            note(f"SBB Public EPG 未返回频道 {channel_id}（{display_name}）的节目条目，已跳过该频道。")
            continue

        for event in events:
            source_title = str(event.get("title") or "")
            try:
                title = translate_programme_title(source_title, "sr", _translate_sbb_eurosport_title)
            except TitleUntranslatable:
                note(f"SBB {display_name} 跳过无法翻译的标题：{source_title!r}")
                continue
            start_value = event.get("startTime")
            end_value = event.get("endTime")
            if not (isinstance(start_value, str) and isinstance(end_value, str)):
                continue
            try:
                event_start = datetime.fromisoformat(start_value.replace("Z", "+00:00")).astimezone(zone)
                event_end = datetime.fromisoformat(end_value.replace("Z", "+00:00")).astimezone(zone)
            except ValueError:
                continue
            if event_end <= event_start or not (today <= event_start.date() < last_day):
                continue
            image_url = _sbb_event_image_url(event)
            records.append(
                Programme(
                    provider="sbb_rs",
                    country="RS",
                    timezone="Europe/Belgrade",
                    channel_id=channel_id,
                    channel_number=channel_id,
                    channel_name=display_name,
                    title=title,
                    start_at=event_start.isoformat(),
                    end_at=event_end.isoformat(),
                    source_url=SBB_PUBLIC_EPG_GUIDE,
                    retrieved_at=retrieved_at,
                    image_url=image_url,
                    image_source_url=SBB_PUBLIC_EPG_GUIDE if image_url else None,
                )
            )
    records = _deduplicate(records)
    if not records:
        raise SourceUnavailable("SBB Public EPG 未返回目标日期范围内可发布的 Eurosport 节目。")
    return records


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


# 法国 Canal+ 官方节目 API（hodor.canalplus.pro）。token 不可硬编码：每次采集
# 先调 authenticate.json 换取新鲜 token，再按频道拉节目。频道 301 = CANAL+
# 主频道，19 = CANAL+ FOOT。
CANALPLUS_FR_AUTH_URL = (
    "https://hodor.canalplus.pro/api/v2/mycanal/authenticate.json/webapp/6.0"
    "?experiments=beta-test-one-tv-guide:control"
)
CANALPLUS_FR_GUIDE = "https://www.canalplus.com/programme-tv/"
CANALPLUS_FR_CHANNELS: tuple[tuple[str, str, str, int], ...] = (
    ("301", "CANAL+", "canal+.fr", 4),
    ("19", "CANAL+ FOOT", "foot+.fr", 10),
)
CANALPLUS_FR_TITLE_TRANSLATIONS: dict[str, str] = json.loads(
    files("epg_tool").joinpath("canalplus_fr_title_translations.json").read_text(encoding="utf-8")
)
_CANALPLUS_FR_FALLBACK_REPLACEMENTS: tuple[tuple[str, str], ...] = (
    ("Émission", "Broadcast"),
    ("Emission", "Broadcast"),
    ("Saison", "Season"),
    ("Episode", "Episode"),
    ("épisode", "episode"),
    ("Partie", "Part"),
    ("partie", "part"),
    ("Qualifications", "Qualifying"),
    ("qualification", "qualifying"),
    ("journée", "matchday"),
    ("matchday", "matchday"),
    ("Ligue des champions", "Champions League"),
    ("Ligue des Champions", "Champions League"),
    ("Ligue Europa", "Europa League"),
    ("Avant-match", "Pre-match"),
    ("le debrief", "the debrief"),
    ("Débrief", "Debrief"),
    ("debrief", "debrief"),
    ("Doc. Fiction", "Documentary Fiction"),
    ("Doc. Musique", "Music Documentary"),
    ("Doc. ", "Documentary "),
    ("Film Animation", "Animation film"),
    ("Film Drame", "Drama film"),
    ("Film Comédie", "Comedy film"),
    ("Film Horreur", "Horror film"),
    ("Film Policier", "Crime film"),
    ("Film Action", "Action film"),
    ("Film Aventure", "Adventure film"),
    ("Film Fantastique", "Fantasy film"),
    ("Film Suspense", "Thriller film"),
    ("Court métrage", "Short film"),
    ("1re ", "1st "),
    ("1er ", "1st "),
    ("2e ", "2nd "),
    ("3e ", "3rd "),
    ("4e ", "4th "),
    ("5e ", "5th "),
)
_CANALPLUS_FR_UNTRANSLATED = re.compile(
    r"\b(?:avec|dans|des|du|et|la|le|les|pour|sur|une|un|Retour|Meilleurs|meilleurs|direct|directe|directement|"
    r"Rugby|Football|Course|Podium|Décrypté|Détective|Club|Emission|Émission|Saison|Journée|Partie|"
    r"arrache|victoire|incroy)\b",
    flags=re.IGNORECASE,
)


def _translate_canalplus_fr_title(title: str) -> str | None:
    """Canal+ 法语标题的确定性英文映射；无法干净转换时返回 None 走后续流水线。"""
    normalised = re.sub(r"\s+", " ", title).strip()
    if not normalised:
        return None
    hit = CANALPLUS_FR_TITLE_TRANSLATIONS.get(normalised)
    if hit:
        return hit
    translated = normalised
    for source, target in _CANALPLUS_FR_FALLBACK_REPLACEMENTS:
        translated = translated.replace(source, target)
    translated = re.sub(r"\s+", " ", translated).strip()
    if translated != normalised and not _CANALPLUS_FR_UNTRANSLATED.search(translated):
        return translated
    return None


def _canalplus_fr_get(session: requests.Session, url: str, **kwargs) -> requests.Response:
    """Canal+ 官方 API 的弹性 GET：

    - 403：命中频率限制，静默 65 秒后重试；
    - 超时/连接错误：瞬时网络抖动，等待 10 秒后重试；
    - 最多 3 次尝试，仍失败则抛出异常。
    """
    last_error: Exception | None = None
    for attempt in range(3):
        try:
            response = session.get(url, **kwargs)
        except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as exc:
            last_error = exc
            time.sleep(10)
            continue
        if response.status_code == 403:
            last_error = requests.exceptions.HTTPError(f"403 rate limited: {url}")
            time.sleep(65)
            continue
        response.raise_for_status()
        return response
    assert last_error is not None
    raise last_error


def _collect_canalplus_fr_official_channel(
    session: requests.Session,
    headers: dict[str, str],
    token: str,
    channel: tuple[str, str, str, int],
    days: int,
    pause_seconds: float,
) -> tuple[list[Programme], int]:
    """经官方 API 拉取单个 Canal+ 频道 days 天节目；返回 (records, skipped)。"""
    channel_id, channel_name, channel_suffix, channel_position = channel
    zone = ZoneInfo("Europe/Paris")
    retrieved_at = utc_now_iso()
    records: list[Programme] = []
    skipped = 0
    for day_offset in range(days):
        response = _canalplus_fr_get(
            session,
            f"https://hodor.canalplus.pro/api/v2/mycanal/channels/{token}/{channel_id}/broadcasts/day/{day_offset}",
            params={
                "channelPosition": channel_position,
                "displayAvailabilityIcons": "false",
                "displayAccessibilityIcons": "false",
            },
            headers=headers,
            timeout=(5, 20),
        )
        payload = response.json()
        time_slices = payload.get("timeSlices") if isinstance(payload, dict) else None
        if not isinstance(time_slices, list):
            raise SourceUnavailable(f"法国 Canal+ {channel_name} 官方 EPG 未返回 timeSlices。")
        for time_slice in time_slices:
            contents = time_slice.get("contents") if isinstance(time_slice, dict) else None
            if not isinstance(contents, list):
                continue
            for content in contents:
                if not isinstance(content, dict):
                    continue
                title = str(content.get("title") or "").strip()
                subtitle = str(content.get("subtitle") or "").strip()
                start_ms = content.get("startTime")
                end_ms = content.get("endTime")
                if not title or not isinstance(start_ms, (int, float)) or not isinstance(end_ms, (int, float)):
                    continue
                start = datetime.fromtimestamp(start_ms / 1000, tz=timezone.utc).astimezone(zone)
                end = datetime.fromtimestamp(end_ms / 1000, tz=timezone.utc).astimezone(zone)
                if end <= start:
                    continue
                source_display_title = title if not subtitle or subtitle == title else f"{title} — {subtitle}"
                try:
                    display_title = translate_programme_title(
                        source_display_title, "fr", _translate_canalplus_fr_title
                    )
                except TitleUntranslatable:
                    skipped += 1
                    continue
                records.append(
                    Programme(
                        provider="canalplus_fr",
                        country="FR",
                        timezone="Europe/Paris",
                        channel_id=channel_suffix,
                        channel_number=channel_id,
                        channel_name=channel_name,
                        title=display_title,
                        start_at=start.isoformat(),
                        end_at=end.isoformat(),
                        source_url=CANALPLUS_FR_GUIDE,
                        retrieved_at=retrieved_at,
                    )
                )
        time.sleep(pause_seconds)
    return records, skipped



EPGPW_FR_URL = "https://epg.pw/xmltv/epg_FR.xml"
# epg.pw 法国包中的 Canal+ 频道 ID（display-name 匹配验证）。
EPGPW_CANALPLUS_CHANNELS = (
    ("459189", "Canal+", "canal+.fr", "301", "CANAL+"),
    ("557557", "CANAL+FOOT", "foot+.fr", "19", "CANAL+ FOOT"),
)


def _collect_canalplus_fr_epgpw(session: requests.Session) -> tuple[list[Programme], int]:
    """epg.pw 法国区 XMLTV 中的 CANAL+ 主频道与 CANAL+ FOOT（约 2–3 天）。

    官方 API 被限流时的临时兜底。标题为法语，经三级流水线译为英文。
    """
    response = session.get(
        EPGPW_FR_URL,
        headers={"User-Agent": "Mozilla/5.0"},
        timeout=60,
    )
    response.raise_for_status()
    root = ET.fromstring(response.content)
    zone = ZoneInfo("Europe/Paris")
    retrieved_at = utc_now_iso()
    records: list[Programme] = []
    skipped = 0
    for epgpw_id, display_name, channel_suffix, channel_number, channel_name in EPGPW_CANALPLUS_CHANNELS:
        for prog in root.iter("programme"):
            if prog.get("channel") != epgpw_id:
                continue
            start_raw = prog.get("start")
            stop_raw = prog.get("stop")
            title_elem = prog.find("title")
            source_title = (title_elem.text or "").strip() if title_elem is not None else ""
            if not start_raw or not source_title:
                continue
            try:
                # 格式如 "20260929003800 +0000"
                start = datetime.strptime(start_raw, "%Y%m%d%H%M%S %z").astimezone(zone)
                end = datetime.strptime(stop_raw, "%Y%m%d%H%M%S %z").astimezone(zone) if stop_raw else None
            except ValueError:
                continue
            if end is not None and end <= start:
                continue
            try:
                title = translate_programme_title(source_title, "fr", _translate_canalplus_fr_title)
            except TitleUntranslatable:
                skipped += 1
                continue
            records.append(
                Programme(
                    provider="canalplus_fr",
                    country="FR",
                    timezone="Europe/Paris",
                    channel_id=channel_suffix,
                    channel_number=channel_number,
                    channel_name=channel_name,
                    title=title,
                    start_at=start.isoformat(),
                    end_at=end.isoformat() if end else None,
                    source_url=EPGPW_FR_URL,
                    retrieved_at=retrieved_at,
                )
            )
    return records, skipped


def collect_canalplus_fr(days: int = 7, pause_seconds: float = 90.0) -> list[Programme]:
    """读取法国 Canal+ 官方 EPG（CANAL+ 主频道与 CANAL+ FOOT），法语标题译为英文。

    先经 authenticate.json 换取新鲜 token（硬编码 token 会被官方拒绝），再按
    频道拉取当日＋未来 6 天节目。官方接口频率限制极严，请求间隔默认 90 秒，
    完整采集约需 20 分钟。官方 API 不可用时回退到 epg.pw 法国区 XMLTV
    （约 2–3 天）；单个标题无法翻译只跳过该节目，不会让整个来源失败。
    """
    if days not in range(1, 8):
        raise ValueError("法国 Canal+ 采集天数必须为 1–7。")
    session = _session()
    headers = {
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "fr-FR,fr;q=0.6",
        "Origin": "https://www.canalplus.com",
        "Referer": CANALPLUS_FR_GUIDE,
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/145.0.0.0 Safari/537.36",
    }
    records: list[Programme] = []
    skipped = 0
    official_ok = False
    try:
        auth = _canalplus_fr_get(session, CANALPLUS_FR_AUTH_URL, headers=headers, timeout=(5, 20))
        token = auth.json().get("token")
        if not token:
            raise SourceUnavailable("法国 Canal+ 官方认证未返回 token。")
        time.sleep(pause_seconds)
        for channel in CANALPLUS_FR_CHANNELS:
            channel_records, channel_skipped = _collect_canalplus_fr_official_channel(
                session, headers, token, channel, days, pause_seconds
            )
            records.extend(channel_records)
            skipped += channel_skipped
        official_ok = True
    except (SourceUnavailable, requests.exceptions.RequestException) as exc:
        note(f"Canal+ 官方 API 不可用（{exc}），回退到 epg.pw")
    if not official_ok:
        fallback_records, fallback_skipped = _collect_canalplus_fr_epgpw(session)
        records.extend(fallback_records)
        skipped += fallback_skipped
    if skipped:
        note(f"Canal+ {skipped} 档法语标题无法译为英文，已跳过")
    records = _deduplicate(records)
    if not records:
        raise SourceUnavailable("法国 Canal+ 未返回节目记录。")
    return records


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


def _magenta_tv_sky_directory(session: requests.Session) -> list[tuple[int, str, str, str, str]]:
    """从 MagentaTV 官方生产频道目录读取目标 Sky 频道及其目录位置。

    MagentaTV 的节目表按频道目录位置分页，而非按单一站点 ID 查询。目录每页最多
    返回 50 个对象；先完整读取公开目录，才能把用户指定的 Sky 频道号映射为最小的
    官方节目表请求分组。
    """
    catalog: list[dict[str, Any]] = []
    for start in range(1, 5001, 50):
        response = session.get(MAGENTA_TV_CHANNEL_DIRECTORY, params={"range": f"{start}-{start + 49}"}, timeout=60)
        response.raise_for_status()
        try:
            payload = response.json()
        except ValueError as exc:
            raise SourceUnavailable("MagentaTV 官方频道目录未返回 JSON。") from exc
        entries = payload.get("entries") if isinstance(payload, dict) else None
        if not isinstance(entries, list):
            raise SourceUnavailable("MagentaTV 官方频道目录格式发生变化。")
        if not entries:
            break
        catalog.extend(item for item in entries if isinstance(item, dict))
        if len(entries) < 50:
            break
    if not catalog:
        raise SourceUnavailable("MagentaTV 官方频道目录未返回可识别的频道对象。")

    def channel_sort_key(item: dict[str, Any]) -> tuple[int, str]:
        value = item.get("channelNumber")
        return (int(value) if isinstance(value, (int, float)) else 999999, str(value or ""))

    catalog.sort(key=channel_sort_key)
    selected: list[tuple[int, str, str, str, str]] = []
    found_names: set[str] = set()
    for position, item in enumerate(catalog, start=1):
        stations = item.get("stations")
        station = next(iter(stations.values()), {}) if isinstance(stations, dict) else {}
        if not isinstance(station, dict):
            continue
        source_name = (station.get("title") or "").strip()
        configured = MAGENTA_TV_SKY_CHANNELS.get(source_name)
        if not configured:
            continue
        service_id = str(station.get("dt$serviceId") or "").strip()
        if not service_id:
            raise SourceUnavailable(f"MagentaTV Sky 频道 {source_name!r} 缺少官方 service ID。")
        sky_number, display_name = configured
        selected.append((position, source_name, service_id, sky_number, display_name))
        found_names.add(source_name)

    missing = sorted(set(MAGENTA_TV_SKY_CHANNELS) - found_names)
    if missing:
        raise SourceUnavailable(f"MagentaTV 官方频道目录未返回预期 Sky 频道：{', '.join(missing)}。")
    if len(selected) != len(MAGENTA_TV_SKY_CHANNELS):
        raise SourceUnavailable("MagentaTV 官方频道目录返回了重复或不完整的目标 Sky 频道映射。")
    return selected


def _magenta_tv_sky_groups(directory: list[tuple[int, str, str, str, str]]) -> list[tuple[int, int]]:
    """根据 MagentaTV 的 2000 channel-hours 限制构造七日节目表请求区间。"""
    positions = sorted(item[0] for item in directory)
    groups: list[list[int]] = []
    # 11 x 7 x 24 = 1848，保留夏令时切换余量，低于官方接口 2000 channel-hours 上限。
    for position in positions:
        if not groups or position != groups[-1][-1] + 1 or len(groups[-1]) >= 11:
            groups.append([position])
        else:
            groups[-1].append(position)
    return [(group[0], group[-1]) for group in groups]


def collect_magenta_tv_sky_de(days: int = 7, pause_seconds: float = 0.05) -> list[Programme]:
    """读取 Telekom MagentaTV 匿名公开节目表中的 Sky Germany 体育频道。

    官方 ThePlatform 节目表要求 ``byLocationId``、本地日期对应的 ``byListingTime``
    和目录范围。采集器每次运行重新读取官方目录，避免把 Telekom 的内部站点标识
    当作稳定 XMLTV ID；导出 ID 使用用户指定的 Sky Germany 频道号 ``sky_de.<number>``。
    """
    if days not in range(1, 8):
        raise ValueError("MagentaTV Sky Germany 采集天数必须为 1–7。")
    session = _session()
    zone = ZoneInfo("Europe/Berlin")
    today = datetime.now(zone).date()
    last_day = today + timedelta(days=days)
    start_utc = datetime.combine(today, clock_time.min, tzinfo=zone).astimezone(timezone.utc)
    end_utc = datetime.combine(last_day, clock_time.min, tzinfo=zone).astimezone(timezone.utc)
    time_range = f"{start_utc.isoformat().replace('+00:00', 'Z')}~{end_utc.isoformat().replace('+00:00', 'Z')}"
    retrieved_at = utc_now_iso()

    directory = _magenta_tv_sky_directory(session)
    source_mapping = {source_name: (service_id, sky_number, display_name) for _, source_name, service_id, sky_number, display_name in directory}
    expected_numbers = {sky_number for _, _, _, sky_number, _ in directory}
    records: list[Programme] = []

    for range_start, range_end in _magenta_tv_sky_groups(directory):
        response = session.get(
            MAGENTA_TV_ALL_CHANNEL_SCHEDULES,
            params={
                "byListingTime": time_range,
                "byLocationId": MAGENTA_TV_LOCATION_ID,
                "range": f"{range_start}-{range_end}",
            },
            timeout=180,
        )
        response.raise_for_status()
        try:
            payload = response.json()
        except ValueError as exc:
            raise SourceUnavailable("MagentaTV 官方 Sky 节目表未返回 JSON。") from exc
        entries = payload.get("entries") if isinstance(payload, dict) else None
        if not isinstance(entries, list):
            raise SourceUnavailable("MagentaTV 官方 Sky 节目表格式发生变化。")
        for schedule in entries:
            if not isinstance(schedule, dict):
                continue
            stations = schedule.get("stations")
            station = next(iter(stations.values()), {}) if isinstance(stations, dict) else {}
            if not isinstance(station, dict):
                continue
            source_name = (station.get("title") or "").strip()
            configured = source_mapping.get(source_name)
            if not configured:
                continue
            service_id, sky_number, display_name = configured
            returned_service_id = str(station.get("dt$serviceId") or "").strip()
            if returned_service_id != service_id:
                raise SourceUnavailable(
                    f"MagentaTV Sky 频道 {source_name!r} 的 service ID 已从 {service_id!r} 变为 {returned_service_id!r}。"
                )
            listings = schedule.get("listings")
            if not isinstance(listings, list):
                continue
            for listing in listings:
                if not isinstance(listing, dict):
                    continue
                program = listing.get("program")
                source_title = (program.get("title") or "").strip() if isinstance(program, dict) else ""
                try:
                    title = translate_programme_title(source_title, "de", _translate_magenta_tv_sky_de_title)
                except TitleUntranslatable:
                    note(f"MagentaTV Sky Germany {sky_number} 跳过无法翻译的标题：{source_title!r}")
                    continue
                start_ms = listing.get("startTime")
                end_ms = listing.get("endTime")
                if not (title and isinstance(start_ms, (int, float)) and isinstance(end_ms, (int, float))):
                    continue
                start = datetime.fromtimestamp(start_ms / 1000, tz=timezone.utc).astimezone(zone)
                end = datetime.fromtimestamp(end_ms / 1000, tz=timezone.utc).astimezone(zone)
                if end <= start or not (today <= start.date() < last_day):
                    continue
                records.append(
                    Programme(
                        provider="sky_de",
                        country="DE",
                        timezone="Europe/Berlin",
                        channel_id=service_id,
                        channel_number=sky_number,
                        channel_name=display_name,
                        title=title,
                        start_at=start.isoformat(),
                        end_at=end.isoformat(),
                        source_url=MAGENTA_TV_GUIDE,
                        retrieved_at=retrieved_at,
                    )
                )
        time.sleep(pause_seconds)

    records = _deduplicate(records)
    published_numbers = {record.channel_number for record in records}
    missing_numbers = sorted(expected_numbers - published_numbers, key=int)
    if missing_numbers:
        raise SourceUnavailable(f"MagentaTV 官方 Sky 节目表未返回频道号 {', '.join(missing_numbers)} 的节目条目。")
    return records


def _deduplicate(records: list[Programme]) -> list[Programme]:
    unique: dict[tuple[str, str, str, str, str], Programme] = {}
    for record in records:
        key = (record.provider, record.channel_id, record.start_at, record.end_at or "", record.title)
        unique[key] = record
    return list(unique.values())


# Player.pl 是波兰 TVN 集团的官方流媒体平台；其 playerapi 直播节目接口
# 匿名可访问、无视地域限制。以下为用户指定的 5 个体育频道及其 live ID。
PLAYER_PL_GUIDE = "https://player.pl/"
PLAYER_PL_API = "https://player.pl/playerapi"
# live ID -> (XMLTV ID, 展示名)
PLAYER_PL_CHANNELS: dict[int, tuple[str, str]] = {
    57615: ("eurosport1.pl", "Eurosport 1"),
    57616: ("eurosport2.pl", "Eurosport 2"),
    4890061: ("eurosport3.pl", "Eurosport 3"),
    4890062: ("eurosport4.pl", "Eurosport 4"),
    57594: ("ElevenSp.1", "Eleven Sports 1"),
}


def _translate_player_pl_title(title: str) -> str | None:
    """把 Player.pl 的波兰语体育节目标题转换为可审计英文。

    仅转换明确的运动、赛事、阶段与性别标记；返回 None 表示标题未被受控
    规则覆盖，调用方将转入翻译记忆／在线翻译。
    """
    normalised = re.sub(r"\s+", " ", title.strip())
    if not normalised:
        return None

    translated = normalised
    replacements = (
        # 整词组必须排在成分词之前，避免短词先替换破坏长词组。
        ("Driftingowe Mistrzostwa Polski", "Polish Drifting Championship"),
        ("Piłka nożna:", "Football:"),
        ("Kolarstwo górskie:", "Mountain Biking:"),
        ("Kolarstwo:", "Cycling:"),
        ("Tenis:", "Tennis:"),
        ("Snooker:", "Snooker:"),
        ("Formuła 1:", "Formula 1:"),
        ("Formuła 2:", "Formula 2:"),
        ("Wyścigi samochodowe:", "Motorsport:"),
        ("Żużel:", "Speedway:"),
        ("Boks:", "Boxing:"),
        ("MMA:", "MMA:"),
        ("Siatkówka:", "Volleyball:"),
        ("Koszykówka:", "Basketball:"),
        ("Piłka ręczna:", "Handball:"),
        ("Hokej:", "Hockey:"),
        ("Narciarstwo:", "Skiing:"),
        ("Lekkoatletyka:", "Athletics:"),
        ("Pływanie:", "Swimming:"),
        ("Golf:", "Golf:"),
        ("Dart:", "Darts:"),
        ("Igrzyska Olimpijskie:", "Olympic Games:"),
        ("Letnie Igrzyska Olimpijskie", "Summer Olympic Games"),
        ("Zimowe Igrzyska Olimpijskie", "Winter Olympic Games"),
        ("Igrzyska Olimpijskie", "Olympic Games"),
        ("Igrzyska olimpijskie", "Olympic Games"),
        ("igrzyska olimpijskie", "Olympic Games"),
        ("Konkurs na skoczni normalnej", "Normal hill competition"),
        ("konkurs na skoczni normalnej", "normal hill competition"),
        ("na skoczni normalnej", "on the normal hill"),
        ("skocznia normalna", "normal hill"),
        ("Skoki narciarskie", "Ski Jumping"),
        ("skoki narciarskie", "ski jumping"),
        ("Konkurs", "Competition"),
        ("konkurs", "competition"),
        ("Lekkoatletyka", "Athletics"),
        ("Narciarstwo", "Skiing"),
        ("Kolarstwo", "Cycling"),
        ("Siatkówka", "Volleyball"),
        ("Koszykówka", "Basketball"),
        ("Pływanie", "Swimming"),
        ("Tenis", "Tennis"),
        ("Mistrzostwa świata", "World Championship"),
        ("Mistrzostwa Europy", "European Championship"),
        ("Mistrzostwa", "Championship"),
        ("mistrzostwa", "championship"),
        ("Puchar Świata", "World Cup"),
        ("Zawody Pucharu Świata", "World Cup"),
        ("mecz finałowy", "final"),
        ("Mecz finałowy", "Final"),
        ("półfinał", "semi-final"),
        ("Półfinał", "Semi-final"),
        ("ćwierćfinał", "quarter-final"),
        ("Ćwierćfinał", "Quarter-final"),
        ("Wyścig", "Race"),
        ("wyścig", "race"),
        ("Grand Prix", "Grand Prix"),
        ("etap", "stage"),
        ("Etap", "Stage"),
        ("dzień", "day"),
        ("Dzień", "Day"),
        ("mężczyzn", "men's"),
        ("kobiet", "women's"),
        ("gra pojedyncza", "singles"),
        ("gra podwójna", "doubles"),
        ("Galeria Sław", "Hall of Fame"),
        ("Skrót", "Highlights"),
        ("skrót", "highlights"),
        ("Magazyn", "Magazine"),
        ("magazyn", "magazine"),
        ("na żywo", "live"),
        ("Na żywo", "Live"),
        # 波兰语地名 → 英文通用名。
        ("Monachium", "Munich"),
        ("Mediolan", "Milan"),
        ("Lipsk", "Leipzig"),
        ("Paryż", "Paris"),
        ("Rzym", "Rome"),
        ("Londyn", "London"),
        ("Madryt", "Madrid"),
        ("Barcelona", "Barcelona"),
        ("Pekin", "Beijing"),
        ("Poznań", "Poznan"),
        ("Poznaniu", "Poznan"),
        ("Arnhem", "Arnhem"),
        # 整词组优先（避免短词先替换破坏长词组）。
        ("Driftingowe", "Drifting"),
        ("driftingowe", "drifting"),
        ("runda", "round"),
        ("Runda", "Round"),
        ("Polski", "Polish"),
        ("Polskiej", "Polish"),
        ("Polska", "Poland"),
        # 时间表达。
        ("godzinny", "hour"),
        ("godzinna", "hour"),
        ("godzinne", "hour"),
        ("minutowy", "minute"),
        ("minutowa", "minute"),
        # 常见赛事词汇。
        ("zjazd", "downhill"),
        ("Zjazd", "Downhill"),
        ("Turniej", "Tournament"),
        ("turniej", "tournament"),
        ("Wielkiej Brytanii", "of Great Britain"),
        ("Wielka Brytania", "Great Britain"),
        ("rozgrywki", "competition"),
        ("Rozgrywki", "Competition"),
        ("klasie", "class"),
        ("klasy", "class"),
    )
    for source, target in replacements:
        translated = translated.replace(source, target)
    # 波兰语介词 "w"（= in/at）单独成词时替换。
    translated = re.sub(r"\bw\b", "in", translated)
    # 波兰语序数 "4. dzień" → "Day 4"。
    translated = re.sub(
        r"\b(\d+)\.\s+(day|stage|race|Day|Stage|Race)\b",
        lambda m: f"{m.group(2).capitalize()} {m.group(1)}",
        translated,
    )
    translated = re.sub(r"\s+", " ", translated).strip(" ,")
    # 仍含波兰语变音符号或常见未覆盖波兰语词 → 交给翻译记忆／在线翻译。
    untranslated = re.search(
        r"[ąćęłńóśźżĄĆĘŁŃÓŚŹŻ]|\b(?:Piłka|Kolarstwo|Mistrzostwa|Zawody|mecz|wyścig|etap|dzień|sekret|sekrety|sukces|sukcesu|zjazd|Turniej|turniej|oraz|drużyna|podsumowanie|zapowiedź|relacja|studio|gość|goście|igrzyska|olimpijskie|skoki|narciarskie|konkurs|skoczni)\b",
        translated,
        flags=re.IGNORECASE,
    )
    if untranslated:
        return None
    return translated


def _player_pl_epg_request(session: requests.Session, live_ids: list[int], since_ms: int, till_ms: int) -> list[dict]:
    """调用 Player.pl 公开 EPG 接口，返回原始节目列表。"""
    params: list[tuple[str, object]] = [("platform", "BROWSER"), ("4K", "true")]
    params += [("liveId[]", live_id) for live_id in live_ids]
    params += [("since", since_ms), ("till", till_ms)]
    query = "&".join(
        f"{key}={value}" if key != "liveId[]" else "liveId[]=" + str(value)
        for key, value in params
    )
    response = session.get(f"{PLAYER_PL_API}/product/live/epg/list?{query}", timeout=30)
    response.raise_for_status()
    try:
        payload = response.json()
    except ValueError as exc:
        raise SourceUnavailable("Player.pl 公开 EPG 接口未返回 JSON。") from exc
    if not isinstance(payload, list):
        raise SourceUnavailable("Player.pl 公开 EPG 接口未返回节目列表。")
    return payload


def collect_player_pl(days: int = 7, pause_seconds: float = 0.4) -> list[Programme]:
    """读取 Player.pl 匿名公开的 Eurosport 1–4 与 Eleven Sports 1 节目表。

    接口按单日时间窗返回数据；波兰语标题经三级流水线（精确映射→翻译记忆→
    在线 Google/MyMemory）转为英文，单条无法翻译只跳过该节目并记入 notes。
    """
    if days not in range(1, 8):
        raise ValueError("Player.pl 采集天数必须为 1–7。")
    session = _session()
    session.headers.update({"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/126.0"})
    zone = ZoneInfo("Europe/Warsaw")
    today = datetime.now(zone).date()
    retrieved_at = utc_now_iso()
    records: list[Programme] = []

    live_ids = list(PLAYER_PL_CHANNELS)
    for day_offset in range(days):
        day_start = datetime.combine(today + timedelta(days=day_offset), clock_time.min, tzinfo=zone)
        since_ms = int(day_start.timestamp() * 1000)
        till_ms = int((day_start + timedelta(days=1)).timestamp() * 1000)
        programmes: list[dict] | None = None
        last_error: Exception | None = None
        for attempt in range(3):
            try:
                programmes = _player_pl_epg_request(session, live_ids, since_ms, till_ms)
                break
            except (requests.RequestException, SourceUnavailable) as exc:
                last_error = exc
                time.sleep(2 * (attempt + 1))
        if programmes is None:
            raise SourceUnavailable(f"Player.pl 公开 EPG 第 {day_offset + 1} 天请求失败（已重试 3 次）：{last_error}")
        for item in programmes:
            if not isinstance(item, dict):
                continue
            live = item.get("live") or {}
            live_id = live.get("id")
            if live_id not in PLAYER_PL_CHANNELS:
                continue
            xmltv_id, display_name = PLAYER_PL_CHANNELS[live_id]
            source_title = (item.get("title") or "").strip()
            if not source_title:
                continue
            try:
                title = translate_programme_title(source_title, "pl", _translate_player_pl_title)
            except TitleUntranslatable:
                note(f"Player.pl {display_name} 跳过无法翻译的标题：{source_title!r}")
                continue
            try:
                start = datetime.strptime(item["since"], "%Y-%m-%d %H:%M:%S").replace(tzinfo=zone)
                end = datetime.strptime(item["till"], "%Y-%m-%d %H:%M:%S").replace(tzinfo=zone)
            except (KeyError, ValueError, TypeError):
                continue
            records.append(
                Programme(
                    provider="player_pl",
                    country="PL",
                    timezone="Europe/Warsaw",
                    channel_id=xmltv_id,
                    channel_number=xmltv_id,
                    channel_name=display_name,
                    title=title,
                    start_at=start.isoformat(),
                    end_at=end.isoformat(),
                    source_url=PLAYER_PL_GUIDE,
                    retrieved_at=retrieved_at,
                )
            )
        time.sleep(pause_seconds)

    records = _deduplicate(records)
    published = {record.channel_id for record in records}
    missing = [xmltv_id for _, (xmltv_id, _) in PLAYER_PL_CHANNELS.items() if xmltv_id not in published]
    if missing:
        raise SourceUnavailable(f"Player.pl 公开 EPG 未返回频道 {', '.join(missing)} 的节目条目。")
    return records


# Telus TV+（Optik TV）官方网页指南的公开 EPG 接口（AVS 平台）。
# 网页版指南 https://telustvplus.com/#/guide 可匿名加载节目数据；接口需
# restful: yes 请求头。生产环境经 Cloudflare 保护；频道按个回退：生产
# 目录缺失的台由 QA 环境补齐（Travelxp 4K 即属此情况）。
TELUS_TVPLUS_HOSTS = (
    "telus.prod.g.telustvplus.com",
    "telus.qa.watchoptiktv.com",
)
TELUS_TVPLUS_AGL_VERSION = "T7.3"
TELUS_TVPLUS_PLATFORM = "CHROME_FIREFOX_HTML5"
TELUS_TVPLUS_GUIDE = "https://telustvplus.com/#/guide"
# （Telus 官方频道号，官方频道名，tvg-id，展示名）
TELUS_CHANNELS: tuple[tuple[str, str, str, str], ...] = (
    ("713", "Love Nature", "telus.713", "Love Nature"),
    ("716", "Travelxp 4K HDR", "telus.716", "Travelxp 4K"),
    ("900", "TSN1", "telus.900", "TSN1"),
    ("901", "TSN2", "telus.901", "TSN2"),
    ("902", "TSN3", "telus.902", "TSN3"),
    ("903", "TSN4", "telus.903", "TSN4"),
    ("904", "TSN5", "telus.904", "TSN5"),
)
# TSN 主频道在 QA 测试阵容中的别名与 channelId。QA 目录只列出 TSN HD／TSN
# （即 TSN1）与 TSN2 HD，TSN3–TSN5 的主 feed 不出现在目录中，但它们的 EPG
# 容器存在（channelId 625／627／629），故 QA 环境按 channelId 兜底定位；
# 相邻的偶数 channelId（624／626／628）是地区黑屏（Blackout）变体，切勿使用。
# 生产环境目录按官方名 TSN1–TSN5 匹配，不走此兜底。
TELUS_TSN_ALIASES: dict[str, tuple[str, ...]] = {
    "telus.900": ("TSN HD", "TSN"),
    "telus.901": ("TSN2 HD",),
}
TELUS_TSN_QA_CHANNEL_IDS: dict[str, str] = {
    "telus.900": "619",
    "telus.901": "621",
    "telus.902": "625",
    "telus.903": "627",
    "telus.904": "629",
}


def _telus_tvplus_api(host: str, path: str, params: dict[str, str]) -> dict:
    """调用 Telus TV+ AVS 接口，返回解析后的 JSON。"""
    session = _session()
    session.headers.update({"restful": "yes", "Accept": "application/json"})
    url = (
        f"https://{host}/TELUS/{TELUS_TVPLUS_AGL_VERSION}/A/en/"
        f"{TELUS_TVPLUS_PLATFORM}/OPTIK{path}"
    )
    try:
        response = session.get(url, params=params, timeout=30)
    except requests.RequestException as exc:
        raise SourceUnavailable(f"Telus TV+ 接口 {host} 连接失败：{exc}") from exc
    if response.status_code in (401, 403):
        raise SourceUnavailable(f"Telus TV+ 接口 {host} 拒绝访问（HTTP {response.status_code}）。")
    try:
        response.raise_for_status()
    except requests.RequestException as exc:
        raise SourceUnavailable(f"Telus TV+ 接口 {host} 返回 HTTP {response.status_code}。") from exc
    try:
        data = response.json()
    except ValueError as exc:
        raise SourceUnavailable(f"Telus TV+ 接口 {host} 未返回 JSON。") from exc
    if not isinstance(data, dict) or data.get("resultCode") != "OK":
        raise SourceUnavailable(f"Telus TV+ 接口 {host} 返回异常：{str(data)[:120]}")
    return data


def _telus_name_key(name: str) -> str:
    """频道名归一化键：去空格与符号后小写，兼容 "Travel XP 4K" 这类写法差异。"""
    return re.sub(r"[^a-z0-9]", "", name.lower())


def _telus_tvplus_find_channels(host: str) -> dict[str, dict]:
    """在指定环境频道目录中按官方名定位目标频道，返回 {tvg-id: channel_meta}。"""
    data = _telus_tvplus_api(
        host, "/TRAY/LIVECHANNELS", {"orderBy": "orderId", "sortOrder": "asc"}
    )
    containers = (data.get("resultObj") or {}).get("containers") or []
    by_name: dict[str, dict] = {}
    for container in containers:
        metadata = container.get("metadata") or {}
        name = str(metadata.get("channelName") or "").strip()
        if name:
            by_name[_telus_name_key(name)] = metadata
    is_qa = host == TELUS_TVPLUS_HOSTS[1]
    found: dict[str, dict] = {}
    for number, official_name, xmltv_id, display_name in TELUS_CHANNELS:
        metadata = None
        # 先按官方名与已知别名精确匹配（归一化比较，顺序即优先序）。
        for candidate in (official_name, *TELUS_TSN_ALIASES.get(xmltv_id, ())):
            metadata = by_name.get(_telus_name_key(candidate))
            if metadata is not None:
                break
        if metadata is None and xmltv_id in TELUS_TSN_QA_CHANNEL_IDS and is_qa:
            # QA 目录缺少 TSN3–TSN5 主 feed 条目，按实测 channelId 兜底。
            metadata = {
                "channelId": TELUS_TSN_QA_CHANNEL_IDS[xmltv_id],
                "channelName": official_name,
                "defaultChannelNumber": number,
            }
        if metadata is None and xmltv_id not in TELUS_TSN_QA_CHANNEL_IDS:
            # Travelxp 在指南中的名称可能带 HDR 后缀或空格差异，做前缀匹配兜底。
            base = _telus_name_key(official_name.split(" HDR")[0])
            candidates = [
                meta for name, meta in by_name.items() if name.startswith(base)
            ]
            metadata = candidates[0] if len(candidates) == 1 else None
        if metadata is None:
            note(f"Telus TV+（{host}）频道目录未找到 {official_name}，已跳过该频道。")
            continue
        actual_number = str(metadata.get("defaultChannelNumber") or "")
        if actual_number and actual_number != number:
            note(f"Telus {official_name} 的频道号为 {actual_number}（配置为 {number}），仍按频道名继续采集。")
        found[xmltv_id] = metadata
    return found


def _telus_tvplus_fetch_records(
    host: str,
    channels: dict[str, dict],
    days: int,
    pause_seconds: float,
    retrieved_at: str,
) -> list[Programme]:
    """在指定环境按 24 小时切片拉取给定频道的 EPG 记录。"""
    zone_utc = timezone.utc
    now = datetime.now(zone_utc)
    records: list[Programme] = []
    channel_ids = {str(meta.get("channelId")) for meta in channels.values()}
    for day_offset in range(days):
        window_start = (now + timedelta(days=day_offset)).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        window_end = window_start + timedelta(days=1)
        try:
            data = _telus_tvplus_api(
                host,
                "/TRAY/EPG",
                {
                    "filter_startTime": str(int(window_start.timestamp() * 1000)),
                    "filter_endTime": str(int(window_end.timestamp() * 1000)),
                },
            )
        except SourceUnavailable as exc:
            raise SourceUnavailable(f"Telus TV+（{host}）EPG 拉取失败：{exc}") from exc
        containers = (data.get("resultObj") or {}).get("containers") or []
        for container in containers:
            channel_id = str((container.get("metadata") or {}).get("channelId") or "")
            if channel_id not in channel_ids:
                continue
            xmltv_id = next(
                xmltv for xmltv, meta in channels.items()
                if str(meta.get("channelId")) == channel_id
            )
            _, _, _, display_name = next(
                item for item in TELUS_CHANNELS if item[2] == xmltv_id
            )
            for programme in container.get("containers") or []:
                meta = programme.get("metadata") or {}
                title = str(meta.get("title") or "").strip()
                if not title:
                    continue
                try:
                    start_ms = int(meta["airingStartTime"])
                    end_ms = int(meta["airingEndTime"])
                except (KeyError, TypeError, ValueError):
                    continue
                start = datetime.fromtimestamp(start_ms / 1000, tz=zone_utc)
                end = datetime.fromtimestamp(end_ms / 1000, tz=zone_utc)
                if end <= start:
                    continue
                sub_title = str(meta.get("episodeTitle") or "").strip() or None
                description = str(meta.get("longDescription") or "").strip() or None
                genres = meta.get("genres") or []
                category = str(genres[0]).strip() if genres else None
                image_url = str(meta.get("pictureUrl") or "").strip() or None
                records.append(
                    Programme(
                        provider="telus_tvplus",
                        country="CA",
                        timezone="UTC",
                        channel_id=xmltv_id,
                        channel_number="",
                        channel_name=display_name,
                        title=title,
                        start_at=start.isoformat(),
                        end_at=end.isoformat(),
                        source_url=TELUS_TVPLUS_GUIDE,
                        retrieved_at=retrieved_at,
                        image_url=image_url,
                        description=description,
                        category=category,
                        sub_title=sub_title,
                    )
                )
        time.sleep(pause_seconds)
    return records


def collect_telus_tvplus(days: int = 7, pause_seconds: float = 1.0) -> list[Programme]:
    """读取 Telus TV+ 官方指南中 Love Nature、Travelxp 4K 与 TSN 1–5 的节目单。

    频道标题本身为英文，直接发布。环境按频道逐个选：生产环境优先，某台
    在生产目录中缺失（或生产整体不可用）时由 QA 环境补齐该台——Travelxp
    4K 在生产目录中的名称始终未能证实，QA 目录中为 "Travel XP 4K"
    （callLetter TXP4KHDR，channelId 614），其实测 7 天节目单完整。QA
    阵容为测试用，按频道名匹配，TSN3–TSN5 按实测 channelId 兜底。单个
    频道在两个环境都缺失时只跳过并记入 notes，不会让整个来源失败。
    """
    if days not in range(1, 8):
        raise ValueError("Telus TV+ 采集天数必须为 1–7。")
    retrieved_at = utc_now_iso()
    per_host: list[tuple[str, dict[str, dict]]] = []
    last_error = ""
    for host in TELUS_TVPLUS_HOSTS:
        try:
            found = _telus_tvplus_find_channels(host)
        except SourceUnavailable as exc:
            last_error = str(exc)
            note(f"Telus TV+（{host}）不可用：{exc}")
            continue
        per_host.append((host, found))
    assigned: dict[str, dict[str, dict]] = {}
    for host, found in per_host:
        for xmltv_id, meta in found.items():
            if any(xmltv_id in group for group in assigned.values()):
                continue
            assigned.setdefault(host, {})[xmltv_id] = meta
    if not assigned:
        raise SourceUnavailable(f"Telus TV+ 所有环境均不可用：{last_error}")
    qa_filled = sorted(
        xmltv_id
        for host, group in assigned.items()
        if host != TELUS_TVPLUS_HOSTS[0]
        for xmltv_id in group
    )
    if qa_filled:
        note(f"Telus TV+ 频道 {', '.join(qa_filled)} 由 QA 环境补齐（生产环境缺失或不可用）。")
    records: list[Programme] = []
    pending: dict[str, dict[str, dict]] = {h: dict(g) for h, g in assigned.items()}
    # 首轮按指派拉取；某环境 EPG 拉取失败时，其频道改由其它已找到该台的
    # 环境重试一轮，避免「目录可达但 EPG 不可用」时整批丢台。
    for attempt in range(2):
        retry: dict[str, dict[str, dict]] = {}
        for host, group in pending.items():
            if not group:
                continue
            try:
                records.extend(
                    _telus_tvplus_fetch_records(
                        host, group, days, pause_seconds, retrieved_at
                    )
                )
            except SourceUnavailable as exc:
                note(f"Telus TV+（{host}）EPG 拉取失败：{exc}")
                if attempt == 0:
                    for xmltv_id in group:
                        for other_host, found in per_host:
                            if other_host != host and xmltv_id in found:
                                retry.setdefault(other_host, {})[xmltv_id] = found[xmltv_id]
                                break
        pending = retry
        if not pending:
            break
    records = _deduplicate(records)
    published = {record.channel_id for record in records}
    missing = [xmltv_id for _, _, xmltv_id, _ in TELUS_CHANNELS if xmltv_id not in published]
    if missing:
        note(f"Telus TV+ 未返回频道 {', '.join(missing)} 的节目条目。")
    if not records:
        raise SourceUnavailable("Telus TV+ 未返回有效节目记录。")
    return records


# Peacock（NBCUniversal）官方 BFF 频道指南接口。网页端与 App 的频道指南均由
# 该接口驱动，可匿名调用（无账号、无 token），仅需 Sky OTT 平台请求头。
# Tennis Channel 2 是 Peacock 阵容中的线性频道（其阵容内只有 TC2，没有
# Tennis Channel 1），按 serviceKey 定位，用户指定 tvg-id 为 TC2.us。
PEACOCK_GUIDE_API = "https://bff-ext.clients.peacocktv.com/bff/channel_guide"
PEACOCK_GUIDE_PAGE = (
    "https://www.peacocktv.com/channels/tennis-channel-2/8969135442586836117"
)
PEACOCK_TC2_SERVICE_KEY = "8969135442586836117"
PEACOCK_TC2_XMLTV_ID = "TC2.us"
PEACOCK_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/126.0 Safari/537.36"
    ),
    "X-SkyOTT-Device": "COMPUTER",
    "X-SkyOTT-Language": "en",
    "X-SkyOTT-Platform": "PC",
    "X-SkyOTT-Proposition": "NBCUOTT",
    "X-SkyOTT-Territory": "US",
}
# 接口约束：startTime 只能在过去 1 天至未来 2 天之间，单次返回约 30 小时
# 窗口。用四个错开的起点拼接出约「过去 1 天 + 未来 3 天」的滚动覆盖，
# 每日刷新时与增量合并形成持续节目单（该源本身不提供 7 天一次拉满）。
PEACOCK_START_OFFSETS_HOURS = (-23, 1, 25, 47)


def _peacock_channel_guide(start: datetime) -> dict:
    """调用 Peacock BFF 频道指南接口，返回解析后的 JSON。"""
    session = _session()
    session.headers.update(PEACOCK_HEADERS)
    # startTime 需 ISO8601 且完整 URL 编码；向最近的 5 分钟取整以贴合其缓存粒度。
    rounded = start.replace(
        minute=(start.minute // 5) * 5, second=0, microsecond=0
    )
    iso = rounded.strftime("%Y-%m-%dT%H:%M+00:00")
    try:
        response = session.get(
            PEACOCK_GUIDE_API,
            params={"startTime": iso, "contentSegments": "D2C,Free"},
            timeout=60,
        )
    except requests.RequestException as exc:
        raise SourceUnavailable(f"Peacock 指南接口连接失败：{exc}") from exc
    if response.status_code != 200:
        raise SourceUnavailable(
            f"Peacock 指南接口返回 HTTP {response.status_code}：{response.text[:120]}"
        )
    try:
        data = response.json()
    except ValueError as exc:
        raise SourceUnavailable("Peacock 指南接口未返回 JSON。") from exc
    if not isinstance(data, dict) or not isinstance(data.get("channels"), list):
        raise SourceUnavailable("Peacock 指南接口返回结构异常。")
    return data


# Peacock 目标频道：（serviceKey、用户指定 tvg-id、官方频道名、指南页）。
# 标题本身为英文，直接发布。
PEACOCK_CHANNELS = (
    (
        PEACOCK_TC2_SERVICE_KEY,
        PEACOCK_TC2_XMLTV_ID,
        "Tennis Channel 2",
        PEACOCK_GUIDE_PAGE,
    ),
)


def collect_peacock(days: int = 7, pause_seconds: float = 1.0) -> list[Programme]:
    """读取 Peacock 官方指南中目标频道的节目单。

    目标频道为 Tennis Channel 2（TC2.us，标题本身为英文，直接发布）。
    接口单次窗口约 30 小时且起点受限（过去 1 天至未来 2 天），因此 days
    参数不改变其可达范围：固定以四个错开起点拉取并去重合并。某个起点
    失败只记 notes，其余窗口仍可用。
    """
    zone_utc = timezone.utc
    now = datetime.now(zone_utc)
    retrieved_at = utc_now_iso()
    records: list[Programme] = []
    successes = 0
    per_channel: dict[str, int] = {entry[1]: 0 for entry in PEACOCK_CHANNELS}
    for offset_hours in PEACOCK_START_OFFSETS_HOURS:
        start = now + timedelta(hours=offset_hours)
        try:
            data = _peacock_channel_guide(start)
        except SourceUnavailable as exc:
            note(f"Peacock 指南窗口（{offset_hours:+d}h）拉取失败：{exc}")
            continue
        successes += 1
        for (
            service_key,
            xmltv_id,
            channel_name,
            guide_page,
        ) in PEACOCK_CHANNELS:
            channel = next(
                (
                    item
                    for item in data["channels"]
                    if str(item.get("serviceKey") or "") == service_key
                ),
                None,
            )
            if channel is None:
                note(
                    f"Peacock 指南窗口（{offset_hours:+d}h）未包含 {channel_name}。"
                )
                continue
            for item in channel.get("scheduleItems") or []:
                meta = item.get("data") or {}
                title = str(meta.get("title") or "").strip()
                if not title:
                    continue
                try:
                    start_ts = int(item["startTimeUTC"])
                    duration = int(item["durationSeconds"])
                except (KeyError, TypeError, ValueError):
                    continue
                if duration <= 0:
                    continue
                begin = datetime.fromtimestamp(start_ts, tz=zone_utc)
                end = begin + timedelta(seconds=duration)
                description = str(meta.get("description") or "").strip() or None
                images = meta.get("images") or {}
                image_url = str(images.get("16-9") or "").strip() or None
                records.append(
                    Programme(
                        provider="peacock",
                        country="US",
                        timezone="UTC",
                        channel_id=xmltv_id,
                        channel_number="",
                        channel_name=channel_name,
                        title=title,
                        start_at=begin.isoformat(),
                        end_at=end.isoformat(),
                        source_url=guide_page,
                        retrieved_at=retrieved_at,
                        image_url=image_url,
                        description=description,
                    )
                )
                per_channel[xmltv_id] += 1
        time.sleep(pause_seconds)

    records = _deduplicate(records)
    if not successes:
        raise SourceUnavailable("Peacock 指南接口全部窗口均拉取失败。")
    for _service_key, xmltv_id, channel_name, _guide_page in PEACOCK_CHANNELS:
        if not per_channel[xmltv_id]:
            raise SourceUnavailable(
                f"Peacock 指南未返回 {channel_name} 的节目条目。"
            )
    return records


# Pluto TV 官方节目单接口。Pluto TV 是 Paramount Global 自家的免费流媒体
# 平台，其网页端与 App 的指南由该接口驱动，可匿名调用。CBS Sports Golazo
# Network 在 Pluto TV 阵容中名为 "Golazo Network"（slug: golazo-network）。
# Paramount+ 自家 apps-api 仅登录态可用（匿名请求被网关以 400 拒绝），故
# Golazo 改走同属 Paramount 的 Pluto TV 官方指南，用户指定 tvg-id 为
# GolazoNet.us。注意 Pluto 对该频道只提前约 1–2 天发布逐节目明细，更远的
# 日期只有官方发布的整段 "Golazo Network" 占位块，如实收录。
PLUTO_GUIDE_API = "https://api.pluto.tv/v2/channels"
PLUTO_GOLAZO_PAGE = "https://pluto.tv/us/live-tv/golazo-network"
PLUTO_GOLAZO_SLUG = "golazo-network"
PLUTO_GOLAZO_XMLTV_ID = "GolazoNet.us"


def _pluto_guide_window(start: datetime, stop: datetime) -> list[dict]:
    """调用 Pluto TV 指南接口拉取一个时间窗，返回 Golazo 的 timelines 列表。"""
    session = _session()
    fmt = "%Y-%m-%dT%H:%M:%SZ"
    try:
        response = session.get(
            PLUTO_GUIDE_API,
            params={"start": start.strftime(fmt), "stop": stop.strftime(fmt)},
            timeout=60,
        )
    except requests.RequestException as exc:
        raise SourceUnavailable(f"Pluto TV 指南接口连接失败：{exc}") from exc
    if response.status_code != 200:
        raise SourceUnavailable(
            f"Pluto TV 指南接口返回 HTTP {response.status_code}。"
        )
    try:
        data = response.json()
    except ValueError as exc:
        raise SourceUnavailable("Pluto TV 指南接口未返回 JSON。") from exc
    if not isinstance(data, list):
        raise SourceUnavailable("Pluto TV 指南接口返回结构异常。")
    channel = next(
        (item for item in data if item.get("slug") == PLUTO_GOLAZO_SLUG), None
    )
    if channel is None:
        raise SourceUnavailable("Pluto TV 指南未包含 Golazo Network 频道。")
    return channel.get("timelines") or []


def collect_pluto_tv(days: int = 7, pause_seconds: float = 0.5) -> list[Programme]:
    """读取 Pluto TV 官方指南中 Golazo Network 的节目单（tvg-id：GolazoNet.us）。

    标题本身为英文，直接发布。接口按 start/stop 时间窗返回时间线，单窗
    覆盖有限，按 24 小时分窗逐日拉取 days 天并去重合并。
    """
    if days not in range(1, 8):
        raise ValueError("Pluto TV 采集天数必须为 1–7。")
    zone_utc = timezone.utc
    now = datetime.now(zone_utc).replace(minute=0, second=0, microsecond=0)
    retrieved_at = utc_now_iso()
    records: list[Programme] = []
    for day_offset in range(days):
        window_start = now + timedelta(days=day_offset)
        window_stop = window_start + timedelta(days=1)
        timelines = _pluto_guide_window(window_start, window_stop)
        for item in timelines:
            episode = item.get("episode") or {}
            title = str(item.get("title") or episode.get("name") or "").strip()
            if not title:
                continue
            try:
                start = datetime.fromisoformat(
                    str(item["start"]).replace("Z", "+00:00")
                )
                stop = datetime.fromisoformat(
                    str(item["stop"]).replace("Z", "+00:00")
                )
            except (KeyError, TypeError, ValueError):
                continue
            if stop <= start:
                continue
            episode_name = str(episode.get("name") or "").strip()
            sub_title = episode_name if episode_name and episode_name != title else None
            description = str(episode.get("description") or "").strip() or None
            category = str(episode.get("genre") or "").strip() or None
            poster = episode.get("poster16_9") or episode.get("poster") or {}
            image_url = str(poster.get("path") or "").strip() or None
            records.append(
                Programme(
                    provider="pluto_tv",
                    country="US",
                    timezone="UTC",
                    channel_id=PLUTO_GOLAZO_XMLTV_ID,
                    channel_number="",
                    channel_name="Golazo Network",
                    title=title,
                    start_at=start.isoformat(),
                    end_at=stop.isoformat(),
                    source_url=PLUTO_GOLAZO_PAGE,
                    retrieved_at=retrieved_at,
                    image_url=image_url,
                    description=description,
                    category=category,
                    sub_title=sub_title,
                )
            )
        time.sleep(pause_seconds)

    records = _deduplicate(records)
    if not records:
        raise SourceUnavailable("Pluto TV 指南未返回 Golazo Network 的节目条目。")
    return records


# Sling TV 是美国 Live TV 服务；其节目指南由平台方 MoveTV 的 CMS 以公开
# CDN 文件形式发布（Kodi 的 Sling TV 插件同款数据源），频道清单与 24 小时
# 节目窗接口均可匿名访问、无需登录。本采集器只取 USA Network 全国主
# feed（清单中的 USAHD，Gracenote 58452）：USA 4K 为独立 4K 频道、
# ZOOMUSA 为隐藏频道，均不取。标题本身为英文，直接发布。
SLING_CMS_URL = "https://cbd46b77.cdn.cms.movetv.com"
SLING_CHANNELS_URL = SLING_CMS_URL + "/cms/publish3/domain/summary/ums/1.json"
SLING_USA_XMLTV_ID = "usanetwork.us"


def _sling_schedule_window(session: requests.Session, guid: str, window_start: datetime) -> list[dict]:
    """拉取 Sling CMS 的一个 24 小时节目窗（窗口起点为给定 UTC 时间）。"""
    timestamp = window_start.strftime("%y%m%d%H%M")
    url = f"{SLING_CMS_URL}/cms/publish3/channel/schedule/24/{timestamp}/1/{guid}.json"
    response = session.get(url, timeout=30)
    response.raise_for_status()
    data = response.json()
    schedule = data.get("schedule") or {}
    return schedule.get("scheduleList") or []


def collect_sling(days: int = 7, pause_seconds: float = 0.5) -> list[Programme]:
    """读取 Sling TV 官方 CMS 中 USA Network 的节目单（tvg-id：usanetwork.us）。

    标题本身为英文，直接发布。频道 guid 从官方频道清单动态解析（CDN
    发布文件会轮换，写死会过期）；接口按 24 小时分窗返回，逐日拉取
    days 天并去重合并。
    """
    if days not in range(1, 8):
        raise ValueError("Sling TV 采集天数必须为 1–7。")
    session = _session()
    now = datetime.now(timezone.utc)
    retrieved_at = utc_now_iso()
    try:
        listing = session.get(SLING_CHANNELS_URL, timeout=30)
        listing.raise_for_status()
        channels = listing.json().get("channels") or []
    except (requests.RequestException, ValueError) as exc:
        raise SourceUnavailable(f"Sling TV 频道清单拉取失败：{exc}") from exc
    guid = None
    for channel in channels:
        if channel.get("title") == "USAHD":
            guid = channel.get("channel_guid")
            break
    if not guid:
        raise SourceUnavailable("Sling TV 频道清单中未找到 USAHD。")
    records: list[Programme] = []
    for day_offset in range(days):
        window_start = now + timedelta(days=day_offset)
        try:
            slots = _sling_schedule_window(session, guid, window_start)
        except (requests.RequestException, ValueError) as exc:
            raise SourceUnavailable(
                f"Sling TV USA Network 第 {day_offset + 1} 天节目窗拉取失败：{exc}"
            ) from exc
        for slot in slots:
            title = str(slot.get("title") or "").strip()
            if not title:
                continue
            try:
                raw_start = str(slot["schedule_start"]).replace(".000", "")
                raw_stop = str(slot["schedule_stop"]).replace(".000", "")
                start = datetime.fromtimestamp(int(raw_start), tz=timezone.utc)
                stop = datetime.fromtimestamp(int(raw_stop), tz=timezone.utc)
            except (KeyError, TypeError, ValueError):
                continue
            if stop <= start:
                continue
            meta = slot.get("metadata") or {}
            episode_name = str(meta.get("episode_title") or "").strip()
            sub_title = episode_name if episode_name and episode_name != title else None
            description = (
                str(meta.get("description") or meta.get("short_description") or "").strip()
                or None
            )
            genres = meta.get("genre") or slot.get("genre") or []
            category = str(genres[0]).strip() if genres else None
            thumbnail = slot.get("thumbnail") or {}
            image_url = str(thumbnail.get("url") or "").strip() or None
            records.append(
                Programme(
                    provider="sling",
                    country="US",
                    timezone="UTC",
                    channel_id=SLING_USA_XMLTV_ID,
                    channel_number="",
                    channel_name="USA Network",
                    title=title,
                    start_at=start.isoformat(),
                    end_at=stop.isoformat(),
                    source_url=SLING_CHANNELS_URL,
                    retrieved_at=retrieved_at,
                    image_url=image_url,
                    description=description,
                    category=category,
                    sub_title=sub_title,
                )
            )
        time.sleep(pause_seconds)

    records = _deduplicate(records)
    if not records:
        raise SourceUnavailable("Sling TV 指南未返回 USA Network 的节目条目。")
    return records


# EPGSHARE（epgshare01.online）公开 XMLTV 聚合文件。此来源是用户指定的
# 例外：四个 NBC Sports 地区频道（湾区／波士顿／费城／加州）虽在 Peacock
# 上线，但其官方 BFF 指南仅对购买附加包的登录会话下发这四台，匿名无法
# 取得；用户遂指定改用 EPGSHARE 的 US2 文件（其数据按日滚动更新，约
# 4 天覆盖）。只提取这四个频道的主 feed：湾区／波士顿／费城取 HD feed，
# 加州无 HD feed，取节目量并列最高的 SAT feed（Outer Market 为异地黑屏
# 变体、Plus 为溢出频道，均不取）。用户指定 tvg-id 为 NBCSpBay.us 等。
# 2026-10-21 用户再指定同走此例外的 Tennis Channel 主台（TC.us）：
# Peacock 官方指南只有二台（TC2），主台不在其中；Tennis Channel 官网
# 的公开接口仅下发正在播出／下一档两档节目，整段节目表不开放。US2
# 中该台为 Gracenote 数据，已与官网的正在播出／下一档逐分钟核对一致。
# 2026-10-22 用户再指定同走此例外的 Universo（Universo.us）：NBCU
# 旗下全国性西语娱乐频道，US2 文件中该台标题为西班牙语，逐条经分层
# 管线译为英文后发布（与 WSCV 相同规则），其余五台标题为英文直发。
EPGSHARE_US2_URL = "https://epgshare01.online/epgshare01/epg_ripper_US2.xml.gz"
EPGSHARE_CHANNELS: tuple[tuple[str, str, str, str | None], ...] = (
    ("NBC.Sports.Bay.Area.HD.us2", "NBCSpBay.us", "NBC Sports Bay Area", None),
    ("NBC.Sports.Boston.HD.us2", "NBCSpBos.us", "NBC Sports Boston", None),
    ("NBC.Sports.Philadelphia.HD.us2", "NBCSpPhilly.us", "NBC Sports Philadelphia", None),
    ("NBC.Sports.California.SAT.us2", "NBCSpCali.us", "NBC Sports California", None),
    ("Tennis.Channel.HD.us2", "TC.us", "Tennis Channel", None),
    ("UNIVERSO.HD.us2", "Universo.us", "Universo", "es"),
)

# Universo 的常驻节目名确定性映射；未覆盖的标题继续走翻译记忆与
# 在线服务，仍无法译出时跳过该条（与其它翻译源一致）。
EPGSHARE_UNIVERSO_ES_TITLE_TRANSLATIONS = {
    "Programa pagado": "Paid Programming",
}


def _translate_epgshare_universo_es_title(title: str) -> str | None:
    """Universo 西语标题的确定性英文映射；未覆盖返回 None。"""
    normalised = re.sub(r"\s+", " ", title).strip()
    return EPGSHARE_UNIVERSO_ES_TITLE_TRANSLATIONS.get(normalised)


def _epgshare_xmltv_time(value: str) -> datetime:
    """解析 XMLTV 时间（"20261015050000 +0000"）为带时区 datetime。"""
    return datetime.strptime(value.strip(), "%Y%m%d%H%M%S %z")


def collect_epgshare_us_rsn(days: int = 7, pause_seconds: float = 1.0) -> list[Programme]:
    """读取 EPGSHARE US2 文件中六个频道的节目单。

    四个 NBC Sports 地区频道与 Tennis Channel 主台标题本身为英文，
    直接发布；Universo（Universo.us）标题为西班牙语，逐条译为英文
    后发布。整文件为 gzip 压缩的 XMLTV（约 4 天滚动窗口，每日更新），
    下载后流式解析，只保留目标频道在
    [昨日 00:00 UTC, 今日 00:00 UTC + days) 内的条目。单个频道缺失只
    记入 notes；全部缺失才视为来源失败。
    """
    if days not in range(1, 8):
        raise ValueError("EPGSHARE 采集天数必须为 1–7。")
    session = _session()
    try:
        response = session.get(EPGSHARE_US2_URL, timeout=120)
        response.raise_for_status()
        xml_bytes = gzip.decompress(response.content)
    except (requests.RequestException, OSError) as exc:
        raise SourceUnavailable(f"EPGSHARE US2 文件下载失败：{exc}") from exc

    targets = {
        source_id: (xmltv_id, name, source_lang)
        for source_id, xmltv_id, name, source_lang in EPGSHARE_CHANNELS
    }
    zone_utc = timezone.utc
    today = datetime.now(zone_utc).replace(hour=0, minute=0, second=0, microsecond=0)
    window_start = today - timedelta(days=1)
    window_end = today + timedelta(days=days)
    retrieved_at = utc_now_iso()
    records: list[Programme] = []
    # 同一标题在本轮内只走一次翻译管线：结果（含失败）按标题备忘，
    # 避免同一标题在多条节目上重复触发在线服务。
    title_memo: dict[str, str | None] = {}
    try:
        context = ET.iterparse(io.BytesIO(xml_bytes), events=("end",))
        for _event, element in context:
            if element.tag != "programme":
                continue
            source_id = element.get("channel") or ""
            if source_id in targets:
                xmltv_id, channel_name, source_lang = targets[source_id]
                title_node = element.find("title")
                title = (title_node.text or "").strip() if title_node is not None else ""
                if title:
                    if source_lang is not None:
                        if title in title_memo:
                            translated = title_memo[title]
                        else:
                            try:
                                translated = translate_programme_title(
                                    title, source_lang, _translate_epgshare_universo_es_title
                                )
                            except TitleUntranslatable:
                                translated = None
                            title_memo[title] = translated
                        if translated is None:
                            note(f"EPGSHARE {channel_name} 跳过无法翻译的标题：{title!r}")
                            element.clear()
                            continue
                        title = translated
                    try:
                        start = _epgshare_xmltv_time(element.get("start") or "")
                        stop = _epgshare_xmltv_time(element.get("stop") or "")
                    except ValueError:
                        start = stop = None
                    if start is not None and stop is not None and stop > start \
                            and window_start <= start < window_end:
                        sub_node = element.find("sub-title")
                        sub_title = (sub_node.text or "").strip() if sub_node is not None else ""
                        desc_node = element.find("desc")
                        description = (desc_node.text or "").strip() if desc_node is not None else ""
                        category = None
                        for cat_node in element.findall("category"):
                            if cat_node.text and cat_node.text.strip():
                                category = cat_node.text.strip()
                                break
                        icon_node = element.find("icon")
                        image_url = (icon_node.get("src") or "").strip() if icon_node is not None else ""
                        records.append(
                            Programme(
                                provider="epgshare",
                                country="US",
                                timezone="UTC",
                                channel_id=xmltv_id,
                                channel_number="",
                                channel_name=channel_name,
                                title=title,
                                start_at=start.isoformat(),
                                end_at=stop.isoformat(),
                                source_url=EPGSHARE_US2_URL,
                                retrieved_at=retrieved_at,
                                image_url=image_url or None,
                                description=description or None,
                                category=category,
                                sub_title=sub_title if sub_title and sub_title != title else None,
                            )
                        )
            element.clear()
    except ET.ParseError as exc:
        raise SourceUnavailable(f"EPGSHARE US2 文件解析失败：{exc}") from exc

    records = _deduplicate(records)
    published = {record.channel_id for record in records}
    missing = [xmltv_id for _, xmltv_id, _, _ in EPGSHARE_CHANNELS if xmltv_id not in published]
    if missing:
        note(f"EPGSHARE US2 未返回频道 {', '.join(missing)} 的节目条目。")
    if not records:
        raise SourceUnavailable("EPGSHARE US2 未返回目标频道的节目条目。")
    return records


# EPGSHARE US_LOCALS1（与 US2 同一来源的用户指定例外）：地方台文件，
# 只提取迈阿密 Telemundo 51（WSCV-DT）、纽约 NBC 4（WNBC-DT）、
# 洛杉矶 NBC 4（KNBC-DT）与旧金山湾区 NBC（KNTV-DT）四台。
# 地方台不在 Peacock 匿名官方指南内（指南只含全国性线性频道），用户
# 指定与 NBC Sports 地方台同样改走 EPGSHARE。文件为 gzip 压缩的
# XMLTV（约 59 MB、约 4 天滚动、每日更新），下载后以 gzip 流式解析，
# 不整包解压。用户指定 tvg-id 为 WSCV.us、WNBC-NY.us、WNBC-LA.us
# 与 KNTV.us。WSCV 节目标题为西班牙语，逐条经分层管线译为英文；
# 其余三台标题本身为英文，直接发布。
EPGSHARE_LOCALS1_URL = "https://epgshare01.online/epgshare01/epg_ripper_US_LOCALS1.xml.gz"
EPGSHARE_LOCALS_CHANNELS: tuple[tuple[str, str, str, str | None], ...] = (
    ("WSCV-DT.us_locals1", "WSCV.us", "Telemundo 51", "es"),
    ("WNBC-DT.us_locals1", "WNBC-NY.us", "NBC 4 New York", None),
    ("KNBC-DT.us_locals1", "WNBC-LA.us", "NBC 4 Los Angeles", None),
    ("KNTV-DT.us_locals1", "KNTV.us", "NBC Bay Area", None),
)

# WSCV 的常驻节目名确定性映射；未覆盖的标题继续走翻译记忆与在线
# 服务，仍无法译出时跳过该条（与其它翻译源一致）。
EPGSHARE_WSCV_ES_TITLE_TRANSLATIONS = {
    "Programa pagado": "Paid Programming",
}


def _translate_epgshare_wscv_es_title(title: str) -> str | None:
    """WSCV 西语标题的确定性英文映射；未覆盖返回 None。"""
    normalised = re.sub(r"\s+", " ", title).strip()
    return EPGSHARE_WSCV_ES_TITLE_TRANSLATIONS.get(normalised)


def collect_epgshare_us_locals(days: int = 7, pause_seconds: float = 1.0) -> list[Programme]:
    """读取 EPGSHARE US_LOCALS1 文件中四台地方台的节目单。

    WSCV（WSCV.us，台名 Telemundo 51）标题为西班牙语，逐条译为英文
    后发布；WNBC（WNBC-NY.us，台名 NBC 4 New York）、KNBC
    （WNBC-LA.us，台名 NBC 4 Los Angeles）与 KNTV（KNTV.us，台名
    NBC Bay Area）标题本身为英文，直接发布。整文件为 gzip 压缩的
    XMLTV（约 4 天滚动窗口，每日
    更新），以流式方式解析，只保留目标频道在
    [昨日 00:00 UTC, 今日 00:00 UTC + days) 内的条目。单个频道缺失
    只记入 notes；全部缺失才视为来源失败。
    """
    if days not in range(1, 8):
        raise ValueError("EPGSHARE 采集天数必须为 1–7。")
    session = _session()
    try:
        response = session.get(EPGSHARE_LOCALS1_URL, timeout=180)
        response.raise_for_status()
        xml_stream = gzip.GzipFile(fileobj=io.BytesIO(response.content))
    except (requests.RequestException, OSError) as exc:
        raise SourceUnavailable(f"EPGSHARE US_LOCALS1 文件下载失败：{exc}") from exc

    targets = {
        source_id: (xmltv_id, name, source_lang)
        for source_id, xmltv_id, name, source_lang in EPGSHARE_LOCALS_CHANNELS
    }
    zone_utc = timezone.utc
    today = datetime.now(zone_utc).replace(hour=0, minute=0, second=0, microsecond=0)
    window_start = today - timedelta(days=1)
    window_end = today + timedelta(days=days)
    retrieved_at = utc_now_iso()
    records: list[Programme] = []
    # 同一标题在本轮内只走一次翻译管线：结果（含失败）按标题备忘，
    # 避免同一标题在多条节目上重复触发在线服务。
    title_memo: dict[str, str | None] = {}
    try:
        context = ET.iterparse(xml_stream, events=("end",))
        for _event, element in context:
            if element.tag != "programme":
                continue
            source_id = element.get("channel") or ""
            if source_id in targets:
                xmltv_id, channel_name, source_lang = targets[source_id]
                title_node = element.find("title")
                title = (title_node.text or "").strip() if title_node is not None else ""
                if title:
                    if source_lang is not None:
                        if title in title_memo:
                            translated = title_memo[title]
                        else:
                            try:
                                translated = translate_programme_title(
                                    title, source_lang, _translate_epgshare_wscv_es_title
                                )
                            except TitleUntranslatable:
                                translated = None
                            title_memo[title] = translated
                        if translated is None:
                            note(f"EPGSHARE {channel_name} 跳过无法翻译的标题：{title!r}")
                            element.clear()
                            continue
                        title = translated
                    try:
                        start = _epgshare_xmltv_time(element.get("start") or "")
                        stop = _epgshare_xmltv_time(element.get("stop") or "")
                    except ValueError:
                        start = stop = None
                    if start is not None and stop is not None and stop > start \
                            and window_start <= start < window_end:
                        sub_node = element.find("sub-title")
                        sub_title = (sub_node.text or "").strip() if sub_node is not None else ""
                        desc_node = element.find("desc")
                        description = (desc_node.text or "").strip() if desc_node is not None else ""
                        category = None
                        for cat_node in element.findall("category"):
                            if cat_node.text and cat_node.text.strip():
                                category = cat_node.text.strip()
                                break
                        icon_node = element.find("icon")
                        image_url = (icon_node.get("src") or "").strip() if icon_node is not None else ""
                        records.append(
                            Programme(
                                provider="epgshare",
                                country="US",
                                timezone="UTC",
                                channel_id=xmltv_id,
                                channel_number="",
                                channel_name=channel_name,
                                title=title,
                                start_at=start.isoformat(),
                                end_at=stop.isoformat(),
                                source_url=EPGSHARE_LOCALS1_URL,
                                retrieved_at=retrieved_at,
                                image_url=image_url or None,
                                description=description or None,
                                category=category,
                                sub_title=sub_title if sub_title and sub_title != title else None,
                            )
                        )
            element.clear()
    except ET.ParseError as exc:
        raise SourceUnavailable(f"EPGSHARE US_LOCALS1 文件解析失败：{exc}") from exc

    records = _deduplicate(records)
    published = {record.channel_id for record in records}
    missing = [xmltv_id for _, xmltv_id, _, _ in EPGSHARE_LOCALS_CHANNELS if xmltv_id not in published]
    if missing:
        note(f"EPGSHARE US_LOCALS1 未返回频道 {', '.join(missing)} 的节目条目。")
    if not records:
        raise SourceUnavailable("EPGSHARE US_LOCALS1 未返回目标频道的节目条目。")
    return records


def collect_epgshare(days: int = 7, pause_seconds: float = 1.0) -> list[Programme]:
    """EPGSHARE 统一入口：US2 的六台（NBC Sports 四台、Tennis Channel、Universo）加 US_LOCALS1 的四台地方台。

    两个文件相互独立：单个文件失败只记入 notes 并降级为部分结果，
    两个都未返回条目时才视为来源失败。
    """
    records: list[Programme] = []
    for collector in (collect_epgshare_us_rsn, collect_epgshare_us_locals):
        try:
            records.extend(collector(days, pause_seconds))
        except SourceUnavailable as exc:
            note(f"EPGSHARE 子来源失败：{exc}")
    if not records:
        raise SourceUnavailable("EPGSHARE 两个文件均未返回目标频道的节目条目。")
    return _deduplicate(records)
