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
| Norway | TVNorge HD, REX HD, FEM HD, Eurosport Norge HD | [Allente Norway TV Guide](https://www.allente.no/tv-guide/) | Full seven-day channel-level schedule; subtitle and audio-description mirrors excluded | Norwegian / source language |
| United Kingdom | Sky Sports, TNT Sports 1–4, BBC, ITV, Channel 4 and selected Sky Entertainment | [EE TV Player Live TV Schedule](https://player.ee.co.uk/#/livetv/schedule) | Full seven-day channel-level EPG for 31 unique standard-definition channels, with official names and start/end times | English |
| United Kingdom | Sky Sports Ultra HD 1 and Sky Sports Ultra HD 2 | [Virgin Media TV Go Guide](https://virgintvgo.virginmedia.com/en/epg/initial) | Full seven-day schedule from the Guide's normal channel directory and six-hour EPG segments; hidden Duplicate mirrors excluded | English |
| Romania | Digi 4K | [Digi 4K](https://www.digi4k.ro/) | Public seven-day schedule | Romanian |
| Türkiye | Eurosport 1 and Eurosport 2 | [TV+ Eurosport 1](https://tvplus.com.tr/canli-tv/yayin-akisi/eurosport-1-hd--77) and [TV+ Eurosport 2](https://tvplus.com.tr/canli-tv/yayin-akisi/eurosport-2-hd--106) | Public full-day schedule shown by the official TV provider; every title passes an event-aware Turkish-to-English conversion before XMLTV publication | English |

The Swedish portfolio comprises **V sport extra HD, premium HD, football HD, vinter HD, motor HD, V sport 1 HD, ultra HD, golf HD, and V sport live 1–5**. Allente’s stable channel IDs are retained in the XMLTV output.

The UK guide uses the **anonymous public schedule rendered by EE TV Player**. It includes TNT Sports 1–4 (EE channel numbers 408–411); Sky Sports News, Main Event, Premier League, Football, Cricket, Golf, F1, Tennis, Action, +, Racing, and Mix (418–429); BBC One London, BBC Two, BBC Three, BBC Four, BBC News and BBC Parliament; ITV1 London, ITV2, ITV3, ITV4 and ITV Quiz; Channel 4; and the non-film Sky Entertainment channels Sky Atlantic, Sky One and Sky Crime. Every XMLTV display name is the official name returned by the EE Player channel directory, and each programme uses the published start time and duration from its normal schedule request.[2]

To avoid duplicate real-world channels, the dataset contains exactly one standard-definition EE row for each channel. It deliberately excludes matching HD mirrors, +1 services, accessibility variants, the old NOW/Sky event-only feed, Sky Cinema and other movie channels, and unrelated TNT Sports Ultimate, TNT Sports 5, or temporary channels. This is channel-level deduplication, not a merge of competing schedules; `ee_uk.<EE channel number>` is the stable XMLTV channel ID format.

The Norway source is the anonymous public Allente Norway guide. It retains the provider’s standard-channel names **TVNorge HD**, **REX HD**, **FEM HD**, and **Eurosport Norge HD**, while deliberately excluding parallel subtitle and audio-description services. [9]

The Virgin Media source retains the two visible, non-duplicate Ultra services reported by the official channel directory: **Sky Sports Ultra HD 1** (internal channel ID `2258`, logical channel 515) and **Sky Sports Ultra HD 2** (internal channel ID `2265`, logical channel 516). Their XMLTV IDs are consequently **`virgin_uk.2258`** and **`virgin_uk.2265`**. The hidden `Duplicate` entries (`2321` and `2322`) are deliberately excluded.[10]

TV+ title conversion is deterministic and executed for every collected programme. It translates only explicit sport, competition and stage terms in the official title, preserves official event names and never invents participants, results or venues. A title containing an unrecognised Turkish marker fails the TV+ source rather than silently publishing untranslated metadata.

The project does not create empty channels when an official page identifies a service but does not offer reusable public channel-level programme data. The current United States scope is limited to **ESPN, ESPN2, ESPNEWS and ESPNU**. ABC, CBS, NBC, FOX, USA Network and all other US networks are deliberately excluded, with no channels or programme records published from them. ESPN’s current official schedule shows channel-labelled programme starts, but no stable channel-level stop times have been confirmed, so ESPN records are not published yet. The same rule currently excludes FS1/FS2, TBS/truTV, France 2–5, Poland Eurosport 1–4, and NHK domestic channels. Orange Romania TV Go’s normal **Free User** Guide visibly provides Eurosport 4K with precise programme timing, but its daily schedule calls are bound to an ephemeral provider-provisioned session. The Actions workflow does not store or replay session credentials, so Orange Eurosport 4K is not yet published. In particular, NHK’s official text guide limits its programme data to private use unless permission is obtained; no public XMLTV redistribution is made from it.

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

Channel IDs normally use the stable `<provider>.<channel-id>` form. Hong Kong NOW TV channel ID **`now_hk.138`** is unchanged while its display name is normalised to the official Chinese name **Now爆谷星影台**. Digi 4K is the documented single-channel exception requested by the user: its XMLTV channel ID is exactly **`digi4k_ro`**, with official display name **Digi 4K**. Virgin Media Sky Sports Ultra uses the requested official-ID format: **`virgin_uk.2258`** for **Sky Sports Ultra HD 1** and **`virgin_uk.2265`** for **Sky Sports Ultra HD 2**.

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
epg search "TNT Sports" --provider ee_uk
epg search "BBC" --provider ee_uk
epg search "Eurosport" --provider allente_no
epg search "Ultra" --provider virgin_uk
```

Schedules can change at short notice. Before automating a refresh, review the relevant provider terms, limit request frequency, and inspect `data/status.json` if a source is unavailable rather than substituting third-party data.

## Automatic daily refresh

The repository includes a GitHub Actions workflow at `.github/workflows/refresh-epg.yml`. It runs every day at **19:00 UTC**, which is **03:00 China Standard Time (UTC+8) on the following calendar day**, and can also be started manually from the repository's Actions page.

Each run executes `epg collect --days 7`, updates the JSONL and XMLTV outputs, and commits only when the snapshot changes. If an official source is temporarily unavailable, the workflow keeps the collected output from the other sources and records the source-level failure in `data/status.json`; it does not substitute third-party data.

## References

[1]: https://www.hbomax.com/tr/en "HBO Max Türkiye — English site"
[2]: https://player.ee.co.uk/#/livetv/schedule "EE TV Player — Live TV Schedule"
[3]: https://content.astro.com.my/channels "Astro Content Guide — Channel guide"
[4]: https://nowplayer.now.com/tvguide "NOW TV Hong Kong — TV Guide"
[5]: https://www.allente.se/tv-guide/ "Allente — TV Guide"
[6]: https://www.digi4k.ro/ "Digi 4K România"
[7]: https://tvplus.com.tr/canli-tv/yayin-akisi/eurosport-1-hd--77 "TV+ — Eurosport 1 schedule"
[8]: https://tvplus.com.tr/canli-tv/yayin-akisi/eurosport-2-hd--106 "TV+ — Eurosport 2 schedule"
[9]: https://www.allente.no/tv-guide/ "Allente Norway — TV Guide"
[10]: https://virgintvgo.virginmedia.com/en/epg/initial "Virgin Media TV Go — Guide"
