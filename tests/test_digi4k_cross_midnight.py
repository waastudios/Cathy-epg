"""Regression coverage for Digi 4K day-container midnight boundaries."""

from datetime import datetime

import epg_tool.sources as sources


def test_digi4k_cross_midnight_programmes_always_have_stops(monkeypatch) -> None:
    """The official 22:00 Real Madrid item must end at the official 00:05 item."""
    # Isolate start/stop derivation from the separate strict title-translation policy.
    monkeypatch.setattr(sources, "_translate_digi4k_title", lambda title: title)

    records = sources.collect_digi4k(days=7)

    assert records
    assert all(record.end_at for record in records)
    assert all(
        datetime.fromisoformat(record.end_at) > datetime.fromisoformat(record.start_at)
        for record in records
    )

    real_madrid = next(record for record in records if record.title == "Real Madrid vs Real Sociedad")
    start = datetime.fromisoformat(real_madrid.start_at)
    end = datetime.fromisoformat(real_madrid.end_at)
    assert (start.hour, start.minute) == (22, 0)
    assert end.date() > start.date()
    assert (end.hour, end.minute) == (0, 5)
