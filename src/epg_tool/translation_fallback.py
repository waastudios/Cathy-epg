"""Best-effort English translation with network and deterministic fallbacks."""
from __future__ import annotations

import json
import re
import time
from functools import lru_cache
from pathlib import Path
from typing import Callable
from urllib.parse import quote

import requests


SESSION = requests.Session()
SESSION.headers.update({"User-Agent": "Cathy-epg/0.2"})

# Persistent translation memory.  Exact local maps in sources.py are consulted
# first; anything translated through an online service is recorded here so the
# result is stable, auditable and reused without another network call.  The
# daily workflow commits this file, so the memory grows over time instead of
# re-translating the same titles every day.
_CACHE_PATH = Path(__file__).with_name("translation_cache.json")


class TitleUntranslatable(Exception):
    """A single programme title could not be converted to English.

    Collectors catch this per programme and skip that entry instead of failing
    the whole provider, so one new title can never wipe out a channel's guide.
    """


_cache: dict[str, dict[str, str]] | None = None


def _load_cache() -> dict[str, dict[str, str]]:
    global _cache
    if _cache is None:
        _cache = {}
        try:
            raw = json.loads(_CACHE_PATH.read_text(encoding="utf-8"))
            if isinstance(raw, dict):
                for lang, table in raw.items():
                    if isinstance(lang, str) and isinstance(table, dict):
                        _cache[lang] = {str(k): str(v) for k, v in table.items()}
        except (OSError, ValueError):
            _cache = {}
    return _cache


def _save_cache_entry(source_lang: str, original: str, translated: str) -> None:
    cache = _load_cache()
    table = cache.setdefault(source_lang, {})
    if table.get(original) == translated:
        return
    table[original] = translated
    try:
        _CACHE_PATH.write_text(
            json.dumps(cache, ensure_ascii=False, indent=1, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    except OSError:
        pass

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


# --- English-output verification -------------------------------------------
# Every tier of translate_programme_title() must pass this gate before its
# result may be published or memorised.  The curated exact maps only know a
# fixed vocabulary, the persistent memory can hold a bad result forever, and
# the online services occasionally return the source text (or a half
# translation) unchanged -- all three leaked non-English programme titles
# into the published guide (e.g. Serbian "Svetska turneja" and Polish
# "Skoki narciarskie" on the Eurosport channels).  The gate is deliberately
# deterministic and auditable: Cyrillic anywhere, source-language diacritics
# for Serbian/Polish (whose Latin scripts carry descriptive wording with
# them), and per-language residual word lists of function words and common
# EPG/sport vocabulary that never occur in an English guide.  A candidate
# that fails is treated as "not translated": the next tier is tried, and if
# no tier passes, TitleUntranslatable skips that single programme.  A few
# tempting markers are deliberately excluded because they collide with
# legitimate English guide text: German "am" (the "Pirelli AM" racing
# class), Norwegian "er" (the series "ER"), French articles ("Tour de
# France", "Le Mans") and German articles ("Die Hard").
_SOURCE_DIACRITICS_HARD = {
    "sr": "čćđšž",
    "pl": "ąćęłńóśźż",
}

_RESIDUAL_WORDS: dict[str, frozenset[str]] = {
    "sr": frozenset("""
        svetska svetski svetsko svetskog svetskom svetske turneja turneje
        turneju prvenstvo prvenstva prvenstvu šampionat šampionata sampionat
        sampionata igre igara igri olimpijske olimpijskih olimpijska
        olimpijski olimpijada olimpijade olimpijadi dvorana dvorane slavnih
        dom biciklizam biciklizma brdski drumska drumski trka trke trku
        utakmica utakmice utakmicu fudbal fudbala fudbalski košarka košarke
        kosarka kosarke rukomet rukometa odbojka odbojke skijanje skijanja
        skokovi skokova plivanje plivanja veslanje jedrenje konjički konjicki
        muškarci muskarci muškaraca muskaraca žene zene žena zena
        polufinale polufinala četvrtfinale cetvrtfinale pregled pregleda
        etapa etape etapu runda runde rundu mešovito mesovito dubl spust
        spusta sati sata pobednik pobednica pobednici takmičenje takmicenje
        takmičenja uživo uzivo prenos prenosa prenose direktan direktni
        repriza reprize reprizu najbolje najbolji najbolja magazin magazina
        emisija emisije emisiju specijal specijala galerija galerije kuća
        kuca ahen snuker tenis triatlon evropska evropski evropsko evrope
        evropi ceremonija ceremonije otvaranje otvaranja zatvaranje
        zatvaranja dnevnik vesti pariz rim tokio
    """.split()),
    "pl": frozenset("""
        oraz lub ale dla przez przed przeciwko między także już jeszcze
        tylko bardzo wciąż mecz meczu mecze meczów spotkanie spotkania
        zawody zawodów turniej turnieju turnieje rozgrywki rozgrywek
        mistrzostwa mistrzostw mistrzostwo puchar pucharu pucharze finał
        finału półfinał półfinału ćwierćfinał ćwierćfinału skoki skoków
        narciarskie narciarskich narciarstwo narciarska konkurs konkursu
        skoczni skocznia skocznie igrzyska igrzysk olimpijskie olimpijskich
        olimpijski olimpijska piłka piłki piłkę nożna nożnej ręczna ręcznej
        siatkówka siatkówki siatkowka koszykówka koszykówki koszykowka
        kolarstwo kolarstwa lekkoatletyka lekkoatletyki pływanie pływania
        plywanie wyścig wyścigu wyścigi wyścigów wyscig etap etapu etapy
        dzień dnia dni relacja relacji transmisja transmisji zapowiedź
        zapowiedzi zapowiedz podsumowanie podsumowania kobiet kobiety
        mężczyzn mężczyźni mezczyzn juniorów juniorow juniorzy seniorów
        seniorow drużyna drużyny druzyna reprezentacja reprezentacji
        zwycięzca zwycięzcy świata europy polski polskiej polskie polskich
        polska polskę wielkiej brytanii brytania finałowy finałowe finałowa
        eliminacje eliminacji kwalifikacje kwalifikacji godzina godziny
        godzinny godzinna godzinne minutowy minutowa minutowe zjazd zjazdu
        slalom gigant bieg biegi biegu sprint sprintu sztafeta sztafety
        łyżwiarstwo lyzwiarstwo hokej hokeja żużel zuzel skrót skróty skrot
        magazyn gość goście sekrety sukces sukcesu najlepszy najlepsze
        najlepsza światowy światowa światowe pucharowy
    """.split()),
    "no": frozenset("""
        og eller fra med mot til på av som det den dette denne sesong
        sesongen trening treningen kvalifisering kvalifiseringen mesterskap
        mesterskapet verdenscup verdenscupen norgescup direkte høydepunkter
        hoydepunkter sammendrag fotball håndball ishockey langrenn
        skiskyting alpint kvinner kvinners menn menns damer damers herrer
        herrers utfor slalåm hopp kombinert sending sendingen sendinger
        magasin nyheter kollega skadet hemmelig merkelig bagasje ferske
    """.split()),
    "sv": frozenset("""
        och eller från med mot till på av är som det den detta denna säsong
        säsongen avsnitt avsnittet träning träningen kval kvalet lopp loppet
        världscup världscupen mästerskap mästerskapet höjdpunkter hojdpunkter
        sammandrag fotboll ishockey längdskidåkning skidskytte alpint
        kvinnor kvinnors damer damers herrar herrars magasin nyheter
        sändning direkt repris ingen
    """.split()),
    "fr": frozenset("""
        avec saison saisons épisode épisodes invité invités invitée
        championnat championnats coupe coupes journée journee mondial
        mondiale mondiaux résumé émission émissions inédit inédits différé
        rediffusion natation cyclisme athlétisme escrime aviron canoë
        équitation equitation voile quotidien quotidienne hebdomadaire chez
    """.split()),
    "ro": frozenset("""
        și cel cea cei cele din pentru cu campionat campionatul campionate
        etapa etapei etape meci meciul meciuri fotbal baschet handbal volei
        tenis cursa cursă curse finala finală semifinala semifinală magazin
        emisiune emisiunea știri stiri cupa cupei divizia sezon sezonul
        episod episodul
    """.split()),
    "de": frozenset("""
        und im vom zum zur bei nach vor aus für über meisterschaft
        meisterschaften spieltag spieltages rennen lauf läufe
        zusammenfassung qualifikation qualifikationen weltcup
        weltmeisterschaft europameisterschaft höhepunkte magazin direkt
        wiederholung heute
    """.split()),
    "es": frozenset("""
        temporada episodio capítulo campeonato partido partidos carrera
        carreras mundo mundial resumen directo diferido fútbol baloncesto
        balonmano ciclismo natación atletismo hombres mujeres
    """.split()),
}

_TOKEN_RE = re.compile(r"[^\W\d_]+", flags=re.UNICODE)


def _looks_untranslated(text: str, source_lang: str) -> bool:
    """True when *text* still carries wording in *source_lang*.

    Used as the publication gate for translated programme titles; see the
    section comment above for the rationale and the trade-offs.
    """
    if not text:
        return False
    if re.search(r"[\u0400-\u04FF]", text):
        return True
    hard = _SOURCE_DIACRITICS_HARD.get(source_lang)
    if hard and re.search("[" + re.escape(hard) + "]", text, flags=re.IGNORECASE):
        return True
    words = _RESIDUAL_WORDS.get(source_lang)
    if words:
        tokens = _TOKEN_RE.findall(text.lower())
        if any(token in words for token in tokens):
            return True
    return False


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


def _online_translate_strict(text: str, source_lang: str) -> str | None:
    """Translate via online services only; None when the network path fails.

    Unlike translate_title(), this never falls back to returning the original
    text, so callers can tell "translated" apart from "unavailable".  A
    service result that still looks like the source language (services do
    return source text or half translations for proper-noun-heavy titles)
    is rejected here as well, so it is neither published nor memorised.
    """
    for fn in (_google_translate, _mymemory_translate):
        for attempt in range(2):
            try:
                value = fn(text, source_lang)
                if value and not _looks_untranslated(value, source_lang):
                    return value
            except Exception:
                if attempt == 0:
                    time.sleep(0.25)
    return None


def translate_programme_title(
    title: str,
    source_lang: str,
    exact: Callable[[str], str | None] | None = None,
) -> str:
    """Convert one official programme title to English.

    Resolution order:
      1. ``exact`` -- the version-controlled deterministic mapping for the
         source.  It returns a translation, or None when the title is not
         covered by the curated rules.
      2. Persistent translation memory (``translation_cache.json``).
      3. Online translation services (Google, then MyMemory); a fresh result
         is recorded in the translation memory.

    Every tier's candidate must pass the English-output gate
    (``_looks_untranslated``): a candidate that still carries source-language
    wording falls through to the next tier instead of being published, and a
    fresh online result is only memorised after it passes.

    Raises TitleUntranslatable when no tier produces a translation, so the
    collector can skip that single programme instead of failing the source.
    """
    text = (title or "").strip()
    if not text:
        raise TitleUntranslatable("official programme object has no title")
    if exact is not None:
        try:
            value = exact(text)
        except Exception:
            value = None
        if value and not _looks_untranslated(value, source_lang):
            return value
    cached = _load_cache().get(source_lang, {}).get(text)
    if cached and not _looks_untranslated(cached, source_lang):
        return cached
    online = _online_translate_strict(text, source_lang)
    if online:
        _save_cache_entry(source_lang, text, online)
        return online
    raise TitleUntranslatable(f"no English translation available for {text!r}")
