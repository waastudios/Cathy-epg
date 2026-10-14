# Cathy-epg

## Project

**Cathy-epg** publishes an XMLTV programme-metadata subscription assembled exclusively from broadcaster websites and normal public programme guides of authorised television providers. It does not use EPGshare, epg.pw, IPTV playlists, third-party EPG mirrors, stream URLs, accounts, session replay, geographical bypasses, or access-control workarounds.

> The repository contains metadata only. It does not publish playback links, credentials, cookies, or empty placeholder channels.

The Chinese version of this document is available as [README-CN.md](README-CN.md). The **actual currently published names and XMLTV IDs** for this scope update are generated from the release snapshot in [CHANNELS.md](CHANNELS.md).

Telegram group: https://t.me/garysclub

## Subscription and data files

The subscription URL remains unchanged:

```text
https://raw.githubusercontent.com/waastudios/Cathy-epg/master/data/epg.xml.gz
```

| File | Purpose |
| --- | --- |
| `data/epg.xml.gz` | Gzip-compressed XMLTV subscription file. |
| `data/epg.xml` | Uncompressed XMLTV file for inspection. |
| `data/current_week.jsonl` | Normalised current programme snapshot. |
| `data/status.json` | Per-source collection result and output totals. |
| `CHANNELS.md` | Generated display-name and XMLTV ID inventory for the published snapshot. |

Every XMLTV `display-name` is the provider’s official channel name unless an explicit user-approved normalisation applies. For Sky Germany, a terminal `HD` is removed while `UHD` is retained. The generated [CHANNELS.md](CHANNELS.md) inventory appends `(T)` to identify channels whose programme titles are translated into English; the XMLTV `display-name` remains the official provider name. Stable XMLTV IDs normally follow `<provider>.<channel-id>`; Sky Documentaries uses the user-designated stable ID `ee_uk.352`, and Sky Germany uses the Sky channel number as `sky_de.<number>`.

## Current coverage and enforced scope

| Market | Published services | Official source |
| --- | --- | --- |
| Malaysia | Astro: 22 explicitly allow-listed sports channels | [Astro Content Guide](https://www.astro.com.my/content/channels) |
| Hong Kong | now TV: 37 explicitly allow-listed sports channels | [now TV Guide](https://nowplayer.now.com/tvguide) and [official Chinese channel directory](https://nowplayer.now.com/channels?lang=zh&filterType=all) |
| Germany | 29 Sky Sport and Sky Sport Bundesliga channels, including UHD | [Telekom MagentaTV](https://www.magenta.tv/) public programme guide |
| Sweden | 13 V Sport services, including V Sport UltraHD | [Allente TV Guide](https://www.allente.se/tv-guide/) |
| Norway | TV Norge, REX, FEM, Eurosport Norge, Eurosport 1 | [Allente Norway TV Guide](https://www.allente.no/tv-guide/) |
| United Kingdom | Selected Sky Sports, TNT Sports, BBC, ITV, Channel 4 and Sky Entertainment services | [EE TV Player Live TV Schedule](https://player.ee.co.uk/#/livetv/schedule) |
| United Kingdom | Sky Sports Ultra HD 1 and 2 | [Virgin Media TV Go Guide](https://virgintvgo.virginmedia.com/en/epg/initial) |
| Romania | Digi 4K | [Digi 4K](https://www.digi4k.ro/) |
| Serbia | Eurosport 1, Eurosport 2 and Eurosport 4K | [SBB / EON Public EPG](https://epg.sbb.rs/) |
| Poland | Eurosport 1–4 and Eleven Sports 1 (titles translated to English) | [Player.pl](https://player.pl/) public EPG API |
| France | CANAL+ main channel and CANAL+ FOOT (titles translated to English) | [Canal+ official EPG API](https://www.canalplus.com/programme-tv/) |
| Canada | Love Nature, Travelxp 4K and TSN 1–5 | [TELUS TV+ guide](https://telustvplus.com/#/guide) |
| United States | Tennis Channel 2 | [Peacock channel guide](https://www.peacocktv.com/channels/tennis-channel-2/8969135442586836117) |
| United States | CBS Sports Golazo Network | [Pluto TV guide](https://pluto.tv/us/live-tv/golazo-network) |

### Sky Germany via MagentaTV

The Germany scope is limited to the 29 current Sky Sport and Sky Sport Bundesliga services that MagentaTV’s anonymous public production guide exposes. The collector dynamically reads MagentaTV’s official channel directory on every refresh, requires all mapped services to return programme records, and exports the user-designated Sky channel-number IDs `sky_de.201`–`sky_de.230` (with no published channel 208). Each German programme title is translated to English through the tiered pipeline described below; a title that cannot be translated skips that single programme instead of failing the Sky source. Sky Austria services are not published because the current public directory does not expose an unambiguous matching set.

### EE Sky Entertainment selection

The EE scope includes **Sky Mix, Sky Arts, Sky Witness, Sky Atlantic, Sky One, Sky Comedy, Sky Sci-Fi, Sky Crime, Sky Documentaries, Sky History, and Sky Nature**. Where EE presents parallel versions, Sky Mix and Sky Arts use the DVB/television service; the others use the standard-definition primary service. HD, +1, accessibility, and other duplicate mirrors are not published. The exact IDs and display names are in [CHANNELS.md](CHANNELS.md).

### ESPN status

**ESPN, ESPN2, ESPNEWS, and ESPNU** remain under evaluation for potential future coverage. ABC, CBS, NBC, FOX, USA Network, and every other US broadcast network are excluded. DIRECTV’s public guide confirms the four ESPN services but exposes only current-programme information; Spectrum’s detailed guide requires account and service-address access; and ESPN’s direct schedule does not offer stable per-channel end times. Consequently, **no ESPN records are currently published**. If a compliant guide becomes available, IDs will be provider-prefixed, for example `directv_espn`. The US streaming service that is published (Peacock) is described below.

**Eurosport 1, Eurosport 2 and Eurosport 4K** are published from Serbia’s normal anonymous SBB Public EPG as `eurosport.1`, `eurosport.2` and `eurosport.4k`. The source provides a channel directory plus programme titles, start times, and end times. Each Serbian source title is converted to English through the tiered pipeline described below; a title that cannot be translated skips that single programme instead of failing the SBB source.

**Love Nature**, **Travelxp 4K** and **TSN 1–5** are published from Canada’s TELUS TV+ (Optik TV) official web guide as `telus.713`, `telus.716` and `telus.900`–`telus.904`. The guide’s public AVS API is queried anonymously (production first, QA fallback); channels are matched by their official names, and TSN’s regional blackout variants are never used. Programme titles arrive in English and are published as-is.

**Tennis Channel 2** is published from Peacock’s official BFF channel guide as `TC2.us`. The guide is queried anonymously with the Sky OTT platform headers Peacock’s own clients send; no account is required. The API accepts a start time only within one day in the past to two days in the future and returns roughly 30 hours per call, so the collector stitches four staggered windows (about four days of rolling coverage) instead of a single 7-day pull. Programme titles arrive in English and are published as-is.

**CBS Sports Golazo Network** is published from Pluto TV’s official guide API as `GolazoNet.us`. Pluto TV is Paramount’s own free streaming platform and carries the channel as “Golazo Network”; its guide API is queried anonymously in 24-hour windows. (Paramount+’s own apps-api guide is not usable here: it rejects anonymous requests.) Pluto publishes full per-programme detail only about one to two days ahead; beyond that it publishes whole-day “Golazo Network” blocks, which are reproduced as-is. Programme titles arrive in English and are published as-is.

### Poland via Player.pl

**Eurosport 1, Eurosport 2, Eurosport 3, Eurosport 4 and Eleven Sports 1** are published from Poland’s TVN Player.pl anonymous public EPG API. The user-designated XMLTV IDs are `eurosport1.pl`, `eurosport2.pl`, `eurosport3.pl`, `eurosport4.pl` and `ElevenSp.1`. Each Polish source title is converted to English through the tiered pipeline described below (curated Polish sports-term mapping, then the translation memory, then online services); a title that cannot be translated skips that single programme instead of failing the Player.pl source. In [CHANNELS.md](CHANNELS.md) these five channels carry a (T) mark to indicate their guides are translated into English.

### France via the official Canal+ API

**CANAL+** (main channel) and **CANAL+ FOOT** are published from the official Canal+ EPG API as `canal+.fr` and `foot+.fr`. A fresh token is fetched from the authenticate endpoint on every run because hard-coded tokens are rejected; the API is aggressively rate-limited, so requests are paced 90 seconds apart and retried. Each French source title is converted to English through the tiered pipeline described below (curated French mapping, then the translation memory, then online services); a title that cannot be translated skips that single programme instead of failing the source. Only the official API is used, no third-party fallback. In [CHANNELS.md](CHANNELS.md) both channels carry a (T) mark to indicate their guides are translated into English.

### English translation

Programme titles from non-English markets (Swedish, Norwegian, German, Romanian, Serbian, Polish, French) are published in English; Chinese titles from now TV Hong Kong are kept as-is. Translation runs inside each collector in three tiers:

1. **Version-controlled exact mapping** in `src/epg_tool/sources.py` — curated deterministic rules per source.
2. **Persistent translation memory** in `src/epg_tool/translation_cache.json` — every online translation is recorded here, so results are stable, auditable, and reused without another network call. The daily workflow commits this file, so the memory grows over time.
3. **Online translation services** (Google, then MyMemory) for titles the first two tiers do not cover.

A title that no tier can translate skips that single programme (recorded in `data/status.json` under the provider’s `notes`) instead of failing the whole source, so one new title can never wipe out a channel’s guide.

## Refresh and validation

The GitHub Actions workflow in `.github/workflows/refresh-epg.yml` runs daily at **19:00 UTC**, which is **03:00 China Standard Time (UTC+8) on the following calendar day**. It runs `epg collect --days 7` across **every configured official channel source**, writes the complete snapshot and XMLTV files (`data/epg.xml` and `data/epg.xml.gz`), and commits only when the results change. If an official source is temporarily unavailable, the workflow records that failure in `data/status.json` rather than substituting third-party data.

A current release is considered valid only when `data/epg.xml.gz` decompresses exactly to `data/epg.xml`, all XMLTV channel display names are official names, the Astro and now TV channel IDs are within their explicit sports allow-lists, and prohibited US provider IDs are absent.

## Local use

Python 3.11 or newer is required.

```bash
python -m pip install -e .
epg collect --days 7
epg search "Premier League" --provider now_hk --channel 611
```

### Three-day programme preview

The published snapshot retains up to seven days of official scheduling data. The `preview` command presents **today, tomorrow, and the day after tomorrow** in China Standard Time by default; use `--day` to show one of those three days and the standard provider/channel filters to narrow the result.

```bash
epg preview
epg preview --day tomorrow --provider allente_se --channel 50048
```

For Serbia’s SBB Eurosport schedules, titles are converted during collection using a version-controlled local Serbian-to-English mapping and controlled rules. Daily refreshes do not call an online translation service, so translation does not add network latency.

## Changelog

- **2026-10-14** — Added CBS Sports Golazo Network (`GolazoNet.us`) from Pluto TV's official guide API, queried anonymously in 24-hour windows. Pluto TV is Paramount's own free streaming platform (Paramount+'s own apps-api guide rejects anonymous requests, so it cannot be used). Pluto publishes full programme detail about one to two days ahead; later days carry its published whole-day "Golazo Network" blocks.
- **2026-10-14** — Added TSN 1–5 (`telus.900`–`telus.904`) from the TELUS TV+ official guide; channels are matched by official name (space/case-insensitive, which also makes Travelxp 4K matching robust against the guide's "Travel XP 4K" spelling) and TSN's regional blackout variants are excluded. Added Tennis Channel 2 (`TC2.us`) from Peacock's official BFF channel guide, queried anonymously; the API's rolling window (start time within −1/+2 days, ~30 hours per call) is stitched from four staggered calls for about four days of coverage. Also fixed the channel-inventory generator: the Canada section was missing from the section order, so TELUS channels never rendered in CHANNELS.md.
- **2026-10-12** — Added Canada coverage: Love Nature (`telus.713`) and Travelxp 4K (`telus.716`) from the TELUS TV+ (Optik TV) official web guide's public AVS API, queried anonymously (production first, QA fallback). Titles arrive in English and are published as-is. Removed Poland's CANAL+ 4K ULTRA HD (`canal+4k.pl`) and the SBB European Travel XP feed (`travelxp.eu`); Travelxp 4K on TELUS replaces the SBB feed.
- **2026-09-29** — Restored both France Canal+ channels from the official Canal+ EPG API as `canal+.fr` (CANAL+) and `foot+.fr` (CANAL+ FOOT), 7 days each. A fresh token is fetched from the authenticate endpoint on every run (hard-coded tokens are rejected); the API is aggressively rate-limited so requests are paced 90 seconds apart with retries. French titles are converted to English through the tiered translation pipeline and marked (T) in CHANNELS.md. Only the official API is used, no third-party fallback.
- **2026-09-28** — Added Travel XP (European feed) from the SBB Public EPG as `travelxp.eu`. Titles arrive in English and are published as-is, marked (T) in CHANNELS.md.
- **2026-09-28** — Added Poland coverage: Eurosport 1–4 and Eleven Sports 1 from the Player.pl public EPG API, with user-designated XMLTV IDs `eurosport1.pl`, `eurosport2.pl`, `eurosport3.pl`, `eurosport4.pl` and `ElevenSp.1`. Polish titles are translated to English through the tiered pipeline and marked (T) in CHANNELS.md.

## References

[1]: https://ee.co.uk/help/tv-sport/ee-tv-channel-guide "EE TV Channel Guide"
[2]: https://player.ee.co.uk/#/livetv/schedule "EE TV Player — Live TV Schedule"
[3]: https://www.astro.com.my/content/channels "Astro Content Guide"
[4]: https://nowplayer.now.com/tvguide "now TV Hong Kong — TV Guide"
[5]: https://virgintvgo.virginmedia.com/en/epg/initial "Virgin Media TV Go — Guide"
