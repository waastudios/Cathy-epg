from __future__ import annotations

import json
import xml.etree.ElementTree as ET
from pathlib import Path
import sys

sys.path.insert(0, "src")
from epg_tool.translation_fallback import translate_title

LANG_BY_PROVIDER = {
    "allente_se": "sv",
    "allente_no": "no",
    "canalplus_fr": "fr",
    "digi4k": "ro",
    "tvplus_eurosport": "tr",
    "sbb_eurosport": "sr",
    "magenta_tv_sky_de": "de",
}

# Exact recurring titles that must never depend on a network translator.
HARD = {
    "Formel 1 - Kval: Italian GP: Qualifying - Pitlane Channel": "Formula 1 - Qualifying: Italian GP: Qualifying - Pitlane Channel",
    "Formel 2: Italien GP - Träning": "Formula 2: Italian GP - Practice",
    "Grensevakten Sverige: Tatt på fersken": "Border Patrol Sweden: Caught Red-Handed",
    "Jamel Comedy Club — Invités : Bruno Sanches, Youssef...": "Jamel Comedy Club — Guests: Bruno Sanches, Youssef...",
}


def provider_for_channel(channel: str) -> str | None:
    return channel.split(".", 1)[0] if "." in channel else None


def main() -> None:
    path = Path("data/epg.xml")
    tree = ET.parse(path)
    root = tree.getroot()
    changed = 0
    translated = 0

    for programme in root.findall("programme"):
        provider = provider_for_channel(programme.get("channel", ""))
        lang = LANG_BY_PROVIDER.get(provider or "")
        if not lang:
            continue
        title = programme.find("title")
        if title is None or not (title.text or "").strip():
            continue
        original = title.text.strip()
        value = HARD.get(original)
        if value is None:
            value = translate_title(original, lang)
        if value and value != original:
            title.text = value
            changed += 1
        translated += 1

    tree.write(path, encoding="utf-8", xml_declaration=True)
    print(f"Translation pass: inspected={translated}, changed={changed}")


if __name__ == "__main__":
    main()
