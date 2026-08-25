"""Enrich selected UK XMLTV programmes with user-authorised TVGuide.co.uk artwork URLs.

The module only saves direct remote image URLs; it does not download, cache or re-host
images. A programme is enriched only when its mapped TVGuide channel, UTC start time
and normalised title form a unique match on the corresponding daily schedule page.
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, replace
from datetime import datetime, timedelta, timezone
import re
import time
import unicodedata
from typing import Iterable

from bs4 import BeautifulSoup
import requests
from zoneinfo import ZoneInfo

from .models import Programme

TVGUIDE_BASE_URL = "https://www.tvguide.co.uk"
TVGUIDE_IMAGE_HOST = "tv.assets.pressassociation.io"
TVGUIDE_USER_AGENT = "Cathy-epg/0.3 (+https://github.com/waastudios/Cathy-epg; authorised TVGuide artwork linking)"

# TVGuide channel-page slugs. Entries that TVGuide does not publish remain absent:
# matching deliberately fails closed rather than substituting a related channel.
TVGUIDE_CHANNEL_SLUGS: dict[str, str] = {
    "BBC One London": "bbc-one-london",
    "BBC Two": "bbc-two-hd",
    "BBC Three": "bbc-three",
    "BBC Four": "bbc-four",
    "BBC News": "bbc-news",
    "BBC Parliament": "bbc-parliament",
    "ITV1 London": "itv1-london",
    "ITV2": "itv2",
    "ITV3": "itv3",
    "ITV4": "itv4",
    "Channel 4": "channel-4",
    "Sky Mix": "sky-mix",
    "Sky Arts": "sky-arts",
    "Sky Witness": "sky-witness",
    "Sky Atlantic": "sky-atlantic",
    "Sky One": "sky-one",
    "Sky Comedy": "sky-comedy",
    "Sky Sci-Fi": "sky-sci-fi",
    "Sky Crime": "sky-crime",
    "Sky Documentaries": "sky-documentaries",
    "Sky History": "sky-history",
    "Sky Nature": "sky-nature",
    "Sky Sports News": "sky-sports-news",
    "Sky Sports Main Event": "sky-sports-main-event",
    "Sky Sports Premier League": "sky-sports-premier-league",
    "Sky Sports Football": "sky-sports-football",
    "Sky Sports Cricket": "sky-sports-cricket",
    "Sky Sports Golf": "sky-sports-golf",
    "Sky Sports F1": "sky-sports-f1",
    "Sky Sports Tennis": "sky-sports-tennis",
    "Sky Sports Action": "sky-sports-action",
    "Sky Sports +": "sky-sports-plus",
    "Sky Sports Racing": "sky-sports-racing",
    "Sky Sports Mix": "sky-sports-mix",
    "TNT Sports 1": "tnt-sports-1",
    "TNT Sports 2": "tnt-sports-2",
    "TNT Sports 3": "tnt-sports-3",
    "TNT Sports 4": "tnt-sports-4",
    "TNT Sports Ultimate": "tnt-sports-ultimate",
    "TNT Sports Box Office HD": "tnt-sports-box-office",
}

_ELIGIBLE_PROVIDERS = frozenset({"ee_uk", "virgin_uk"})
_LONDON = ZoneInfo("Europe/London")


@dataclass(frozen=True)
class TVGuideScheduleEntry:
    """A single image-bearing entry parsed from one TVGuide daily channel schedule."""

    start_at: datetime
    title: str
    image_url: str
    detail_url: str


def _normalise_title(value: str) -> str:
    """Create a conservative comparison key for schedule title matching."""
    value = unicodedata.normalize("NFKC", value).casefold().strip()
    value = re.sub(r"^live\s*:\s*", "", value)
    value = re.sub(r"\s+", " ", value)
    return re.sub(r"[^\w]+", "", value)


def parse_tvguide_schedule(html: str) -> list[TVGuideScheduleEntry]:
    """Extract image-bearing programme entries from a TVGuide channel-day HTML page."""
    soup = BeautifulSoup(html, "html.parser")
    entries: list[TVGuideScheduleEntry] = []
    for block in soup.select("div.js-schedule[data-date]"):
        raw_start = block.get("data-date")
        if not isinstance(raw_start, str):
            continue
        try:
            start_at = datetime.fromisoformat(raw_start.replace("Z", "+00:00"))
        except ValueError:
            continue
        title_link = next(
            (
                anchor
                for anchor in block.find_all("a", href=True)
                if "/schedule/" in str(anchor.get("href")) and anchor.get_text(" ", strip=True)
            ),
            None,
        )
        image = block.find("img", src=True)
        if title_link is None or image is None:
            continue
        title = title_link.get_text(" ", strip=True)
        src = str(image.get("src") or "").strip()
        if not title or not src or TVGUIDE_IMAGE_HOST not in src:
            continue
        detail_url = str(title_link.get("href") or "").strip()
        if detail_url.startswith("/"):
            detail_url = f"{TVGUIDE_BASE_URL}{detail_url}"
        entries.append(TVGuideScheduleEntry(start_at=start_at, title=title, image_url=src, detail_url=detail_url))
    return entries


def _programme_key(record: Programme) -> tuple[str, datetime, str] | None:
    """Build a matching key only for mapped UK programme records with valid timestamps."""
    if record.provider not in _ELIGIBLE_PROVIDERS:
        return None
    slug = TVGUIDE_CHANNEL_SLUGS.get(record.channel_name)
    if not slug:
        return None
    try:
        start_at = datetime.fromisoformat(record.start_at).astimezone(timezone.utc)
    except ValueError:
        return None
    return slug, start_at, _normalise_title(record.title)


def _entry_match(record: Programme, entries: Iterable[TVGuideScheduleEntry]) -> TVGuideScheduleEntry | None:
    """Return exactly one same-channel, same-time, same-title entry; otherwise fail closed."""
    record_start = datetime.fromisoformat(record.start_at).astimezone(timezone.utc)
    target_title = _normalise_title(record.title)
    matches = [
        entry
        for entry in entries
        if _normalise_title(entry.title) == target_title
        and abs(entry.start_at.astimezone(timezone.utc) - record_start) <= timedelta(minutes=1)
    ]
    return matches[0] if len(matches) == 1 else None


def enrich_tvguide_uk_images(
    records: Iterable[Programme],
    *,
    session: requests.Session | None = None,
    pause_seconds: float = 0.25,
) -> tuple[list[Programme], dict[str, int]]:
    """Add user-authorised TVGuide artwork URLs to exact UK programme matches.

    The TVGuide HTML is fetched once per mapped channel/day and retained only in the
    in-memory per-run cache. Existing image URLs are preserved unchanged.
    """
    rows = list(records)
    request_session = session or requests.Session()
    request_session.headers.setdefault("User-Agent", TVGUIDE_USER_AGENT)

    requested: dict[tuple[str, str], list[int]] = defaultdict(list)
    for index, record in enumerate(rows):
        if record.image_url:
            continue
        key = _programme_key(record)
        if key is None:
            continue
        slug, start_at, _ = key
        requested[(slug, start_at.astimezone(_LONDON).date().isoformat())].append(index)

    page_entries: dict[tuple[str, str], list[TVGuideScheduleEntry]] = {}
    failures = 0
    for (slug, local_date) in sorted(requested):
        try:
            response = request_session.get(
                f"{TVGUIDE_BASE_URL}/channel/{slug}", params={"date": local_date}, timeout=30
            )
            response.raise_for_status()
            page_entries[(slug, local_date)] = parse_tvguide_schedule(response.text)
        except requests.RequestException:
            failures += 1
            page_entries[(slug, local_date)] = []
        if pause_seconds:
            time.sleep(pause_seconds)

    enriched = 0
    misses = 0
    for (slug, local_date), indexes in requested.items():
        entries = page_entries[(slug, local_date)]
        for index in indexes:
            match = _entry_match(rows[index], entries)
            if match is None:
                misses += 1
                continue
            rows[index] = replace(
                rows[index], image_url=match.image_url, image_source_url=match.detail_url
            )
            enriched += 1

    stats = {
        "eligible_programmes": sum(len(indexes) for indexes in requested.values()),
        "schedule_pages": len(requested),
        "schedule_page_failures": failures,
        "matched_images": enriched,
        "unmatched_programmes": misses,
    }
    return rows, stats
