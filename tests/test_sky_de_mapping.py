from __future__ import annotations

import unittest

from epg_tool.sources import (
    MAGENTA_TV_SKY_CHANNELS,
    SKY_DE_TITLE_TRANSLATIONS,
    SourceUnavailable,
    _magenta_tv_sky_groups,
    _translate_magenta_tv_sky_de_title,
)


class SkyGermanyMappingTests(unittest.TestCase):
    def test_channel_count_and_user_designated_numbers(self) -> None:
        configured_numbers = {number for number, _ in MAGENTA_TV_SKY_CHANNELS.values()}
        expected = {str(number) for number in [201, 202, 203, 204, 205, 206, 207, 209, 210, *range(211, 221), *range(221, 231)]}
        self.assertEqual(len(MAGENTA_TV_SKY_CHANNELS), 29)
        self.assertEqual(configured_numbers, expected)
        self.assertNotIn("208", configured_numbers)

    def test_channel_names_remain_official_after_normalisation(self) -> None:
        for _, display_name in MAGENTA_TV_SKY_CHANNELS.values():
            self.assertFalse(display_name.endswith(" HD"))
            self.assertFalse(display_name.endswith("(T)"))
            self.assertFalse(display_name.endswith("（T）"))
        self.assertEqual(MAGENTA_TV_SKY_CHANNELS["Sky Sport UHD"][1], "Sky Sport UHD")
        self.assertEqual(MAGENTA_TV_SKY_CHANNELS["Sky Sport Bundesliga UHD"][1], "Sky Sport Bundesliga UHD")

    def test_current_published_titles_have_static_english_mappings(self) -> None:
        self.assertGreaterEqual(len(SKY_DE_TITLE_TRANSLATIONS), 500)
        self.assertEqual(_translate_magenta_tv_sky_de_title("Sendepause"), "Off Air")
        self.assertEqual(_translate_magenta_tv_sky_de_title("F1: Rennen - GP Niederlande"), "F1: Race - GP Netherlands")
        self.assertEqual(
            _translate_magenta_tv_sky_de_title("DFB-Pokal: Alle Spiele, alle Tore, 1. Runde (Freitag)"),
            "DFB-Pokal: All matches, all goals, 1st Round (Friday)",
        )

    def test_new_titles_use_only_controlled_fallback_translation(self) -> None:
        self.assertEqual(
            _translate_magenta_tv_sky_de_title("Live Fußball: 3. Spieltag"),
            "Live Football: 3. Matchday",
        )
        with self.assertRaises(SourceUnavailable):
            _translate_magenta_tv_sky_de_title("Unbekannte deutsche Sendung")

    def test_seven_day_groups_never_exceed_eleven_channels(self) -> None:
        directory = [(position, f"Channel {position}", f"service-{position}", str(position), f"Channel {position}") for position in range(100, 112)]
        self.assertEqual(_magenta_tv_sky_groups(directory), [(100, 110), (111, 111)])


if __name__ == "__main__":
    unittest.main()
