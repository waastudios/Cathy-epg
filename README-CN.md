# Cathy-epg

## 1. 项目介绍

**Cathy-epg** 是一个仅从节目运营商官网及官方电视服务商导览页面汇集节目元数据的 XMLTV 项目。项目不使用 EPGshare、epg.pw、IPTV 播放列表、第三方节目表镜像、视频流、账号数据、会话 Cookie 或访问控制规避方式。

当前 XMLTV 订阅地址：

```text
https://raw.githubusercontent.com/waastudios/Cathy-epg/master/data/epg.xml.gz
```

`data/epg.xml.gz` 为压缩订阅文件，`data/epg.xml` 为可读 XMLTV 文件，`data/current_week.jsonl` 为标准化节目快照。下表的频道名严格使用相应服务商发布的官方名称，所有 XMLTV ID 均取自当前发布版本。

## 2. EPG 所含频道

### 土耳其

#### TV+

| 频道官方名称 | XMLTV ID |
| --- | --- |
| Eurosport 1 | `eurosport.1` |
| Eurosport 2 | `eurosport.2` |

### 挪威

#### Allente 挪威

| 频道官方名称 | XMLTV ID |
| --- | --- |
| Eurosport Norge HD | `allente_no.10022` |
| FEM HD | `allente_no.10010` |
| REX HD | `allente_no.10011` |
| TVNorge HD | `allente_no.10009` |

### 瑞典

#### Allente 瑞典

| 频道官方名称 | XMLTV ID |
| --- | --- |
| V sport 1 HD (S) | `allente_se.50079` |
| V sport extra HD | `allente_se.20092` |
| V sport football HD (S) | `allente_se.50056` |
| V sport golf HD | `allente_se.50077` |
| V sport live 1 | `allente_se.50125` |
| V sport live 2 | `allente_se.50126` |
| V sport live 3 | `allente_se.50127` |
| V sport live 4 | `allente_se.50128` |
| V sport live 5 | `allente_se.50129` |
| V sport motor HD | `allente_se.50048` |
| V sport premium HD (S) | `allente_se.50078` |
| V sport ultra HD | `allente_se.50105` |
| V sport vinter HD (S) | `allente_se.50049` |

### 罗马尼亚

#### Digi 4K

| 频道官方名称 | XMLTV ID |
| --- | --- |
| Digi 4K | `digi4k_ro` |

### 英国

#### EE TV Player

| 频道官方名称 | XMLTV ID |
| --- | --- |
| BBC Four | `ee_uk.9` |
| BBC News | `ee_uk.231` |
| BBC One London | `ee_uk.1` |
| BBC Parliament | `ee_uk.232` |
| BBC Three | `ee_uk.23` |
| BBC Two | `ee_uk.2` |
| Channel 4 | `ee_uk.4` |
| ITV Quiz | `ee_uk.28` |
| ITV1 London | `ee_uk.3` |
| ITV2 | `ee_uk.6` |
| ITV3 | `ee_uk.10` |
| ITV4 | `ee_uk.26` |
| Sky Atlantic | `ee_uk.342` |
| Sky Crime | `ee_uk.349` |
| Sky One | `ee_uk.346` |
| Sky Sports + | `ee_uk.427` |
| Sky Sports Action | `ee_uk.426` |
| Sky Sports Cricket | `ee_uk.422` |
| Sky Sports F1 | `ee_uk.424` |
| Sky Sports Football | `ee_uk.421` |
| Sky Sports Golf | `ee_uk.423` |
| Sky Sports Main Event | `ee_uk.419` |
| Sky Sports Mix | `ee_uk.429` |
| Sky Sports News | `ee_uk.418` |
| Sky Sports Premier League | `ee_uk.420` |
| Sky Sports Racing | `ee_uk.428` |
| Sky Sports Tennis | `ee_uk.425` |
| TNT Sports 1 | `ee_uk.408` |
| TNT Sports 2 | `ee_uk.409` |
| TNT Sports 3 | `ee_uk.410` |
| TNT Sports 4 | `ee_uk.411` |

#### Virgin Media TV Go

| 频道官方名称 | XMLTV ID |
| --- | --- |
| Sky Sports Ultra HD 1 | `virgin_uk.2258` |
| Sky Sports Ultra HD 2 | `virgin_uk.2265` |

### 香港

#### NOW TV

| 频道官方名称 | XMLTV ID |
| --- | --- |
| ABC Australia | `now_hk.561` |
| Animax | `now_hk.150` |
| AXN | `now_hk.512` |
| BBC Earth | `now_hk.220` |
| BBC Lifestyle | `now_hk.502` |
| BBC News | `now_hk.320` |
| beIN SPORTS 1 | `now_hk.638` |
| beIN SPORTS 2 | `now_hk.639` |
| beIN SPORTS 3 | `now_hk.643` |
| beIN SPORTS 4 | `now_hk.644` |
| beIN SPORTS 5 | `now_hk.645` |
| beIN SPORTS 6 | `now_hk.646` |
| Bloomberg Television | `now_hk.321` |
| Cartoon Network | `now_hk.443` |
| CBeebies | `now_hk.447` |
| CCTV-1 | `now_hk.541` |
| CCTV-4 | `now_hk.542` |
| CINEMAX | `now_hk.113` |
| CNBC | `now_hk.319` |
| CNN 國際新聞網絡 | `now_hk.316` |
| COLORS | `now_hk.780` |
| Cricbuzz | `now_hk.674` |
| Discovery Asia | `now_hk.208` |
| Discovery Channel | `now_hk.209` |
| Discovery 科學頻道 | `now_hk.211` |
| DMAX | `now_hk.212` |
| DW (English) | `now_hk.324` |
| euronews | `now_hk.326` |
| Food Network | `now_hk.526` |
| France 24 | `now_hk.327` |
| France 24 (French) | `now_hk.715` |
| GMA Life TV | `now_hk.721` |
| GMA News TV | `now_hk.722` |
| GMA Pinoy TV | `now_hk.720` |
| HBO | `now_hk.115` |
| HBO Family | `now_hk.112` |
| HBO Hits | `now_hk.111` |
| HBO Signature | `now_hk.114` |
| HISTORY | `now_hk.223` |
| HITS | `now_hk.513` |
| HITS MOVIES | `now_hk.119` |
| KBS World | `now_hk.156` |
| Lifetime | `now_hk.525` |
| Love Nature | `now_hk.217` |
| Love Nature 4K | `now_hk.218` |
| Moonbug | `now_hk.448` |
| MOVIE MOVIE | `now_hk.116` |
| MTV India | `now_hk.779` |
| NBA TV | `now_hk.642` |
| NHK World Premium | `now_hk.711` |
| NHK WORLD-JAPAN | `now_hk.328` |
| Nick Jr. | `now_hk.449` |
| Nickelodeon | `now_hk.444` |
| Now Golf 2 | `now_hk.683` |
| Now Golf 3 | `now_hk.684` |
| Now Sports 1 | `now_hk.631` |
| Now Sports 2 | `now_hk.632` |
| Now Sports 3 | `now_hk.633` |
| Now Sports 4 | `now_hk.634` |
| Now Sports 4K 1 | `now_hk.611` |
| Now Sports 4K 2 | `now_hk.612` |
| Now Sports 4K 3 | `now_hk.613` |
| Now Sports 5 | `now_hk.635` |
| Now Sports 6 | `now_hk.636` |
| Now Sports 641 | `now_hk.641` |
| Now Sports 647 | `now_hk.647` |
| Now Sports 651 | `now_hk.651` |
| Now Sports 652 | `now_hk.652` |
| Now Sports 7 | `now_hk.637` |
| Now Sports Plus | `now_hk.680` |
| Now Sports Premier League TV | `now_hk.620` |
| Now Sports 精選 | `now_hk.630` |
| Now Sports 英超1台 | `now_hk.621` |
| Now Sports 英超2台 | `now_hk.622` |
| Now Sports 英超3台 | `now_hk.623` |
| Now Sports 英超4台 | `now_hk.624` |
| Now Sports 英超5台 | `now_hk.625` |
| Now Sports 英超6台 | `now_hk.626` |
| Now Sports 英超7台 | `now_hk.627` |
| Now 爆谷台 | `now_hk.133` |
| Now668 | `now_hk.668` |
| NowJelli | `now_hk.108` |
| Now報價台 | `now_hk.336` |
| Now新聞台 | `now_hk.332` |
| Now爆谷星影台 | `now_hk.138` |
| Now直播台 | `now_hk.331` |
| Now華劇台 | `now_hk.105` |
| Now財經台 | `now_hk.333` |
| Premier Sports | `now_hk.679` |
| ROCK Entertainment | `now_hk.517` |
| RT | `now_hk.329` |
| Sky News | `now_hk.323` |
| Sony MAX | `now_hk.772` |
| Sony SAB | `now_hk.774` |
| Sony TV (India) | `now_hk.771` |
| Star Bharat | `now_hk.797` |
| Star Gold | `now_hk.793` |
| STAR PLUS | `now_hk.794` |
| TFC | `now_hk.725` |
| TLC旅遊生活頻道 | `now_hk.213` |
| TV5MONDE ASIE | `now_hk.714` |
| TV5MONDE Style | `now_hk.713` |
| tvN | `now_hk.155` |
| Viu 頻道 | `now_hk.102` |
| Zee Cinema International | `now_hk.781` |
| Zee News | `now_hk.785` |
| Zee TV | `now_hk.782` |
| 三沙衛視 | `now_hk.553` |
| 中國環球電視網 | `now_hk.330` |
| 中天亞洲台 | `now_hk.538` |
| 中央電視台新聞頻道 | `now_hk.545` |
| 亞洲新聞台 | `now_hk.322` |
| 亞洲美食台 | `now_hk.527` |
| 動物星球頻道 | `now_hk.210` |
| 半島電視台英語頻道 | `now_hk.325` |
| 大灣區衛視 | `now_hk.543` |
| 戶外頻道 | `now_hk.221` |
| 曼聯電視頻道 | `now_hk.640` |
| 東方衛視國際頻道 | `now_hk.551` |
| 深圳衛視 | `now_hk.540` |
| 熊貓 TV | `now_hk.200` |
| 罪案 + 偵緝 | `now_hk.222` |
| 鳳凰衛視中文台 | `now_hk.548` |
| 鳳凰衛視資訊台 | `now_hk.366` |

### 马来西亚

#### Astro

| 频道官方名称 | XMLTV ID |
| --- | --- |
| 8TV | `astro.148` |
| ABC Australia HD | `astro.518` |
| Adithya | `astro.214` |
| AI FM | `astro.874` |
| Al Jazeera English HD | `astro.513` |
| Al-Hijrah | `astro.114` |
| Aniplus | `astro.120` |
| Arena Bola | `astro.803` |
| Arena Bola 2 | `astro.804` |
| Asian Food Network HD | `astro.709` |
| Astro AEC | `astro.306` |
| Astro AOD | `astro.311` |
| Astro Arena | `astro.801` |
| Astro Aura | `astro.113` |
| Astro Awani HD | `astro.501` |
| Astro Badminton | `astro.815` |
| Astro Boo | `astro.404` |
| Astro Ceria | `astro.611` |
| Astro Citra | `astro.108` |
| Astro Daebak | `astro.393` |
| Astro FAM Time | `astro.412` |
| Astro First HD | `astro.472` |
| Astro First HD | `astro.473` |
| Astro First HD | `astro.474` |
| Astro First HD | `astro.475` |
| Astro First HD | `astro.476` |
| Astro First HD | `astro.477` |
| Astro First HD | `astro.478` |
| Astro First HD | `astro.479` |
| Astro First HD | `astro.482` |
| Astro First HD | `astro.483` |
| Astro First HD | `astro.484` |
| Astro First HD | `astro.485` |
| Astro First HD | `astro.486` |
| Astro First HD | `astro.487` |
| Astro First HD | `astro.488` |
| Astro First HD | `astro.489` |
| Astro Football | `astro.814` |
| Astro Golf | `astro.831` |
| Astro Grandstand | `astro.810` |
| Astro Hua Hee Dai | `astro.333` |
| Astro Oasis | `astro.106` |
| Astro Premier League | `astro.811` |
| Astro Premier League 2 | `astro.812` |
| Astro Premier League 3 | `astro.813` |
| Astro Prima | `astro.105` |
| Astro QJ | `astro.308` |
| Astro Rania | `astro.112` |
| Astro Ria | `astro.104` |
| Astro Showcase | `astro.413` |
| Astro Showtime | `astro.411` |
| Astro Sports Plus | `astro.817` |
| Astro Sports Plus 2 | `astro.818` |
| Astro Sports UHD 805 | `astro.805` |
| Astro Tennis | `astro.819` |
| Astro Thangathirai | `astro.241` |
| Astro Tutor TV | `astro.603` |
| Astro Vaanavil | `astro.201` |
| Astro Vellithirai HD | `astro.203` |
| Astro Vinmeen | `astro.202` |
| Astro30 | `astro.100` |
| ASYIK FM | `astro.875` |
| AXN HD | `astro.701` |
| BAYU | `astro.867` |
| BBC Earth | `astro.554` |
| BBC News HD | `astro.512` |
| beIN SPORTS 1 | `astro.820` |
| beIN SPORTS 2 | `astro.821` |
| beIN SPORTS 3 | `astro.822` |
| Berita RTM | `astro.505` |
| Bernama TV | `astro.502` |
| Blippi & Friends | `astro.619` |
| Bloomberg TV HD | `astro.517` |
| Cartoon Network HD | `astro.615` |
| CCTV4 HD | `astro.335` |
| Celestial Classic Movies | `astro.321` |
| Celestial Movies HD | `astro.309` |
| CGTN Documentary | `astro.556` |
| CGTN HD | `astro.503` |
| CLASSIC ROCK | `astro.860` |
| CNA HD | `astro.515` |
| CNBC Asia HD | `astro.516` |
| CNN HD | `astro.511` |
| Colors Hindi HD | `astro.116` |
| Colors Tamil HD | `astro.222` |
| CricBuzz | `astro.832` |
| Crime & Investigation HD | `astro.714` |
| CTI Asia HD | `astro.316` |
| Discovery Asia HD | `astro.553` |
| Discovery Channel HD | `astro.552` |
| DW English | `astro.521` |
| ERA FM | `astro.856` |
| France24 | `astro.522` |
| GOLD | `astro.861` |
| GOXUAN | `astro.877` |
| HGTV HD | `astro.715` |
| History HD | `astro.555` |
| HITS HD | `astro.706` |
| HITS MOVIES HD | `astro.401` |
| HITS NOW | `astro.702` |
| HITZ FM | `astro.852` |
| INDIA BEAT | `astro.864` |
| iQIYI HD | `astro.300` |
| JAZZ | `astro.865` |
| K-Plus HD | `astro.396` |
| KBS World HD | `astro.392` |
| KENYALANG | `astro.868` |
| KTV | `astro.216` |
| Lifetime HD | `astro.703` |
| LITE FM | `astro.854` |
| Love Nature | `astro.550` |
| Love Nature 4K | `astro.549` |
| MELODY FM | `astro.858` |
| MINNAL FM | `astro.873` |
| MIX FM | `astro.855` |
| Moonbug | `astro.618` |
| MY FM | `astro.853` |
| NAS FM | `astro.869` |
| NHK World Premium | `astro.398` |
| Nick Jr. | `astro.617` |
| Nickelodeon HD | `astro.616` |
| NTV7 | `astro.147` |
| OPUS | `astro.862` |
| OSAI | `astro.866` |
| Phoenix Chinese Channel HD | `astro.325` |
| Phoenix Info News HD | `astro.326` |
| Premier Sports | `astro.833` |
| Rock Action | `astro.414` |
| Rock X Stream | `astro.415` |
| SINAR FM | `astro.857` |
| Stadium Astro | `astro.802` |
| Star Vijay HD | `astro.221` |
| Sukan+ | `astro.806` |
| Sun Life | `astro.217` |
| Sun Music HD | `astro.212` |
| Sun News | `astro.215` |
| SUN TV HD | `astro.211` |
| THR GEGAR | `astro.863` |
| THR RAAGA | `astro.859` |
| TLC HD | `astro.707` |
| TRAXX FM | `astro.872` |
| TV Okey HD | `astro.146` |
| TV Sarawak | `astro.122` |
| TV1 HD | `astro.101` |
| TV2 HD | `astro.102` |
| TV3 | `astro.103` |
| TV9 | `astro.149` |
| TVB Classic HD | `astro.305` |
| TVB Entertainment News HD | `astro.317` |
| TVB Jade | `astro.310` |
| TVB Xing He HD | `astro.319` |
| TVBS Asia HD | `astro.320` |
| tvN HD | `astro.395` |
| tvN Movies HD | `astro.416` |
| V FM | `astro.870` |
| W-Sport | `astro.826` |
| WAI FM | `astro.871` |
| Z Cinema HD | `astro.117` |
| Z Tamil HD | `astro.223` |
| ZAYAN | `astro.876` |

## 3. 官方节目表网站与正常页面数据接口

| 市场 | 服务商 | 官方节目表页面 | 正常页面数据接口或页面数据 |
| --- | --- | --- | --- |
| 马来西亚 | Astro | [Astro Content Guide](https://www.astro.com.my/content/channels) | `https://contenthub-api.eco.astro.com.my/api/v2/search-linear` |
| 香港 | NOW TV | [NOW TV Guide](https://nowplayer.now.com/tvguide?filterType=all) 与[官方中文频道目录](https://nowplayer.now.com/channels?lang=zh&filterType=all) | `https://nowplayer.now.com/tvguide/epglist` |
| 瑞典 | Allente | [Allente TV Guide](https://www.allente.se/tv-guide/) | `https://www.allente.se/api/epg/refetch-epg-data` |
| 挪威 | Allente Norway | [Allente Norway TV Guide](https://www.allente.no/tv-guide/) | `https://www.allente.no/api/epg/refetch-epg-data` |
| 英国 | EE TV Player | [EE TV Player Live TV Schedule](https://player.ee.co.uk/#/livetv/schedule) | `https://api.youview.tv/metadata/linear/v2/schedule/by-servicelocator` |
| 英国 | Virgin Media TV Go | [Virgin Media TV Go Guide](https://virgintvgo.virginmedia.com/en/epg/initial) | `https://spark-prod-gb.gnp.cloud.virgintvgo.virginmedia.com/eng/web/linear-service/v2/channels`；`https://staticqbr-prod-gb.gnp.cloud.virgintvgo.virginmedia.com/eng/web/epg-service-lite/gb/en/events/segments/{segment}` |
| 罗马尼亚 | Digi 4K | [Digi 4K](https://www.digi4k.ro/) | 官方页面内嵌的公开节目表数据 |
| 土耳其 | TV+ | [Eurosport 1](https://tvplus.com.tr/canli-tv/yayin-akisi/eurosport-1-hd--77) 与 [Eurosport 2](https://tvplus.com.tr/canli-tv/yayin-akisi/eurosport-2-hd--106) | 每个官方频道页内嵌的公开 SSR `playbills` 数据 |
