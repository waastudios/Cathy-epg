"""Regression coverage for the dedicated F1-channel title adaptation."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from epg_tool.f1_titles import adapt_f1_title


def test_f1_session_titles_are_deterministic() -> None:
    cases = {
        "F1: 1. Freies Training - GP Singapur": "F1: 1st Free Practice - GP Singapore",
        "F1: 2. Freies Training - GP Singapur": "F1: 2nd Free Practice - GP Singapore",
        "F1: 3. Freies Training - GP Aserbaidschan": "F1: 3rd Free Practice - GP Azerbaijan",
        "F1: Rennen - GP Aserbaidschan": "F1: Race - GP Azerbaijan",
        "F1: Rennen Kompakt - GP Singapur": "F1: Race Compact - GP Singapore",
        "F1: Sprint - GP Singapur": "F1: Sprint - GP Singapore",
        "F1: Sprint-Qualifying - GP Singapur": "F1: Sprint Qualifying - GP Singapore",
        "F1: Zeittraining - GP Spanien": "F1: Qualifying - GP Spain",
        "F1: Qualifying Kompakt - GP Singapur": "F1: Qualifying Compact - GP Singapore",
        "Live F1: Rennen - GP Singapur": "Live F1: Race - GP Singapore",
    }
    for german, expected in cases.items():
        assert adapt_f1_title(german) == expected, german


def test_f1_ordinals_and_venues_across_series() -> None:
    cases = {
        "F2: 1. Rennen - GP Aserbaidschan": "F2: 1st Race - GP Azerbaijan",
        "F2: 2. Rennen - GP Aserbaidschan": "F2: 2nd Race - GP Azerbaijan",
        "F3: 1. Rennen - GP Spanien": "F3: 1st Race - GP Spain",
        "F3: 3. Rennen - GP Spanien": "F3: 3rd Race - GP Spain",
        "F1 Academy: 1. Rennen - GP Niederlande": "F1 Academy: 1st Race - GP Netherlands",
        "F1 Academy: 2. Rennen - GP Niederlande": "F1 Academy: 2nd Race - GP Netherlands",
        "Live HDBWC: 1. Rennen - GP Aragonien": "Live HDBWC: 1st Race - GP Aragon",
        "PMSC: 2. Rennen - GP Niederlande": "PMSC: 2nd Race - GP Netherlands",
        "GTWC: Barcelona (Sprint Cup) - 1. Rennen": "GTWC: Barcelona (Sprint Cup) - 1st Race",
        "IndyCar: Training in West Allis (Wisconsin)": "IndyCar: Practice in West Allis (Wisconsin)",
        "MotoGP: Highlights: GP Indonesien": "MotoGP: Highlights: GP Indonesia",
    }
    for german, expected in cases.items():
        assert adapt_f1_title(german) == expected, german


def test_f1_press_conferences_read_naturally() -> None:
    cases = {
        "F1: Pressekonferenz Fahrer - GP Singapur": "F1: Drivers' Press Conference - GP Singapore",
        "Live F1: Pressekonferenz Teamchefs - GP Singapur": "Live F1: Team Principals' Press Conference - GP Singapore",
        "Live F1: Pressekonferenz Qualifying - GP Bahrain": "Live F1: Post-Qualifying Press Conference - GP Bahrain",
        "F1: Pressekonferenz Sprint - GP Singapur": "F1: Post-Sprint Press Conference - GP Singapore",
        "Live F1: Pressekonferenz Rennen - GP Singapur": "Live F1: Post-Race Press Conference - GP Singapore",
    }
    for german, expected in cases.items():
        assert adapt_f1_title(german) == expected, german


def test_f1_adapter_declines_non_german_titles() -> None:
    # Already-English titles must pass through untouched so the normal
    # pipeline (exact map / cache) keeps working.
    for title in [
        "F1: Qualifying - GP Bahrain",
        "F1: Iconic Onboards: Max Verstappen",
        "F1 Academy: Weekend Wrapped - GP China",
        "F1: Greatest Races: F. Alonso / Nürburgring 2007",
        "Ted's Notebook",
        "",
    ]:
        assert adapt_f1_title(title) is None, title


def test_f1_adapter_never_emits_half_german() -> None:
    # Unknown German wording must decline instead of leaking half-translated
    # titles into the EPG.
    assert adapt_f1_title("F1: Irgendein unbekanntes Spezialformat - GP Singapur") is None


def test_f1_series_aliases() -> None:
    assert adapt_f1_title("Formel 1: Rennen - GP Singapur") == "F1: Race - GP Singapore"
    assert adapt_f1_title("Formel 2: 1. Rennen - GP Spanien") == "F2: 1st Race - GP Spain"
