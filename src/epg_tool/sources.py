"""仅调用运营商官网或官方电视提供商页面的节目表采集器。"""

from __future__ import annotations

from datetime import date, datetime, time as clock_time, timedelta, timezone
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

USER_AGENT = "Cathy-epg/0.2 (+https://github.com/waastudios/Cathy-epg; official-source-only research tool)"
ASTRO_API = "https://contenthub-api.eco.astro.com.my/api/v2/search-linear"
ASTRO_GUIDE = "https://www.astro.com.my/content/channels"
# 用户要求仅保留 Astro 官方体育区当前有排期的频道；不按节目标题猜测体育属性。
ASTRO_SPORT_CHANNEL_NUMBERS = frozenset({"801", "802", "803", "804", "805", "806", "810", "811", "812", "813", "814", "815", "817", "818", "819", "820", "821", "822", "826", "831", "832", "833"})
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
CANALPLUS_FR_GUIDE = "https://www.canalplus.com/live-tv/programme-tv/"
CANALPLUS_FR_API_BASE = "https://hodor.canalplus.pro/api/v2/mycanal/channels/b63a43e7548cb1a6e7c7319084f48af8"
CANALPLUS_FR_SPORT_CHANNELS: tuple[tuple[str, str, str, int], ...] = (
    ("83", "CANAL+ SPORT 360", "canalplus_sport360", 9),
    ("19", "CANAL+ FOOT", "canalplus_foot", 10),
    ("177", "CANAL+ SPORT", "canalplus_sport", 11),
)
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
TVPLUS_EUROSPORT_1_GUIDE = "https://tvplus.com.tr/canli-tv/yayin-akisi/eurosport-1-hd--77"
TVPLUS_EUROSPORT_2_GUIDE = "https://tvplus.com.tr/canli-tv/yayin-akisi/eurosport-2-hd--106"
# SBB 是塞尔维亚的授权付费电视服务商；以下端点由其匿名 Public EPG 页面正常加载。
SBB_PUBLIC_EPG_GUIDE = "https://epg.sbb.rs/"
SBB_PUBLIC_API = "https://api-web.ug-be.cdn.united.cloud"
SBB_COMMUNITY_ID = "1"
SBB_LANGUAGE_ID = "404"
SBB_EUROSPORT_4K_CHANNEL_ID = "1082"
SBB_EUROSPORT_4K_CHANNEL_NUMBER = "123"
SBB_EUROSPORT_4K_SOURCE_NAME = "Eurosport 4K IPTV"
SBB_EUROSPORT_4K_NAME = "Eurosport 4K"
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


def _translate_magenta_tv_sky_de_title(title: str) -> str:
    """将已收录 Sky Germany 节目标题稳定转换为英文。

    优先使用随代码版本控制的精确映射；对未出现过但仅含受控体育词汇的标题
    使用固定替换。若仍检测到未覆盖的德语，整个 Sky 来源失败而非发布原文，
    以便在下一次代码更新中显式审校并固定新翻译。
    """
    normalised = unicodedata.normalize("NFC", re.sub(r"\s+", " ", title.strip()))
    if not normalised:
        raise SourceUnavailable("MagentaTV Sky Germany 官方节目对象缺少可翻译的标题。")
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
        raise SourceUnavailable(f"MagentaTV Sky Germany 标题不在已审校的英文映射或受控词汇范围内：{title!r}")
    if _SKY_DE_UNTRANSLATED.search(translated):
        raise SourceUnavailable(f"MagentaTV Sky Germany 标题未获得可验证的英文转换：{title!r}")
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


def _translate_allente_se_title(title: str) -> str:
    """将 Allente Sweden V Sport 官方节目标题转换为可验证的英文。

    此函数在每次瑞典 V Sport 采集时对每个官方节目对象调用。仅进行受控的
    赛事、演播室节目和官方地名转换；未覆盖的瑞典语残留会使来源失败，避免
    在 XMLTV 中发布瑞典语标题。瑞典语以外的官方专有名词（例如德国或挪威
    队名）保持原样。
    """
    normalised = unicodedata.normalize("NFC", re.sub(r"\s+", " ", title.strip()))
    if not normalised:
        raise SourceUnavailable("Allente Sweden 官方节目对象缺少可翻译的标题。")
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
        raise SourceUnavailable(f"Allente Sweden 标题未获得可验证的英文转换：{title!r}")
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
                title = _translate_allente_se_title(source_title)
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


def _translate_allente_no_title(title: str) -> str:
    """将 Allente Norway 官方节目标题转换成可验证的英文。

    此函数在每一次挪威频道采集时对每个官方节目对象调用。只进行赛事类别、
    节目正式名称和明确节目属性的受控转换，不添加选手、比分、场地或其他原始
    页面未提供的细节。若检测到未覆盖的挪威语，来源明确失败而不发布原文。
    """
    normalised = re.sub(r"\s+", " ", title.strip())
    if not normalised:
        raise SourceUnavailable("Allente Norway 官方节目对象缺少可翻译的标题。")
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
    # silently enter XMLTV. The source fails so the daily workflow records the issue instead.
    untranslated = re.search(
        r"[æøåÆØÅ]|\b(?:Alpint|Alle|Angrip|Bagasjekrigen|Danskebåten|Direkte|Ditt|E-sport|EM|Etappe|Fabelaktig|FedExCup-kavalkaden|Først|Fotball|Friidrett|Hest|Hestesport|Husdrøm|Husfikserne|Håndball|Helgens|Hjertesorg|Hvordan|Ildere|Ishockey|Kongen|Kvinner|Langrenn|Lottomillionærenes|Løpet|Maraton|Menn|Mor|Nabo|Norge|Norske|Norsk|Nå|Renoveringsdrømmer|Ringenes|Samveldelekene|Seiling|Skiskyting|Skuddveksling|Svømming|Sykkel|Svenske|Terrengsykkel|Triatlon|Veiens|Verdenscup|Verdenscupåpning|VM|øyliv|spesial|tegnspråktolket|timer|ukers)\b",
        translated,
        flags=re.IGNORECASE,
    )
    if untranslated:
        raise SourceUnavailable(f"Allente Norway 标题未获得可验证的英文转换：{title!r}")
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
                title = _translate_allente_no_title(source_title)
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
    """返回覆盖本地连续日期的 EE Player 十二小时时间窗起点（统一换算为 UTC）。"""
    intervals: list[datetime] = []
    for day_offset in range(days):
        local_midnight = datetime.combine(today + timedelta(days=day_offset), clock_time.min, tzinfo=zone)
        for hour in range(0, 24, 12):
            intervals.append((local_midnight + timedelta(hours=hour)).astimezone(timezone.utc))
    return intervals


def _canalplus_fr_image_url(value: object) -> str | None:
    if not isinstance(value, str) or not value.strip():
        return None
    return (
        value.replace("{resolutionXY}", "254x143")
        .replace("{imageQualityPercentage}", "80")
        .replace("\\u002F", "/")
        .replace("\\u0026", "&")
    )


def collect_canalplus_fr_sport(days: int = 7, pause_seconds: float = 0.02) -> list[Programme]:
    """读取法国 Canal+ 官方节目表中的三个体育频道。"""
    if days not in range(1, 9):
        raise ValueError("法国 Canal+ 采集天数必须为 1–8。")
    session = _session()
    zone = ZoneInfo("Europe/Paris")
    retrieved_at = utc_now_iso()
    records: list[Programme] = []
    for channel_id, channel_name, channel_suffix, channel_position in CANALPLUS_FR_SPORT_CHANNELS:
        for day_offset in range(days):
            response = session.get(
                f"{CANALPLUS_FR_API_BASE}/{channel_id}/broadcasts/day/{day_offset}",
                params={
                    "channelPosition": channel_position,
                    "displayAvailabilityIcons": "false",
                    "displayAccessibilityIcons": "false",
                },
                headers={
                    "Accept": "application/json, text/plain, */*",
                    "Origin": "https://www.canalplus.com",
                    "Referer": CANALPLUS_FR_GUIDE,
                    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36",
                },
                timeout=(5, 20),
            )
            response.raise_for_status()
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
                    display_title = title if not subtitle or subtitle == title else f"{title} — {subtitle}"
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
                            image_url=_canalplus_fr_image_url(content.get("URLImage")),
                            image_source_url=CANALPLUS_FR_GUIDE,
                        )
                    )
            time.sleep(pause_seconds)
    records = _deduplicate(records)
    if not records:
        raise SourceUnavailable("法国 Canal+ 官方体育 EPG 未返回节目记录。")
    return records


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


def _translate_digi4k_title(title: str) -> str:
    """将 Digi 4K 官网的罗马尼亚语节目标题转换为可验证的英文。

    此函数在每次 Digi 4K 采集时对每个官方标题调用。仅使用受控的节目名称、
    集数标签和球队名称转换；无法明确转换的罗马尼亚语标题会使该来源失败，
    从而避免在 XMLTV 中发布罗马尼亚语残留。
    """
    normalised = unicodedata.normalize("NFC", re.sub(r"\s+", " ", title.strip()))
    if not normalised:
        raise SourceUnavailable("Digi 4K 官方节目对象缺少可翻译的标题。")

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
                raise SourceUnavailable(f"Digi 4K 标题包含未识别的集数标签：{title!r}")
            translated = f"{translated} — Episode {matched.group(1)}"

    translated = re.sub(r"\s+", " ", translated).strip()
    untranslated = re.search(
        r"[ăâîșşțţǎĂÂÎȘŞȚŢǍ]|\b(?:Arome|din|paradisul|culinar|Balistică|Balistica|spatele|casei|Cei|mai|periculoși|periculoşi|vulcani|Cum|intrat|combatem|schimbarea|climatului|Fluturii|eroii|naturii|Lucrătorii|sălbăticie|Minunile|oceanului|Misterele|apelor|fermecate|Muzică|planetă|bizarerii|Odiseea|insulelor|grecești|greceşti|sepiei|Orașul|Oraşul|corali|Poveste|leneș|leneş|Tabăra|puilor|urs|Urangutanii|Școala|Şcoala|junglă|Valea|Rinului|Reclădind|Reclǎdind|natura|Munții|Munţii|Știința|Ştiinţa|bate|ficțiunea|ficţiunea)\b",
        translated,
        flags=re.IGNORECASE,
    )
    if untranslated:
        raise SourceUnavailable(f"Digi 4K 标题未获得可验证的英文转换：{title!r}")
    return translated


def collect_digi4k(days: int = 7) -> list[Programme]:
    """解析 Digi 4K 罗马尼亚官网首页公开发布的一周节目表。

    官网按页面顺序给出节目，午夜后的首档仍位于前一日期容器的末尾。采集器
    因此保留 DOM 顺序而不按时钟排序，遇到时间回绕时推进日历日期。每一条
    XMLTV 节目均必须从官网的下一条节目获得明确结束时间；不能建立该边界的
    节目不会发布，避免部分 XMLTV 客户端直接隐藏无 ``stop`` 的条目。
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
    window_start = datetime.combine(today, clock_time.min, tzinfo=zone)
    window_end = window_start + timedelta(days=days)
    entries: list[tuple[datetime, str]] = []

    for day_offset, day_node in enumerate(day_nodes[:days]):
        schedule_day = today + timedelta(days=day_offset)
        effective_day = schedule_day
        previous_time: clock_time | None = None
        day_entries = 0
        for mark in day_node.select("mark.schedule-days-item-hour"):
            start_time = _digi4k_time(mark.get_text(" ", strip=True))
            row = mark.find_parent("div", class_=lambda classes: classes and "flex" in classes)
            title_node = row.select_one("h3") if row else None
            source_title = title_node.get_text(" ", strip=True) if title_node else ""
            if not (start_time and source_title):
                continue
            # The official schedule inserts the post-midnight programme after the
            # evening items in the same date container. A clock reset is the only
            # authoritative signal required to advance to the following calendar day.
            if previous_time is not None and start_time <= previous_time:
                effective_day += timedelta(days=1)
            entries.append(
                (
                    datetime.combine(effective_day, start_time, tzinfo=zone),
                    _translate_digi4k_title(source_title),
                )
            )
            previous_time = start_time
            day_entries += 1
        if not day_entries:
            raise SourceUnavailable(f"Digi 4K 官网日期容器 {schedule_day.isoformat()} 未返回可发布节目。")

    entries.sort(key=lambda item: item[0])
    if len(entries) < 2:
        raise SourceUnavailable("Digi 4K 官网未返回足够节目以建立明确的结束时间。")

    records: list[Programme] = []
    for index, (start, title) in enumerate(entries):
        if not (window_start <= start < window_end):
            continue
        if index + 1 >= len(entries):
            # The displayed official horizon ends here. Do not manufacture an
            # end time or publish a record that XMLTV clients may hide.
            continue
        end, _ = entries[index + 1]
        if end <= start:
            raise SourceUnavailable(
                f"Digi 4K 官网节目顺序无法建立正向结束时间：{start.isoformat()} -> {end.isoformat()}。"
            )
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
                end_at=end.isoformat(),
                source_url=DIGI4K_GUIDE,
                retrieved_at=retrieved_at,
            )
        )
    if not records:
        raise SourceUnavailable("Digi 4K 官网未返回目标日期范围内具有完整起止时间的节目。")
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
    "2026 Portekiz Bisiklet Turu": "2026 Tour of Portugal",
    "Amerika Açık": "US Open",
}


def _translate_tvplus_eurosport_title(title: str) -> str:
    """将 TV+ 官方土耳其语 Eurosport 标题转换成赛事语义准确的英文。

    该转换在每次 TV+ 刷新时逐条执行。它只翻译公开标题中可明确识别的
    赛事、运动项目与阶段，不补充选手、比分、场地或未由官方页面提供的细节。
    已是英语或国际赛事正式名称的内容保持原样。
    """
    normalised = re.sub(r"\s*,\s*", ", ", title.strip())
    normalised = re.sub(r"\s+", " ", normalised)
    # TV+ 节目列表偶尔以 `(T)`／`（T）` 标示土耳其语原文；该标记不是标题本体。
    # 移除后，标题仍须通过下方严格英文转换和残余土耳其语检查。
    normalised = re.sub(r"\s*[（(]T[）)]\s*$", "", normalised, flags=re.IGNORECASE)
    if not normalised:
        raise SourceUnavailable("TV+ Eurosport 官方节目对象缺少可翻译的标题。")
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
        r"[çğıöşüÇĞİÖŞÜ]|\\b(?:Açık|Amerika|Avrupa|Binicilik|Bisiklet|Bisikleti|Bölüm|Canlı|Dağ|Dünya|Erkekler|Etap|Kadınlar|Portekiz|Sezon|Serisi|Şampiyonası|Tekrar|Tırmanış|Tur|Turu|Yarı|Özet)\\b",
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
            # 每一个来自官方 ``playbills`` 的节目对象都必须先经过翻译函数；
            # 空标题或残余无法验证的土耳其语会抛出 SourceUnavailable，绝不跳过或原样发布。
            source_title = str(item.get("name") or "")
            title = _translate_tvplus_eurosport_title(source_title)
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


_SBB_EUROSPORT_4K_TITLE_EXACT: dict[str, str] = {
    "Discovery Golf": "Discovery Golf",
    "Magazin: Cycling Show": "Magazine: Cycling Show",
    "NFL Hard Knocks": "NFL Hard Knocks",
    "UEC BMX Racing European Championship - Pregled": "UEC BMX Racing European Championship - Highlights",
    "Esport Svetski Kup Show": "Esports World Cup Show",
}


def _translate_sbb_eurosport_4k_title(title: str) -> str:
    """把 SBB 公共 EPG 的塞尔维亚语 Eurosport 4K 标题转换为可审计英文。

    仅转换明确的运动、赛事、地点、性别与阶段标记；不能可靠确认的词会令整个
    来源失败，避免向 XMLTV 写入未经验证的英语细节或原文残余。
    """
    normalised = re.sub(r"\s*,\s*", ", ", title.strip())
    normalised = re.sub(r"\s+", " ", normalised)
    if not normalised:
        raise SourceUnavailable("SBB Eurosport 4K 官方节目对象缺少可翻译的标题。")
    if normalised in _SBB_EUROSPORT_4K_TITLE_EXACT:
        return _SBB_EUROSPORT_4K_TITLE_EXACT[normalised]

    translated = normalised
    replacements = (
        ("Brdski biciklizam", "Mountain Biking"),
        ("Biciklizam", "Cycling"),
        ("Jedrenje", "Sailing"),
        ("Konjički sport", "Equestrian"),
        ("Skakanje", "Jumping"),
        ("Kratke staze", "Short Track"),
        ("Ahen", "Aachen"),
        ("Snuker", "Snooker"),
        ("Tenis", "Tennis"),
        ("Triatlon", "Triathlon"),
        ("Svetsko prvenstvo", "World Championship"),
        ("Svetski Šampionat", "World Championship"),
        ("Svetski kup", "World Cup"),
        ("Tur Portugala", "Tour of Portugal"),
        ("Tur Beneluksa", "Benelux Tour"),
        ("Tur Nemačke", "Tour of Germany"),
        ("Serija PRO", "PRO Series"),
        ("Meksiko Siti", "Mexico City"),
        ("Majami", "Miami"),
        ("Šangaj", "Shanghai"),
        ("Tokio", "Tokyo"),
        ("Džeda", "Jeddah"),
        ("Rolan Garos", "Roland Garros"),
        ("Koboli", "Cobolli"),
        ("Aleksander", "Alexander"),
        ("Etapa", "Stage"),
        ("Trka", "Race"),
        ("Singl", "Singles"),
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
    translated = re.sub(r"\s+", " ", translated).strip(" ,")
    untranslated = re.search(
        r"[čćđšžČĆĐŠŽ]|\b(?:Ahen|Aleksander|Biciklizam|Brdski|Dubl|Etapa|finala|Garos|Jedrenje|Koboli|Konjički|Kratke|Majami|Meksiko|Mešovito|Nemačke|Pregled|pregled|Rolan|Runda|Serija|Singl|Skakanje|Snuker|Spust|staze|Svetski|Svetsko|Šampionat|Tenis|Tokio|Trka|Triatlon|Tur|Žene|Muškarci)\b",
        translated,
    )
    if untranslated:
        raise SourceUnavailable(f"SBB Eurosport 4K 标题未获得可验证的英文转换：{title!r}")
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


def collect_sbb_eurosport_4k(days: int = 7) -> list[Programme]:
    """读取 SBB Public EPG 中 Eurosport 4K IPTV 的匿名公开周排期。

    SBB 的普通 Public EPG 页面为每次页面加载新建匿名应用令牌。本采集器每次
    运行都重新获取该公开页面所需令牌，并只在进程内存使用；不保存、重放或读取
    用户登录、Cookie、订阅或播放权限。所有标题均须通过严格英文转换。
    """
    if days not in range(1, 8):
        raise ValueError("SBB Eurosport 4K 采集天数必须为 1–7。")
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
    channels = [
        item for item in directory if isinstance(item, dict) and str(item.get("id")) == SBB_EUROSPORT_4K_CHANNEL_ID
    ] if isinstance(directory, list) else []
    if len(channels) != 1:
        raise SourceUnavailable("SBB Public EPG 频道目录未返回唯一的 Eurosport 4K IPTV 服务。")
    channel = channels[0]
    if (channel.get("name") or "").strip() != SBB_EUROSPORT_4K_SOURCE_NAME:
        raise SourceUnavailable("SBB Public EPG 的 Eurosport 4K IPTV 原始频道名发生变化。")
    if str(channel.get("position")) != SBB_EUROSPORT_4K_CHANNEL_NUMBER:
        raise SourceUnavailable("SBB Public EPG 的 Eurosport 4K IPTV 频道号发生变化。")

    zone = ZoneInfo("Europe/Belgrade")
    today = datetime.now(zone).date()
    start = datetime.combine(today, clock_time.min, tzinfo=zone).astimezone(timezone.utc)
    end = datetime.combine(today + timedelta(days=days), clock_time.min, tzinfo=zone).astimezone(timezone.utc) - timedelta(seconds=1)
    events_response = session.get(
        f"{SBB_PUBLIC_API}/v1/public/events/epg",
        params={
            **common_params,
            "cid": SBB_EUROSPORT_4K_CHANNEL_ID,
            "fromTime": start.isoformat(),
            "toTime": end.isoformat(),
        },
        timeout=30,
    )
    events_response.raise_for_status()
    try:
        events = _sbb_events(events_response.json())
    except ValueError as exc:
        raise SourceUnavailable("SBB Public EPG Eurosport 4K 排期未返回 JSON。") from exc
    if not events:
        raise SourceUnavailable("SBB Public EPG 未返回 Eurosport 4K IPTV 的节目条目。")

    retrieved_at = utc_now_iso()
    records: list[Programme] = []
    for event in events:
        source_title = str(event.get("title") or "")
        title = _translate_sbb_eurosport_4k_title(source_title)
        start_value = event.get("startTime")
        end_value = event.get("endTime")
        if not (isinstance(start_value, str) and isinstance(end_value, str)):
            continue
        try:
            event_start = datetime.fromisoformat(start_value.replace("Z", "+00:00")).astimezone(zone)
            event_end = datetime.fromisoformat(end_value.replace("Z", "+00:00")).astimezone(zone)
        except ValueError:
            continue
        if event_end <= event_start or not (today <= event_start.date() < today + timedelta(days=days)):
            continue
        records.append(
            Programme(
                provider="sbb_rs",
                country="RS",
                timezone="Europe/Belgrade",
                channel_id=SBB_EUROSPORT_4K_CHANNEL_ID,
                channel_number=SBB_EUROSPORT_4K_CHANNEL_ID,
                channel_name=SBB_EUROSPORT_4K_NAME,
                title=title,
                start_at=event_start.isoformat(),
                end_at=event_end.isoformat(),
                source_url=SBB_PUBLIC_EPG_GUIDE,
                retrieved_at=retrieved_at,
            )
        )
    records = _deduplicate(records)
    if not records:
        raise SourceUnavailable("SBB Public EPG 未返回目标日期范围内可发布的 Eurosport 4K IPTV 节目。")
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
                title = _translate_magenta_tv_sky_de_title(source_title)
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
