# 已发布频道清单

本清单由当前已发布的 `data/current_week.jsonl` 自动生成，并与 `data/epg.xml.gz` 校验一致。它仅列出 XMLTV 中实际已发布的频道；每个显示名称均为 XMLTV 实际发布的 `display-name`。

当前快照生成时间为 `2026-08-24T19:13:20Z`，包含 **120 个频道** 与 **15368 条节目记录**。其 gzip 文件解压后与 `data/epg.xml` 完全一致。

## Astro：仅发布体育频道

所有非体育 Astro 频道均已排除。以下为当前保留的 22 条官方服务。

| XMLTV ID | 官方显示名称 |
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

## NOW TV 香港：仅发布体育频道

所有非体育 NOW TV 频道均已排除，包括 `now_hk.138`（Now爆谷星影台）。以下为当前保留的 37 条官方服务。

| XMLTV ID | 官方显示名称 |
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

## EE TV Player：指定 Sky 娱乐频道

下表列出当前 XMLTV 实际发布的 EE Sky 娱乐频道。

| XMLTV ID | 官方显示名称 |
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

## SBB Public EPG：Eurosport 4K

| XMLTV ID | 官方显示名称 |
| --- | --- |
| `sbb_rs.1082` | Eurosport 4K IPTV |

## 未发布服务

| 用户请求的服务 | 发布结论 | 原因 |
| --- | --- | --- |
| ESPN / ESPN2 / ESPNEWS / ESPNU | 未添加 | 目前没有合规的匿名授权服务商来源提供可复用的逐节目开始与结束时间。如日后加入，ID 将带服务商前缀，例如 `directv_espn`。 |

## 当前来源总计

| 来源 | 频道数 | 节目记录数 |
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

## 来源与使用规则

所有数据仅来自节目运营商官网或授权电视服务商的正常公开节目表。项目不使用第三方 EPG 聚合网站、IPTV 播放列表、账户访问、会话重放、地域绕过，也不创建空占位频道。

订阅地址保持不变：`https://raw.githubusercontent.com/waastudios/Cathy-epg/master/data/epg.xml.gz`。
