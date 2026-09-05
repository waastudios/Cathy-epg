"""Best-effort English translation with network and deterministic fallbacks."""
from __future__ import annotations

import re
import time
from functools import lru_cache
from urllib.parse import quote

import requests


SESSION = requests.Session()
SESSION.headers.update({"User-Agent": "Cathy-epg/0.2"})

# Deterministic fallback for common Nordic/French TV wording.  This is deliberately
# small: it is a last resort when public translation services are unavailable.
PHRASES = {
    "Träning": "Practice", "Kval": "Qualifying", "kval": "qualifying",
    "Lopp": "Race", "Final": "Final", "Semifinal": "Semi-final",
    "Sverige": "Sweden", "svensk": "Swedish", "svenska": "Swedish",
    "Norge": "Norway", "norsk": "Norwegian", "norska": "Norwegian",
    "Italien": "Italy", "Italiensk": "Italian", "GP": "Grand Prix",
    "Invités": "Guests", "Invité": "Guest", "Saison": "Season",
    "Épisode": "Episode", "épisode": "episode", "avec": "with",
    "Les": "The", "Le": "The", "La": "The", "Des": "The",
    "du": "of the", "de": "of", "et": "and", "ou": "or",
    "Tatt på fersken": "Caught Red-Handed", "Grensevakten Sverige": "Border Patrol Sweden",
    "Formel 1": "Formula 1", "Formel 2": "Formula 2", "V Sport UltraHD": "V Sport UltraHD",
}


def _hard_translate(text: str) -> str:
    out = text
    for src, dst in sorted(PHRASES.items(), key=lambda x: len(x[0]), reverse=True):
        out = re.sub(rf"(?<!\w){re.escape(src)}(?!\w)", dst, out, flags=re.IGNORECASE if src.islower() else 0)
    # Common punctuation/whitespace normalization only; never erase program data.
    return re.sub(r"\s+", " ", out).strip()


def _google_translate(text: str, source: str | None) -> str | None:
    sl = source or "auto"
    url = (
        "https://translate.googleapis.com/translate_a/single"
        f"?client=gtx&sl={quote(sl)}&tl=en&dt=t&q={quote(text)}"
    )
    r = SESSION.get(url, timeout=8)
    r.raise_for_status()
    data = r.json()
    translated = "".join(part[0] for part in data[0] if part and part[0])
    return translated.strip() or None


def _mymemory_translate(text: str, source: str | None) -> str | None:
    # MyMemory accepts ISO language pairs and is used only as a secondary service.
    sl = source or "auto"
    if sl == "auto":
        sl = "en"
    url = (
        "https://api.mymemory.translated.net/get"
        f"?q={quote(text)}&langpair={quote(sl)}|en"
    )
    r = SESSION.get(url, timeout=8)
    r.raise_for_status()
    data = r.json()
    translated = (data.get("responseData") or {}).get("translatedText")
    if not translated or data.get("responseStatus") not in (200, "200"):
        return None
    return translated.strip()


@lru_cache(maxsize=4096)
def translate_title(text: str, source: str | None = None) -> str:
    """Translate a TV title to English without making translation a hard failure.

    Order: Google public endpoint -> MyMemory -> deterministic phrase fallback.
    If every service is unavailable, the original title is returned rather than
    breaking the official EPG fetch and causing stale data to be published.
    """
    text = (text or "").strip()
    if not text:
        return text
    for fn in (_google_translate, _mymemory_translate):
        for attempt in range(2):
            try:
                value = fn(text, source)
                if value and value.lower() != text.lower():
                    return value
                if value:
                    return value
            except Exception:
                if attempt == 0:
                    time.sleep(0.25)
    return _hard_translate(text)
