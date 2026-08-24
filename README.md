# Cathy-epg

Cathy-epg is an **official-source-only** XMLTV collector and local search utility. It gathers programme metadata solely from broadcaster websites and official TV-provider guides. It does **not** use EPGshare, epg.pw, IPTV playlists, third-party EPG mirrors, or unauthorised data interfaces.

> The repository contains only channel and programme metadata snapshots. It does not include streams, playback URLs, user accounts, session cookies, or access-control bypasses.

Chinese documentation is available in [README-CN.md](README-CN.md).

## Coverage and source boundaries

| Market | Channel or service | Official source | Current coverage | Language |
| --- | --- | --- | --- | --- |
| Malaysia | Astro | [Astro Content Guide](https://www.astro.com.my/content/channels) | Full seven-day linear schedule | Source language |
| Hong Kong | NOW TV | [NOW TV Guide](https://nowplayer.now.com/tvguide) and the [Chinese channel directory](https://nowplayer.now.com/channels?lang=zh&filterType=all) | Full seven-day linear schedule; official Chinese channel display names | Primarily Chinese |
| Sweden | V Sport portfolio | [Allente TV Guide](https://www.allente.se/tv-guide/) | Full seven-day schedule for 13 V Sport channels | Source language |
| United Kingdom | NOW Sports / Sky Sports | [Sky Sports live schedule](https://www.sky.com/watch/channel/sky-sports) | Official live-event listings, channel names, and start times; not a full linear EPG | English |
| Romania | Digi 4K | [Digi 4K](https://www.digi4k.ro/) | Public seven-day schedule | Romanian |
| Türkiye | Eurosport 1 and Eurosport 2 | [TV+ Eurosport 1](https://tvplus.com.tr/canli-tv/yayin-akisi/eurosport-1-hd--77) and [TV+ Eurosport 2](https://tvplus.com.tr/canli-tv/yayin-akisi/eurosport-2-hd--106) | Public full-day schedule shown by the official TV provider | Turkish |

The Swedish portfolio comprises **V sport extra HD, premium HD, football HD, vinter HD, motor HD, V sport 1 HD, ultra HD, golf HD, and V sport live 1–5**. Allente’s stable channel IDs are retained in the XMLTV output.

The official UK NOW TV website does not publicly expose a complete seven-day, linear XMLTV guide. To preserve the official-source-only scope, Cathy-epg includes only Sky Sports live events explicitly published by Sky, with the listed channel and start time. Where no end time is published, the XMLTV programme omits `stop` rather than inferring a duration.

The English HBO Max Türkiye site confirms the local availability of Eurosport 1, Eurosport 2, and live sports. It does not publish a channel-by-channel schedule, so programme items are sourced from the official Turkish TV+ provider guide instead.[1]

## XMLTV data and subscription

| File | Purpose |
| --- | --- |
| `data/epg.xml.gz` | Gzip-compressed XMLTV file for clients that support XMLTV subscriptions. |
| `data/epg.xml` | Uncompressed XMLTV output for inspection and debugging. |
| `data/current_week.jsonl` | Normalised source snapshot, with one programme record per line. |
| `data/status.json` | Collection status, record count, and output totals for each source. |

### Subscription URL

```text
https://raw.githubusercontent.com/waastudios/Cathy-epg/master/data/epg.xml.gz
```

Channel IDs use the stable `<provider>.<channel-id>` form. For example, Hong Kong NOW TV channel ID **`now_hk.138`** is unchanged while its display name is normalised to the official Chinese name **Now爆谷星影台**.

## Run locally

Python 3.11 or newer is required. The following commands collect the available official schedules and generate JSONL, XMLTV, and gzip outputs.

```bash
python -m pip install -e .
epg collect --days 7
```

Local search reads only the generated JSONL snapshot.

```bash
epg search "Premier League"
epg search "Now爆谷" --provider now_hk --channel 138
epg search "Eurosport" --provider tvplus_tr
```

Schedules can change at short notice. Before automating a refresh, review the relevant provider terms, limit request frequency, and inspect `data/status.json` if a source is unavailable rather than substituting third-party data.

## Automatic daily refresh

The repository includes a GitHub Actions workflow at `.github/workflows/refresh-epg.yml`. It runs every day at **19:00 UTC**, which is **03:00 China Standard Time (UTC+8) on the following calendar day**, and can also be started manually from the repository's Actions page.

Each run executes `epg collect --days 7`, updates the JSONL and XMLTV outputs, and commits only when the snapshot changes. If an official source is temporarily unavailable, the workflow keeps the collected output from the other sources and records the source-level failure in `data/status.json`; it does not substitute third-party data.

## References

[1]: https://www.hbomax.com/tr/en "HBO Max Türkiye — English site"
[2]: https://content.astro.com.my/channels "Astro Content Guide — Channel guide"
[3]: https://nowplayer.now.com/tvguide "NOW TV Hong Kong — TV Guide"
[4]: https://www.allente.se/tv-guide/ "Allente — TV Guide"
[5]: https://www.sky.com/watch/channel/sky-sports "Sky Sports — Live schedule"
[6]: https://www.digi4k.ro/ "Digi 4K România"
[7]: https://tvplus.com.tr/canli-tv/yayin-akisi/eurosport-1-hd--77 "TV+ — Eurosport 1 schedule"
[8]: https://tvplus.com.tr/canli-tv/yayin-akisi/eurosport-2-hd--106 "TV+ — Eurosport 2 schedule"
