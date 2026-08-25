from __future__ import annotations

import unittest

from epg_tool.sources import MAGENTA_TV_SKY_CHANNELS, _magenta_tv_sky_groups


class SkyGermanyMappingTests(unittest.TestCase):
    def test_channel_count_and_user_designated_numbers(self) -> None:
        configured_numbers = {number for number, _ in MAGENTA_TV_SKY_CHANNELS.values()}
        expected = {str(number) for number in [201, 202, 203, 204, 205, 206, 207, 209, 210, *range(211, 221), *range(221, 231)]}
        self.assertEqual(len(MAGENTA_TV_SKY_CHANNELS), 29)
        self.assertEqual(configured_numbers, expected)
        self.assertNotIn("208", configured_numbers)

    def test_terminal_hd_is_removed_and_uhd_is_preserved(self) -> None:
        for source_name, (_, display_name) in MAGENTA_TV_SKY_CHANNELS.items():
            self.assertFalse(display_name.endswith(" HD"))
            if source_name.endswith(" HD"):
                self.assertEqual(display_name, source_name.removesuffix(" HD"))
        self.assertEqual(MAGENTA_TV_SKY_CHANNELS["Sky Sport UHD"][1], "Sky Sport UHD")
        self.assertEqual(MAGENTA_TV_SKY_CHANNELS["Sky Sport Bundesliga UHD"][1], "Sky Sport Bundesliga UHD")

    def test_seven_day_groups_never_exceed_eleven_channels(self) -> None:
        directory = [(position, f"Channel {position}", f"service-{position}", str(position), f"Channel {position}") for position in range(100, 112)]
        self.assertEqual(_magenta_tv_sky_groups(directory), [(100, 110), (111, 111)])


if __name__ == "__main__":
    unittest.main()
