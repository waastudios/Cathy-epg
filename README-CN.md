# Cathy-epg

## 项目说明

**Cathy-epg** 是仅从节目运营商官网或授权电视服务商的正常公开节目表生成的 XMLTV 节目元数据订阅。项目不使用 EPGshare、epg.pw、IPTV 播放列表、第三方节目表镜像、播放地址、账号、会话重放、地域绕过或任何访问控制规避方法。

> 本仓库只发布频道和节目元数据；不发布播放链接、凭据、Cookie，也不会为了填充清单而创建空频道。

英文说明见 [README.md](README.md)。本次范围更新后，**实际已发布**的频道显示名和 XMLTV ID 由当前快照自动生成在 [CHANNELS.md](CHANNELS.md)，不是手工猜测的静态列表。

Telegram 群组：https://t.me/garysclub

## 订阅地址与数据文件

订阅地址保持不变：

```text
https://raw.githubusercontent.com/waastudios/Cathy-epg/master/data/epg.xml.gz
```

| 文件 | 用途 |
| --- | --- |
| `data/epg.xml.gz` | 可订阅的 gzip 压缩 XMLTV 文件。 |
| `data/epg.xml` | 未压缩 XMLTV 文件，便于审计。 |
| `data/current_week.jsonl` | 当前规范化节目快照。 |
| `data/status.json` | 每个来源的采集状态和输出总量。 |
| `CHANNELS.md` | 由当前发布快照生成的显示名与 XMLTV ID 对照表。 |

除经用户明确指定的名称规范化外，XMLTV 中的每个 `display-name` 都是服务商公开的官方频道名称。德国 Sky 会移除频道显示名末尾的 `HD` 并保留 `UHD`；[CHANNELS.md](CHANNELS.md) 频道清单会在其名称后追加“（T）”以标记节目标题固定译为英文，但 XMLTV `display-name` 仍保留服务商官方名称。稳定 ID 通常采用 `<provider>.<channel-id>`；Sky Documentaries 使用用户指定的稳定 ID `ee_uk.352`，德国 Sky 使用 Sky 频道号作为 `sky_de.<频道号>`。

## 当前覆盖与强制范围

| 市场 | 已发布服务 | 官方来源 |
| --- | --- | --- |
| 马来西亚 | Astro：23 条明确白名单体育频道 | [Astro Content Guide](https://www.astro.com.my/content/channels) |
| 香港 | now TV：37 条明确白名单体育频道 | [now TV Guide](https://nowplayer.now.com/tvguide) 与 [官方中文频道目录](https://nowplayer.now.com/channels?lang=zh&filterType=all) |
| 德国 | 29 条 Sky Sport 与 Sky Sport Bundesliga 频道，包含 UHD | [Telekom MagentaTV](https://www.magenta.tv/) 正常公开节目表 |
| 瑞典 | 13 条 V Sport 服务，包含 V Sport UltraHD | [Allente TV Guide](https://www.allente.se/tv-guide/) |
| 挪威 | TV Norge、REX、FEM、Eurosport Norge、Eurosport 1 | [Allente Norway TV Guide](https://www.allente.no/tv-guide/) |
| 英国 | 指定 Sky Sports、TNT Sports、BBC、ITV、Channel 4 与 Sky 娱乐频道 | [EE TV Player Live TV Schedule](https://player.ee.co.uk/#/livetv/schedule) |
| 英国 | Sky Sports Ultra HD 1、Sky Sports Ultra HD 2 | [Virgin Media TV Go Guide](https://virgintvgo.virginmedia.com/en/epg/initial) |
| 罗马尼亚 | Digi 4K | [Digi 4K](https://www.digi4k.ro/) |
| 塞尔维亚 | Eurosport 1、Eurosport 2 与 Eurosport 4K | [SBB / EON 公开 EPG](https://epg.sbb.rs/) |
| 波兰 | Eurosport 1–4 与 Eleven Sports 1（标题已译为英文） | [Player.pl](https://player.pl/) 公开 EPG 接口 |
| 法国 | CANAL+ 主频道与 CANAL+ FOOT（标题已译为英文） | [Canal+ 官方 EPG 接口](https://www.canalplus.com/programme-tv/) |
| 加拿大 | 爱自然（Love Nature）、Travelxp 4K 与 TSN 1–5 | [TELUS TV+ 节目指南](https://telustvplus.com/#/guide) |
| 美国 | Tennis Channel 2 与 Telemundo Deportes Ahora | [Peacock 频道指南](https://www.peacocktv.com/channels/tennis-channel-2/8969135442586836117)、[Telemundo Deportes Ahora](https://www.peacocktv.com/channels/telemundo-deportes-ahora/5923023667697108117) |
| 美国 | CBS Sports Golazo Network | [Pluto TV 指南](https://pluto.tv/us/live-tv/golazo-network) |
| 美国 | NBC Sports 湾区、波士顿、费城与加州 | [EPGShare 美国节目文件](https://epgshare01.online/epgshare01/epg_ripper_US2.xml.gz) |
| 美国 | Telemundo 51（迈阿密）与 NBC 4 纽约 | [EPGShare 美国地方台节目文件](https://epgshare01.online/epgshare01/epg_ripper_US_LOCALS1.xml.gz) |

### 德国 Sky 与 MagentaTV

德国范围仅包括 MagentaTV 正常公开的生产节目表当前暴露的 29 条 Sky Sport 与 Sky Sport Bundesliga 服务。采集器每次刷新都会动态读取 MagentaTV 的官方频道目录，要求所有映射频道均返回节目记录，并按用户指定的 Sky 频道号导出 `sky_de.201` 至 `sky_de.230`（频道 208 不发布）。德语节目标题统一通过下文的分级流水线翻译为英文；无法翻译的标题只会跳过当条节目，不会导致整个 Sky 来源失败。当前公开目录没有可无歧义映射的一组 Sky Austria 频道，因此不会发布 Sky Austria。

### EE Sky 娱乐频道选择

EE 范围包含 **Sky Mix、Sky Arts、Sky Witness、Sky Atlantic、Sky One、Sky Comedy、Sky Sci-Fi、Sky Crime、Sky Documentaries、Sky History 与 Sky Nature**。若 EE 提供多个版本，Sky Mix 与 Sky Arts 优先选择 DVB／电视版；其余频道使用标准清晰度主服务。HD、+1、辅助服务和其他镜像均不会发布。精确 ID 和显示名见 [CHANNELS.md](CHANNELS.md)。

### ESPN 状态

**ESPN、ESPN2、ESPNEWS、ESPNU** 仍在评估未来可能加入。ABC、CBS、NBC、FOX、USA Network 和其他所有美国广播频道都已排除。DIRECTV 公开指南确认四个 ESPN 频道，但只提供当前节目；Spectrum 的详细节目表需要账户与服务地址；ESPN 官网排期没有稳定的逐频道结束时间。因此，**当前不发布任何 ESPN 记录**。如日后出现合规节目表，ID 会使用服务商前缀，例如 `directv_espn`。下文介绍实际发布的美国流媒体来源（Peacock）。

**Eurosport 1、Eurosport 2 和 Eurosport 4K** 均通过塞尔维亚 SBB 的正常匿名 Public EPG 发布，XMLTV ID 分别为 `eurosport.1`、`eurosport.2` 和 `eurosport.4k`。该来源提供频道目录、节目标题、开始时间和结束时间。每条原始塞尔维亚语标题均通过下文的分级流水线转换成英文；无法翻译的标题只会跳过当条节目，不会导致整个 SBB 来源失败。

**爱自然（Love Nature）**、**Travelxp 4K** 与 **TSN 1–5** 通过加拿大 TELUS TV+（Optik TV）官方网页指南发布，XMLTV ID 分别为 `telus.713`、`telus.716` 与 `telus.900`–`telus.904`。指南的公开 AVS 接口可匿名查询（优先生产环境，失败回退 QA 环境）；按官方频道名匹配频道，绝不使用 TSN 的地区黑屏（Blackout）变体。节目标题本身为英文，直接发布。

**Tennis Channel 2** 通过 Peacock 官方 BFF 频道指南发布，XMLTV ID 为 `TC2.us`。该指南携带 Peacock 自家客户端使用的 Sky OTT 平台请求头即可匿名查询，无需账号。接口的起始时间只能在过去 1 天至未来 2 天之间、单次返回约 30 小时，采集器以四个错开的窗口拼接（约 4 天滚动覆盖），而非一次拉满 7 天。节目标题本身为英文，直接发布。

**Telemundo Deportes Ahora** 通过同一个 Peacock BFF 频道指南发布，XMLTV ID 为 `TDA.us`，与 Tennis Channel 2 在同一次匿名采集内完成。每条原始西班牙语标题均通过下文的分级流水线转换成英文（西语体育节目名精确映射 → 翻译记忆 → 在线服务）；无法翻译的标题只会跳过当条节目，不会导致整个 Peacock 来源失败。在 [CHANNELS-CN.md](CHANNELS-CN.md) 中该频道带有（T）标记，表示节目单已翻译为英文。

**CBS Sports Golazo Network** 通过 Pluto TV 官方指南接口发布，XMLTV ID 为 `GolazoNet.us`。Pluto TV 是 Paramount 自家的免费流媒体平台，该频道在其阵容中名为 “Golazo Network”；指南接口可匿名查询，按 24 小时分窗拉取。（Paramount+ 自家的 apps-api 指南无法使用：匿名请求会被拒绝。）Pluto 对该频道只提前约 1–2 天发布逐节目明细，更远的日期只有其官方发布的整段 “Golazo Network” 占位块，如实收录。节目标题本身为英文，直接发布。

**NBC Sports 湾区（Bay Area）、波士顿（Boston）、费城（Philadelphia）与加州（California）** 以 `NBCSpBay.us`、`NBCSpBos.us`、`NBCSpPhilly.us`、`NBCSpCali.us` 发布。这四个台在 Peacock 上为付费附加包，其官方指南不对匿名查询开放（已逐一核查官方指南接口、官网与站点地图），因此作为本项目官方源原则的一项明确例外，其节目单改用 EPGShare 的 US2 XMLTV 文件；该文件每日更新、约 4 天滚动覆盖。每台取主 feed（HD feed；加州在该文件中无 HD feed，取 SAT feed），不取 Outer Market 黑屏变体与 Plus 溢出频道。节目标题本身为英文，直接发布。

**Telemundo 51（迈阿密）与 NBC 4 纽约（New York）** 以 `WSCV.us` 与 `WNBC.us` 发布。两台均为地方台，不在 Peacock 匿名官方指南内（该指南只含全国性线性频道），因此与 NBC Sports 四台同样作为本项目官方源原则的一项明确例外，其节目单改用 EPGShare 的 US_LOCALS1 XMLTV 文件；该文件每日更新、约 4 天滚动覆盖。Telemundo 51 的西班牙语标题按分级流水线译为英文发布（无法翻译的标题只跳过当条节目），在 [CHANNELS-CN.md](CHANNELS-CN.md) 中带（T）标记；NBC 4 纽约的标题本身为英文，直接发布。

### 波兰 Player.pl

**Eurosport 1、Eurosport 2、Eurosport 3、Eurosport 4 与 Eleven Sports 1** 均通过波兰 TVN Player.pl 的匿名公开 EPG 接口发布。用户指定的 XMLTV ID 为 `eurosport1.pl`、`eurosport2.pl`、`eurosport3.pl`、`eurosport4.pl` 与 `ElevenSp.1`。每条原始波兰语标题均通过下文的分级流水线转换成英文（波兰语体育术语精确映射 → 翻译记忆 → 在线服务）；无法翻译的标题只会跳过当条节目，不会导致整个 Player.pl 来源失败。在 [CHANNELS-CN.md](CHANNELS-CN.md) 中这五个频道带有（T）标记，表示节目单已翻译为英文。

### 法国 Canal+ 官方接口

**CANAL+**（主频道）与 **CANAL+ FOOT** 均通过 Canal+ 官方 EPG 接口发布，XMLTV ID 为 `canal+.fr` 与 `foot+.fr`。每次采集先经认证接口换取新鲜 token（硬编码 token 会被拒绝）；官方接口频率限制极严，请求间隔 90 秒并带重试。每条原始法语标题均通过下文的分级流水线转换成英文（法语精确映射 → 翻译记忆 → 在线服务）；无法翻译的标题只会跳过当条节目，不会导致整个来源失败。仅使用官方接口，无第三方兜底。在 [CHANNELS-CN.md](CHANNELS-CN.md) 中这两个频道带有（T）标记，表示节目单已翻译为英文。

### 英文翻译

非英语市场（瑞典语、挪威语、德语、罗马尼亚语、塞尔维亚语、波兰语、法语、西班牙语）的节目标题均以英文发布；香港 now TV 的中文标题保持原样。翻译在各采集器内部按三级流水线进行：

1. **版本控制的精确映射**（`src/epg_tool/sources.py`）——按来源维护的确定性规则。
2. **持久翻译记忆**（`src/epg_tool/translation_cache.json`）——每次在线翻译的结果都会记录在此，稳定、可审计，无需重复请求网络。每日工作流会提交该文件，记忆随时间增长。
3. **在线翻译服务**（先 Google，后 MyMemory）——处理前两级未覆盖的标题。

三级都无法翻译的标题只会跳过当条节目（记入 `data/status.json` 中该来源的 `notes`），不会让整个来源失败；单个新标题永远不会清空某个频道的节目表。

## 自动刷新与校验

`.github/workflows/refresh-epg.yml` 中的 GitHub Actions 工作流每天在 **19:00 UTC** 运行，即北京时间（UTC+8）**次日 03:00**。工作流会对**全部已配置的官方频道来源**运行 `epg collect --days 7`，写入完整节目快照和 XMLTV 文件（`data/epg.xml` 与 `data/epg.xml.gz`），并且只在结果变化时提交。若官网暂时无法访问，`data/status.json` 会记录来源失败，绝不使用第三方数据替代。

当前发布只有在以下条件同时满足时才视为有效：`data/epg.xml.gz` 解压后与 `data/epg.xml` 完全一致；所有 XMLTV 频道显示名为官方频道名；Astro 与 now TV 频道都属于明确体育白名单；被禁止的美国服务商 ID 不存在。

## 本地使用

需要 Python 3.11 或更高版本。

```bash
python -m pip install -e .
epg collect --days 7
epg search "Premier League" --provider now_hk --channel 611
```

### 三天节目预告

已发布快照保留最多七天的官方节目数据。`preview` 命令默认以北京时间输出**今天、明天和后天**的节目；使用 `--day` 可只查看其中一天，并可配合常规服务商／频道筛选缩小结果。

```bash
epg preview
epg preview --day tomorrow --provider allente_se --channel 50048
```

对于塞尔维亚 SBB Eurosport 节目表，标题会在采集阶段通过本地固定的塞尔维亚语到英文映射和受控规则转换；每日刷新不会调用在线翻译服务，因此不会因翻译请求导致额外等待。

## 更新日志

- **2026-10-16** —— Astro 体育白名单新增 Astro Badminton 2（`astro.816`），共 23 条。该台是 Astro 为并行羽毛球直播开设的 ad hoc 频道；本次按官方目录核查，现有 22 条 Astro 体育频道无改名、无下线。
- **2026-10-17** —— 通过 EPGShare 的 US_LOCALS1 XMLTV 文件新增迈阿密 Telemundo 51（`WSCV.us`）与纽约 NBC 4（`WNBC.us`）。地方台不在 Peacock 匿名官方指南内，故这两台同样明确破例使用 EPGShare；约 4 天滚动覆盖。Telemundo 51 的西语标题按分级流水线译为英文发布；NBC 4 纽约的标题直接发布。

- **2026-10-16** —— 通过 EPGShare 的 US2 XMLTV 文件新增四个 NBC Sports 地区频道（`NBCSpBay.us`、`NBCSpBos.us`、`NBCSpPhilly.us`、`NBCSpCali.us`）。这四个台是 Peacock 付费附加包、官方指南无法匿名取得，故为这四个台明确破例使用 EPGShare；只取主 feed，约 4 天滚动覆盖。
- **2026-10-16** —— 修复 Travelxp 4K（`telus.716`）节目为空的问题：TELUS TV+ 采集器改为按频道回退（不再是整表二选一环境）。该台在生产目录中始终匹配不到，生产环境一旦可用它便一直为空；现在生产缺失（或拉取失败）的频道由 QA 环境逐台补齐——QA 目录中该台为 “Travel XP 4K”（callLetter TXP4KHDR），7 天节目单完整。
- **2026-10-15** —— 通过 Peacock 官方 BFF 频道指南新增 Telemundo Deportes Ahora（`TDA.us`），可匿名查询，与 Tennis Channel 2 同一次采集完成。该频道节目标题为西班牙语，按分级流水线译为英文发布；无法翻译的标题只跳过当条节目。
- **2026-10-14** —— 通过 Pluto TV 官方指南接口新增 CBS Sports Golazo Network（`GolazoNet.us`），可匿名查询、按 24 小时分窗拉取。Pluto TV 是 Paramount 自家的免费流媒体平台（Paramount+ 自家的 apps-api 指南拒绝匿名请求，无法使用）。Pluto 对该频道只提前约 1–2 天发布逐节目明细，之后的日期为其官方发布的整段 “Golazo Network” 占位块。
- **2026-10-14** —— 通过 TELUS TV+ 官方指南新增 TSN 1–5（`telus.900`–`telus.904`）；频道按官方名匹配（忽略空格与大小写，这也让 Travelxp 4K 能兼容指南中的 "Travel XP 4K" 写法），并排除 TSN 的地区黑屏（Blackout）变体。通过 Peacock 官方 BFF 频道指南新增 Tennis Channel 2（`TC2.us`），可匿名查询；该接口为滚动窗口（起始时间限过去 1 天至未来 2 天、单次约 30 小时），采集器以四个错开的窗口拼接约 4 天覆盖。另修复频道清单生成器：加拿大分区此前不在排序表中，Telus 频道一直未显示在 CHANNELS 清单中。
- **2026-10-12** —— 新增加拿大覆盖：通过 TELUS TV+（Optik TV）官方网页指南的公开 AVS 接口发布爱自然（Love Nature，`telus.713`）与 Travelxp 4K（`telus.716`），可匿名查询（优先生产环境，失败回退 QA 环境）。标题本身为英文，直接发布。删除波兰 CANAL+ 4K ULTRA HD（`canal+4k.pl`）与 SBB 欧洲 Travel XP（`travelxp.eu`）；Telus 的 Travelxp 4K 接替 SBB 台。
- **2026-09-29** —— 恢复法国 Canal+ 双频道：通过 Canal+ 官方 EPG 接口发布，XMLTV ID 为 `canal+.fr`（CANAL+）与 `foot+.fr`（CANAL+ FOOT），各 7 天。每次采集先经认证接口换取新鲜 token（硬编码 token 会被拒绝）；官方接口频率限制极严，请求间隔 90 秒并带重试。法语标题经分级流水线译为英文，并在频道清单中以（T）标记。仅使用官方接口，无第三方兜底。
- **2026-09-28** —— 新增 Travel XP（欧洲台）：通过 SBB 公开 EPG 发布，XMLTV ID 为 `travelxp.eu`。标题本身为英文，直接发布，并在频道清单中以（T）标记。
- **2026-09-28** —— 新增波兰覆盖：通过 Player.pl 公开 EPG 接口发布 Eurosport 1–4 与 Eleven Sports 1，用户指定的 XMLTV ID 为 `eurosport1.pl`、`eurosport2.pl`、`eurosport3.pl`、`eurosport4.pl` 与 `ElevenSp.1`。波兰语标题经分级流水线译为英文，并在频道清单中以（T）标记。

## 参考资料

[1]: https://ee.co.uk/help/tv-sport/ee-tv-channel-guide "EE TV Channel Guide"
[2]: https://player.ee.co.uk/#/livetv/schedule "EE TV Player — Live TV Schedule"
[3]: https://www.astro.com.my/content/channels "Astro Content Guide"
[4]: https://nowplayer.now.com/tvguide "now TV Hong Kong — TV Guide"
[5]: https://virgintvgo.virginmedia.com/en/epg/initial "Virgin Media TV Go — Guide"
