# Published channels

This inventory is generated from the currently published `data/current_week.jsonl` and verified against `data/epg.xml.gz`. It lists channels that are actually published in the XMLTV output; each displayed name is the actual XMLTV `display-name`.

The snapshot generated at `2026-08-24T19:13:20Z` contains **120 channels** and **15368 programmes**. Its gzip file expands byte-for-byte to `data/epg.xml`.

## Astro — sports-only published channels

All non-sports Astro channels are excluded. The following 22 current official services remain.

| XMLTV ID | Official display name |
| --- | --- |
| `astro.801` | Astro Arena |
| `astro.802` | Stadium Astro |
| `astro.803` | Arena Bola |
| `astro.804` | Arena Bola 2 |
| `astro.805` | Astro Sports UHD 805 |
| `astro.806` | Sukan+ |
| `astro.810` | Astro Grandstand |
| `astro.811` | Astro Premier League |
| `astro.812` | Astro Premier League 2 |
| `astro.813` | Astro Premier League 3 |
| `astro.814` | Astro Football |
| `astro.815` | Astro Badminton |
| `astro.817` | Astro Sports Plus |
| `astro.818` | Astro Sports Plus 2 |
| `astro.819` | Astro Tennis |
| `astro.820` | beIN SPORTS 1 |
| `astro.821` | beIN SPORTS 2 |
| `astro.822` | beIN SPORTS 3 |
| `astro.826` | W-Sport |
| `astro.831` | Astro Golf |
| `astro.832` | CricBuzz |
| `astro.833` | Premier Sports |

## NOW TV Hong Kong — sports-only published channels

All non-sports NOW TV channels are excluded, including `now_hk.138` (Now爆谷星影台). The following 37 current official services remain.

| XMLTV ID | Official display name |
| --- | --- |
| `now_hk.611` | Now Sports 4K 1 |
| `now_hk.612` | Now Sports 4K 2 |
| `now_hk.613` | Now Sports 4K 3 |
| `now_hk.620` | Now Sports Premier League TV |
| `now_hk.621` | Now Sports 英超1台 |
| `now_hk.622` | Now Sports 英超2台 |
| `now_hk.623` | Now Sports 英超3台 |
| `now_hk.624` | Now Sports 英超4台 |
| `now_hk.625` | Now Sports 英超5台 |
| `now_hk.626` | Now Sports 英超6台 |
| `now_hk.627` | Now Sports 英超7台 |
| `now_hk.630` | Now Sports 精選 |
| `now_hk.631` | Now Sports 1 |
| `now_hk.632` | Now Sports 2 |
| `now_hk.633` | Now Sports 3 |
| `now_hk.634` | Now Sports 4 |
| `now_hk.635` | Now Sports 5 |
| `now_hk.636` | Now Sports 6 |
| `now_hk.637` | Now Sports 7 |
| `now_hk.638` | beIN SPORTS 1 |
| `now_hk.639` | beIN SPORTS 2 |
| `now_hk.640` | 曼聯電視頻道 |
| `now_hk.641` | Now Sports 641 |
| `now_hk.642` | NBA TV |
| `now_hk.643` | beIN SPORTS 3 |
| `now_hk.644` | beIN SPORTS 4 |
| `now_hk.645` | beIN SPORTS 5 |
| `now_hk.646` | beIN SPORTS 6 |
| `now_hk.647` | Now Sports 647 |
| `now_hk.651` | Now Sports 651 |
| `now_hk.652` | Now Sports 652 |
| `now_hk.668` | Now668 |
| `now_hk.674` | Cricbuzz |
| `now_hk.679` | Premier Sports |
| `now_hk.680` | Now Sports Plus |
| `now_hk.683` | Now Golf 2 |
| `now_hk.684` | Now Golf 3 |

## EE TV Player — requested Sky Entertainment channels

This table lists the EE Sky Entertainment services actually published in the current XMLTV output.

| XMLTV ID | Official display name |
| --- | --- |
| `ee_uk.11` | Sky Mix |
| `ee_uk.36` | Sky Arts |
| `ee_uk.341` | Sky Witness |
| `ee_uk.342` | Sky Atlantic |
| `ee_uk.346` | Sky One |
| `ee_uk.347` | Sky Comedy |
| `ee_uk.348` | Sky Sci-Fi |
| `ee_uk.349` | Sky Crime |
| `ee_uk.352` | Sky Documentaries |
| `ee_uk.353` | Sky History |
| `ee_uk.354` | Sky Nature |

## SBB Public EPG — Eurosport 4K

| XMLTV ID | Official display name |
| --- | --- |
| `sbb_rs.1082` | Eurosport 4K IPTV |

## Not published

| Requested service | Publication decision | Reason |
| --- | --- | --- |
| ESPN / ESPN2 / ESPNEWS / ESPNU | Not added | No compliant anonymous authorised-provider source currently provides reusable per-event start and stop timing. If added later, IDs will carry the provider prefix (for example, `directv_espn`). |

## Current provider totals

| Provider | Channels | Programme records |
| --- | ---: | ---: |
| `allente_no` | 4 | 704 |
| `allente_se` | 13 | 896 |
| `astro` | 22 | 2499 |
| `digi4k_ro` | 1 | 115 |
| `ee_uk` | 38 | 6442 |
| `now_hk` | 37 | 4526 |
| `sbb_rs` | 1 | 67 |
| `tvplus_tr` | 2 | 34 |
| `virgin_uk` | 2 | 85 |

## Source and policy

All data is obtained only from broadcaster websites or normal public guides of authorised TV providers. The project does not use third-party EPG aggregators, IPTV playlists, account access, session replay, geographical bypasses, or empty placeholder channels.

The subscription file remains: `https://raw.githubusercontent.com/waastudios/Cathy-epg/master/data/epg.xml.gz`.
