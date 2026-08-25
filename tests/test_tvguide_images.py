from __future__ import annotations

from datetime import datetime
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from xml.etree import ElementTree as ET

from epg_tool.models import Programme
from epg_tool.tvguide_images import enrich_tvguide_uk_images, parse_tvguide_schedule
from epg_tool.xmltv import write_xmltv


IMAGE_URL = "https://tv.assets.pressassociation.io/fcb61a5d-5637-5517-aa51-edb1548f5a79.jpg"
DETAIL_URL = "https://www.tvguide.co.uk/schedule/8fad938f-686f-5666-be7f-3c66e1814e03/formula-1"
SCHEDULE_HTML = f"""
<div class="js-schedule" data-date="2026-08-25T12:00:00.000Z">
  <a href="{DETAIL_URL}">Formula 1</a>
  <a href="{DETAIL_URL}"><img src="{IMAGE_URL}" alt="" /></a>
</div>
"""


class _FakeResponse:
    def __init__(self, html: str) -> None:
        self.text = html

    def raise_for_status(self) -> None:
        return None


class _FakeSession:
    def __init__(self, html: str) -> None:
        self.html = html
        self.headers: dict[str, str] = {}
        self.calls: list[tuple[str, dict[str, str]]] = []

    def get(self, url: str, *, params: dict[str, str], timeout: int) -> _FakeResponse:
        self.calls.append((url, params))
        return _FakeResponse(self.html)


def _programme(*, title: str = "Live: Formula 1", start_at: str = "2026-08-25T13:00:00+01:00", image_url: str | None = None) -> Programme:
    return Programme(
        provider="ee_uk",
        country="GB",
        timezone="Europe/London",
        channel_id="424",
        channel_number="424",
        channel_name="Sky Sports F1",
        title=title,
        start_at=start_at,
        end_at="2026-08-25T14:00:00+01:00",
        source_url="https://player.ee.co.uk/#/livetv/schedule",
        retrieved_at="2026-08-25T12:00:00Z",
        image_url=image_url,
    )


class TVGuideImageTests(unittest.TestCase):
    def test_parser_returns_programme_image_and_detail_url(self) -> None:
        entries = parse_tvguide_schedule(SCHEDULE_HTML)
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0].title, "Formula 1")
        self.assertEqual(entries[0].image_url, IMAGE_URL)
        self.assertEqual(entries[0].detail_url, DETAIL_URL)
        self.assertEqual(entries[0].start_at, datetime.fromisoformat("2026-08-25T12:00:00+00:00"))

    def test_enrichment_requires_same_channel_day_time_and_title(self) -> None:
        session = _FakeSession(SCHEDULE_HTML)
        enriched, stats = enrich_tvguide_uk_images([_programme()], session=session, pause_seconds=0)
        self.assertEqual(enriched[0].image_url, IMAGE_URL)
        self.assertEqual(enriched[0].image_source_url, DETAIL_URL)
        self.assertEqual(stats["matched_images"], 1)
        self.assertEqual(stats["unmatched_programmes"], 0)
        self.assertEqual(session.calls[0][1], {"date": "2026-08-25"})

        unmatched, miss_stats = enrich_tvguide_uk_images(
            [_programme(start_at="2026-08-25T13:05:00+01:00")], session=_FakeSession(SCHEDULE_HTML), pause_seconds=0
        )
        self.assertIsNone(unmatched[0].image_url)
        self.assertEqual(miss_stats["matched_images"], 0)
        self.assertEqual(miss_stats["unmatched_programmes"], 1)

    def test_xmltv_emits_programme_icon_only_when_artwork_exists(self) -> None:
        with TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            xml_path = root / "epg.xml"
            gzip_path = root / "epg.xml.gz"
            write_xmltv([_programme(image_url=IMAGE_URL)], xml_path, gzip_path)
            programme = ET.parse(xml_path).getroot().find("programme")
            self.assertIsNotNone(programme)
            icon = programme.find("icon") if programme is not None else None
            self.assertIsNotNone(icon)
            self.assertEqual(icon.get("src") if icon is not None else None, IMAGE_URL)
            backdrop = programme.find("image") if programme is not None else None
            self.assertIsNotNone(backdrop)
            self.assertEqual(backdrop.get("type") if backdrop is not None else None, "backdrop")
            self.assertEqual(backdrop.text if backdrop is not None else None, IMAGE_URL)


if __name__ == "__main__":
    unittest.main()
