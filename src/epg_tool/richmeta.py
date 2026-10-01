"""富媒体元数据：节目分类推断与简介回退生成。

背景：上游源站大多只给标题（无简介、无分类），而 TiviMate / OTT Navigator
等播放器在检测到 `<desc>-</desc>` 这类无实质描述时会折叠海报面板、转入
精简文本模式。本模块在 XMLTV 输出阶段补齐：

- ``infer_category``：从频道/标题关键词推断分类（Sports / Movie / News …）；
- ``build_description``：有上游简介则用之，否则按「标题＋频道＋分类」
  生成符合语义的基础描述，**严禁输出单字符 "-"**。
"""

from __future__ import annotations

import re


# 频道名关键词 -> 分类。按 provider 前缀 + 频道名匹配。
_CHANNEL_CATEGORY_RULES: tuple[tuple[str, str], ...] = (
    ("eurosport", "Sports"),
    ("eleven sports", "Sports"),
    ("tnt sports", "Sports"),
    ("sky sports", "Sports"),
    ("beinsports", "Sports"),
    ("beIN".lower(), "Sports"),
    ("sky news", "News"),
    ("bbc news", "News"),
    ("cnn", "News"),
    ("sky cinema", "Movie"),
    ("film", "Movie"),
    ("kids", "Children"),
    ("cartoon", "Children"),
    ("boomerang", "Children"),
    ("discovery", "Documentary"),
    ("national geographic", "Documentary"),
    ("history", "Documentary"),
    ("music", "Music"),
    ("mtv", "Music"),
)


# 标题关键词 -> 分类（标题里出现则优先）。
_TITLE_CATEGORY_RULES: tuple[tuple[str, str], ...] = (
    ("live:", "Sports"),
    (" vs ", "Sports"),
    (" v ", "Sports"),
    ("grand prix", "Sports"),
    ("championship", "Sports"),
    ("league", "Sports"),
    ("cup final", "Sports"),
    ("news", "News"),
    ("weather", "News"),
    ("documentary", "Documentary"),
)


def infer_category(channel_name: str, title: str, provider: str = "") -> str:
    """推断节目分类，返回 XMLTV category 文本。"""
    lowered_title = title.lower()
    for keyword, category in _TITLE_CATEGORY_RULES:
        if keyword in lowered_title:
            return category
    lowered_channel = channel_name.lower()
    for keyword, category in _CHANNEL_CATEGORY_RULES:
        if keyword in lowered_channel:
            return category
    if provider in {"sbb_rs", "player_pl"} and "eurosport" in lowered_channel:
        return "Sports"
    return "Entertainment"


_SENTENCE_END = re.compile(r"[.!?]$")


def build_description(
    title: str,
    channel_name: str,
    category: str,
    upstream_desc: str | None = None,
) -> str:
    """构造节目简介。

    有上游简介且非空时直接采用；否则按标题/频道/分类生成语义化基础描述。
    永不返回空字符串或 "-" 占位符。
    """
    if upstream_desc:
        cleaned = upstream_desc.strip()
        if cleaned and cleaned != "-":
            return cleaned
    # 回退：语义化基础描述，不虚构剧情，只陈述已知事实。
    if category == "Movie":
        text = f"{title} — feature film on {channel_name}."
    elif category == "Sports":
        text = f"{title} — sports coverage on {channel_name}."
    elif category == "News":
        text = f"{title} — news programme on {channel_name}."
    elif category == "Documentary":
        text = f"{title} — documentary on {channel_name}."
    elif category == "Children":
        text = f"{title} — children's programme on {channel_name}."
    elif category == "Music":
        text = f"{title} — music programme on {channel_name}."
    else:
        text = f"{title} on {channel_name}."
    return text if _SENTENCE_END.search(text) else text + "."
