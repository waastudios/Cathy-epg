"""节目海报镜像：把来源 CDN 的节目图下载到仓库 data/posters/，XMLTV 输出改用 jsDelivr 链接。

背景（2026-09-30）：SBB Public EPG 的官方节目图放在塞尔维亚 United Group
CDN（images-web.ug-be.cdn.united.cloud）上。XML 结构经 NanoTV 作者确认无误、
图片在境外可正常打开，但用户在 NanoTV（含开梯子）中始终看不到海报。
为彻底绕开该小众 CDN 可能存在的 TLS/链路兼容问题，采集时把图片下载到
仓库并改用 jsDelivr（cdn.jsdelivr.net，全球加速、iOS 兼容性好）输出。
下载失败时保留原始 URL，不阻塞采集。
"""

from __future__ import annotations

import re
from pathlib import Path
from urllib.parse import urlparse

import requests

# 仓库根目录下的海报存放目录（采集命令均在仓库根目录运行）。
POSTER_DIR = Path("data") / "posters"

# jsDelivr 的 GitHub 加速地址模板。
JSDELIVR_TEMPLATE = "https://cdn.jsdelivr.net/gh/waastudios/Cathy-epg@master/data/posters/{filename}"

# 标题中的零宽/不可见字符（SBB 源站 CMS 会带入，如 "Speed\u200b\u200bRelay"），输出前清理。
_INVISIBLE_CHARS = re.compile("[\u200b\u200c\u200d\ufeff]")


def sanitize_title(title: str) -> str:
    """去掉标题中的零宽空格等不可见字符，并做常规空白规整。"""
    cleaned = _INVISIBLE_CHARS.sub("", title)
    return re.sub(r"\s+", " ", cleaned).strip()


def mirror_poster(image_url: str, session: requests.Session | None = None) -> str:
    """把来源图片下载到 data/posters/，返回 jsDelivr 镜像 URL。

    文件已存在则直接返回镜像 URL；下载失败返回原始 URL。
    """
    filename = Path(urlparse(image_url).path).name
    if not filename or "." not in filename:
        return image_url
    POSTER_DIR.mkdir(parents=True, exist_ok=True)
    target = POSTER_DIR / filename
    if not target.exists():
        try:
            sess = session or requests.Session()
            response = sess.get(
                image_url,
                timeout=60,
                headers={"User-Agent": "Mozilla/5.0 (compatible; Cathy-epg/1.0)"},
            )
            response.raise_for_status()
            content_type = (response.headers.get("Content-Type") or "").lower()
            if "image" not in content_type:
                return image_url
            target.write_bytes(response.content)
        except Exception:
            return image_url
    return JSDELIVR_TEMPLATE.format(filename=filename)
