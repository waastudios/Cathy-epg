# Cathy-epg

## Project

**Cathy-epg** publishes an XMLTV programme-metadata subscription whose schedules are assembled from broadcaster websites and normal public programme guides of authorised television providers. It does not use EPGshare, epg.pw, IPTV playlists, third-party EPG mirrors, stream URLs, accounts, session replay, geographical bypasses, or access-control workarounds. For selected UK programmes only, it additionally links artwork from TVGuide.co.uk after the project maintainer obtained permission to do so; this does not replace or alter provider-sourced schedule data.

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

### Authorised UK programme artwork

For mapped EE TV and Virgin Media UK records, the refresh links a TVGuide.co.uk image directly in XMLTV as both the standard `<programme><image type="backdrop" orient="L">…</image></programme>` element and a compatibility `<icon>` element. Images are neither downloaded nor re-hosted. An icon is emitted only when the mapped TVGuide channel page has exactly one candidate with the same normalised programme title and a start time within one minute of the provider record; absent, ambiguous, unsupported-channel, or failed-page matches remain image-free. Programme titles, times, and channels continue to come solely from EE TV or Virgin Media. The daily status file records the number of eligible records, page requests, exact artwork matches, and unmatched records.

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
| United Kingdom artwork | Exact-matched programme icons for mapped EE TV / Virgin Media entries | [TVGuide.co.uk](https://www.tvguide.co.uk/) direct artwork URLs, under maintainer-authorised use |
| Romania | Digi 4K | [Digi 4K](https://www.digi4k.ro/) |
| Türkiye | Eurosport 1 and Eurosport 2 | [TV+ Eurosport 1](https://tvplus.com.tr/canli-tv/yayin-akisi/eurosport-1-hd--77) and [Eurosport 2](https://tvplus.com.tr/canli-tv/yayin-akisi/eurosport-2-hd--106) |
| Serbia | Eurosport 4K | [SBB / EON Public EPG](https://epg.sbb.rs/) |

### Sky Germany via MagentaTV

The Germany scope is limited to the 29 current Sky Sport and Sky Sport Bundesliga services that MagentaTV’s anonymous public production guide exposes. The collector dynamically reads MagentaTV’s official channel directory on every refresh, requires all mapped services to return programme records, and exports the user-designated Sky channel-number IDs `sky_de.201`–`sky_de.230` (with no published channel 208). Each known German programme title is translated through the version-controlled local mapping; controlled sports vocabulary handles new routine titles, while a title that still contains unverified German causes the Sky source to fail rather than publish untranslated text. Sky Austria services are not published because the current public directory does not expose an unambiguous matching set.

### EE Sky Entertainment selection

The EE scope includes **Sky Mix, Sky Arts, Sky Witness, Sky Atlantic, Sky One, Sky Comedy, Sky Sci-Fi, Sky Crime, Sky Documentaries, Sky History, and Sky Nature**. Where EE presents parallel versions, Sky Mix and Sky Arts use the DVB/television service; the others use the standard-definition primary service. HD, +1, accessibility, and other duplicate mirrors are not published. The exact IDs and display names are in [CHANNELS.md](CHANNELS.md).

### ESPN status

The United States scope is intentionally restricted to potential future coverage for **ESPN, ESPN2, ESPNEWS, and ESPNU**. ABC, CBS, NBC, FOX, USA Network, and every other US network are excluded. DIRECTV’s public guide confirms the four ESPN services but exposes only current-programme information; Spectrum’s detailed guide requires account and service-address access; and ESPN’s direct schedule does not offer stable per-channel end times. Consequently, **no ESPN records are currently published**. If a compliant guide becomes available, IDs will be provider-prefixed, for example `directv_espn`.

**Eurosport 4K** is published from SBB’s normal anonymous Public EPG as `eurosport.4k`. The source provides a channel directory plus programme titles, start times, and end times. Each source title is converted through strict deterministic Serbian-to-English rules; an unrecognised title fails the SBB source rather than being guessed or published untranslated.

## Refresh and validation

The GitHub Actions workflow in `.github/workflows/refresh-epg.yml` runs daily at **19:00 UTC**, which is **03:00 China Standard Time (UTC+8) on the following calendar day**. It runs `epg collect --days 7`, writes the snapshot and XMLTV files, and commits only when the results change. If a provider EPG source is temporarily unavailable, the workflow records that failure in `data/status.json` rather than substituting another schedule source. The separately authorised TVGuide artwork enrichment is optional and never blocks publication of provider-sourced programme data.

A current release is considered valid only when `data/epg.xml.gz` decompresses exactly to `data/epg.xml`, all XMLTV channel display names are official names, artwork is emitted only from an exact mapped programme match, the Astro and now TV channel IDs are within their explicit sports allow-lists, and prohibited US provider IDs are absent.

## Local use

Python 3.11 or newer is required.

```bash
python -m pip install -e .
epg collect --days 7
epg search "Premier League" --provider now_hk --channel 611
```

## References

[1]: https://ee.co.uk/help/tv-sport/ee-tv-channel-guide "EE TV Channel Guide"
[2]: https://player.ee.co.uk/#/livetv/schedule "EE TV Player — Live TV Schedule"
[3]: https://www.astro.com.my/content/channels "Astro Content Guide"
[4]: https://nowplayer.now.com/tvguide "now TV Hong Kong — TV Guide"
[5]: https://virgintvgo.virginmedia.com/en/epg/initial "Virgin Media TV Go — Guide"
[6]: https://www.tvguide.co.uk/ "TVGuide.co.uk — programme artwork, project-maintainer authorised use"
