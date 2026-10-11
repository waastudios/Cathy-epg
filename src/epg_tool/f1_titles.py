"""Dedicated adaptation for F1-channel programme titles (Sky DE source).

Sky Sport F1 airs F1 / F2 / F3 / F1 Academy plus other motorsport series
(Porsche Supercup, GTWC, IndyCar, MotoGP, ...), and their German titles follow
strict patterns such as ``F1: 1. Freies Training - GP Singapur`` or
``Live F2: 2. Rennen - GP Ungarn``.  Machine translation of these patterns is
inconsistent -- the frozen ``translation_cache.json`` contains
``Azerbaijan GP`` next to ``GP Azerbaijan``, ``1. Race`` next to ``1st Race``,
and mangled hybrids like ``Pressekonferenz Race`` -- so this module translates
them deterministically.

``adapt_f1_title`` is consulted before the curated exact map, the translation
memory and the online services (see ``_translate_magenta_tv_sky_de_title``),
which keeps F1-channel titles stable regardless of third-party translation
behaviour.

House style (matches the reviewed ``sky_de_title_translations.json``):
``F1: 1st Free Practice - GP Singapore`` -- i.e. ``<series>: <session> - GP <venue>``.
"""
from __future__ import annotations

import re

# Motorsport series airing on Sky DE F1 channels, longest first for the regex.
MOTORSPORT_SERIES: tuple[str, ...] = (
    "F1 Academy",
    "Ferrari Challenge Europe",
    "Formula E",
    "WorldSBK",
    "WorldSSP",
    "Indy NXT",
    "IndyCar",
    "MotoGP",
    "Moto2",
    "Moto3",
    "MotoE",
    "GTWC",
    "PMSC",
    "HDBWC",
    "DTM",
    "WRC",
    "WEC",
    "NASCAR",
    "F1",
    "F2",
    "F3",
    "Motorsport",
)

# German series names occasionally used by Sky DE, normalised to the
# canonical English short form in the output.
_SERIES_ALIASES: dict[str, str] = {
    "Formel 1": "F1",
    "Formel 2": "F2",
    "Formel 3": "F3",
}

_SERIES_PATTERN = "|".join(
    sorted(list(MOTORSPORT_SERIES) + list(_SERIES_ALIASES), key=len, reverse=True)
)

# German GP venue / country names -> English.  Covers the current F1 calendar
# plus F2/F3 venues that appear on Sky DE motorsport channels.
GP_NAME_DE_EN: dict[str, str] = {
    "Aserbaidschan": "Azerbaijan",
    "Singapur": "Singapore",
    "Spanien": "Spain",
    "Niederlande": "Netherlands",
    "Ungarn": "Hungary",
    "Großbritannien": "Great Britain",
    "Österreich": "Austria",
    "Italien": "Italy",
    "Belgien": "Belgium",
    "Frankreich": "France",
    "Kanada": "Canada",
    "Mexiko": "Mexico",
    "Brasilien": "Brazil",
    "Japan": "Japan",
    "Australien": "Australia",
    "Katar": "Qatar",
    "Saudi-Arabien": "Saudi Arabia",
    "USA": "USA",
    "Monaco": "Monaco",
    "China": "China",
    "Bahrain": "Bahrain",
    "Abu Dhabi": "Abu Dhabi",
    "Las Vegas": "Las Vegas",
    "Miami": "Miami",
    "Imola": "Imola",
    "Emilia-Romagna": "Emilia-Romagna",
    "Steiermark": "Styria",
    "Eifel": "Eifel",
    "Zandvoort": "Zandvoort",
    "Silverstone": "Silverstone",
    "Spielberg": "Spielberg",
    "Budapest": "Budapest",
    "Barcelona": "Barcelona",
    "Portimão": "Portimao",
    "Jerez": "Jerez",
    "Le Castellet": "Le Castellet",
    "Monte Carlo": "Monte Carlo",
    "Portugal": "Portugal",
    "Türkei": "Turkey",
    "Russland": "Russia",
    "San Marino": "San Marino",
    "Deutschland": "Germany",
    "Aragonien": "Aragon",
    "Indonesien": "Indonesia",
}

_ORDINALS = {"1": "1st", "2": "2nd", "3": "3rd"}


def _ordinal(n: str) -> str:
    return _ORDINALS.get(n, f"{n}th")


def _ordinal_repl(match: re.Match, word: str) -> str:
    return f"{_ordinal(match.group(1))} {word}"


# Session keywords, longest first so "Rennen Kompakt" wins over "Rennen".
# Each entry is (pattern, replacement); replacement may be a callable.
_SESSION_RULES: tuple[tuple[str, object], ...] = (
    # Press-conference compounds first so the word order stays natural and
    # generic rules (e.g. "Rennen" -> "Race") cannot break them apart.
    (r"Pressekonferenz Fahrer", "Drivers' Press Conference"),
    (r"Pressekonferenz Teamchefs", "Team Principals' Press Conference"),
    (r"Pressekonferenz Qualifying", "Post-Qualifying Press Conference"),
    (r"Pressekonferenz Sprint", "Post-Sprint Press Conference"),
    (r"Pressekonferenz Rennen", "Post-Race Press Conference"),
    (r"(\d+)\.\s*Freies Training", lambda m: _ordinal_repl(m, "Free Practice")),
    (r"Freies Training", "Free Practice"),
    (r"Zeittraining", "Qualifying"),
    (r"Sprint-Qualifying", "Sprint Qualifying"),
    (r"Sprintqualifying", "Sprint Qualifying"),
    (r"Sprintrennen", "Sprint Race"),
    (r"Rennen Kompakt", "Race Compact"),
    (r"Qualifying Kompakt", "Qualifying Compact"),
    (r"Sprint Kompakt", "Sprint Compact"),
    (r"(\d+)\.\s*Rennen", lambda m: _ordinal_repl(m, "Race")),
    (r"Rennen", "Race"),
    (r"(\d+)\.\s*Training", lambda m: _ordinal_repl(m, "Practice")),
    (r"Training", "Practice"),
    (r"Pressekonferenz", "Press Conference"),
    (r"Fahrerparade", "Drivers' Parade"),
    (r"Siegerehrung", "Podium Ceremony"),
    (r"Analysen & Interviews", "Analysis & Interviews"),
    (r"Teamchefs", "Team Principals"),
    (r"Fahrer", "Drivers"),
    (r"Vorberichte", "Build-up"),
    (r"Nachberichte", "Recap"),
    (r"Zusammenfassung", "Recap"),
    (r"Highlights", "Highlights"),
    (r"Sprint", "Sprint"),
    (r"Qualifying", "Qualifying"),
    # Documentary / feature titles on F1 channels.
    (r"ein Wochenende mit", "a weekend with"),
    (r"eine Woche mit", "a week with"),
    (r"Boxenstopp", "Pit Stop"),
    (r"Spektakuläre", "Spectacular"),
    (r"Spektakulär", "Spectacular"),
    (r"Abflüge", "Offs"),
    (r"Abflug", "Off"),
    (r"zum Rennen", "for the Race"),
    (r"Rallye", "Rally"),
    (r"Die grüne Hölle", "The Green Hell"),
    (r"wie im Rausch", "in a frenzy"),
)


def _translate_session(session: str) -> str:
    out = session
    for pattern, replacement in _SESSION_RULES:
        out = re.sub(rf"(?<!\w){pattern}(?!\w)", replacement, out)
    return re.sub(r"\s+", " ", out).strip()


# Primary pattern: "[Live ]<series>: <session> - GP <venue>"
_F1_PATTERN = re.compile(
    r"^(?P<live>Live\s+)?(?P<series>" + _SERIES_PATTERN + r"):\s*"
    r"(?P<session>.+?)\s*-\s*GP\s+(?P<venue>[A-Za-zäöüÄÖÜß\-\s]+?)\s*$"
)

# Fallback: any other "[Live ]<series>: ..." title.
_F1_SERIES_PREFIX = re.compile(
    r"^(?P<live>Live\s+)?(?P<series>" + _SERIES_PATTERN + r"):\s*(?P<rest>.+)$"
)

_GP_NAME_PATTERN = re.compile(
    r"(?<!\w)(" + "|".join(sorted(map(re.escape, GP_NAME_DE_EN), key=len, reverse=True)) + r")(?!\w)"
)

# German marker detection: when the output still contains German, the adapter
# declines and the normal translation pipeline takes over instead of emitting
# half-German titles.  Umlauts/ß are decisive; the word list covers common
# German function words and stems that do not collide with English vocabulary
# used in motorsport titles.  Function words are matched case-sensitively
# (German prepositions/articles are lowercase; uppercase "AM"/"IM" are racing
# classes), content words case-insensitively.
_GERMAN_MARKER_LOWER = re.compile(
    r"[äöüß]|"
    r"\b(?:der|die|das|den|dem|des|ein|eine|einer|einem|einen|eines|und|oder|"
    r"aber|auch|nicht|kein|keine|noch|schon|sehr|wieder|mit|von|vom|zum|zur|"
    r"für|über|aus|bei|nach|vor|alle|alles|neue|neuer|neues|neuen|große|großer|"
    r"großes|weitere|unbekannt\w*|irgend\w*|etwa)\b"
)
_GERMAN_MARKER_NOUN = re.compile(
    r"\b(?:Alle|Damen|Ein|Es|Folgt|Frauen|Herren|Rennen|Runde|Sendepause|Spezial|"
    r"Spiel|Spieltag|Tore|Topspiel|Freies|Zeittraining|Pressekonferenz|Fahrer|"
    r"Training|Freitag|Samstag|Sonntag|Montag|Dienstag|Mittwoch|Donnerstag|"
    r"Wiederholung|Stunde\w*|Rausch|Hölle)\b",
    flags=re.IGNORECASE,
)


def _has_german_residue(text: str) -> bool:
    return bool(
        _GERMAN_MARKER_LOWER.search(text) or _GERMAN_MARKER_NOUN.search(text)
    )


def _translate_venue_names(text: str) -> str:
    return _GP_NAME_PATTERN.sub(lambda m: GP_NAME_DE_EN[m.group(1)], text)


def adapt_f1_title(title: str) -> str | None:
    """Translate one German F1-channel title deterministically.

    Returns the English title, or None when the title is not an F1-pattern
    title or cannot be translated cleanly (the caller then falls back to the
    regular translation pipeline).
    """
    text = re.sub(r"\s+", " ", (title or "").strip())
    if not text:
        return None

    primary = _F1_PATTERN.match(text)
    if primary:
        live = primary.group("live") or ""
        series = _SERIES_ALIASES.get(primary.group("series"), primary.group("series"))
        session_en = _translate_session(primary.group("session"))
        venue_en = GP_NAME_DE_EN.get(primary.group("venue"), primary.group("venue"))
        result = f"{live}{series}: {session_en} - GP {venue_en}"
    else:
        prefixed = _F1_SERIES_PREFIX.match(text)
        if not prefixed:
            return None
        live = prefixed.group("live") or ""
        series = _SERIES_ALIASES.get(prefixed.group("series"), prefixed.group("series"))
        rest = prefixed.group("rest")
        rest_en = _translate_session(_translate_venue_names(rest))
        if rest_en == rest:
            return None
        result = f"{live}{series}: {rest_en}"

    if result == text:
        return None
    if _has_german_residue(result):
        return None
    return result
