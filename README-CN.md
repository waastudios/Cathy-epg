# Cathy-epg

## 项目说明

**Cathy-epg** 是仅从节目运营商官网或授权电视服务商的正常公开节目表生成的 XMLTV 节目元数据订阅。项目不使用 EPGshare、epg.pw、IPTV 播放列表、第三方节目表镜像、播放地址、账号、会话重放、地域绕过或任何访问控制规避方法。

> 本仓库只发布频道和节目元数据；不发布播放链接、凭据、Cookie，也不会为了填充清单而创建空频道。

英文说明见 [README.md](README.md)。本次范围更新后，**实际已发布**的频道显示名和 XMLTV ID 由当前快照自动生成在 [CHANNELS.md](CHANNELS.md)，不是手工猜测的静态列表。

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

XMLTV 中的每个 `display-name` 都是服务商公开的官方频道名称。稳定 ID 通常采用 `<provider>.<channel-id>`；Sky Documentaries 使用用户指定的稳定 ID `ee_uk.352`。

## 当前覆盖与强制范围

| 市场 | 已发布服务 | 官方来源 |
| --- | --- | --- |
| 马来西亚 | Astro：22 条明确白名单体育频道 | [Astro Content Guide](https://www.astro.com.my/content/channels) |
| 香港 | now TV：37 条明确白名单体育频道 | [now TV Guide](https://nowplayer.now.com/tvguide) 与 [官方中文频道目录](https://nowplayer.now.com/channels?lang=zh&filterType=all) |
| 瑞典 | 13 条 V Sport 服务，包含 V Sport UltraHD | [Allente TV Guide](https://www.allente.se/tv-guide/) |
| 挪威 | TV Norge、REX、FEM、Eurosport Norge | [Allente Norway TV Guide](https://www.allente.no/tv-guide/) |
| 英国 | 指定 Sky Sports、TNT Sports、BBC、ITV、Channel 4 与 Sky 娱乐频道 | [EE TV Player Live TV Schedule](https://player.ee.co.uk/#/livetv/schedule) |
| 英国 | Sky Sports Ultra HD 1、Sky Sports Ultra HD 2 | [Virgin Media TV Go Guide](https://virgintvgo.virginmedia.com/en/epg/initial) |
| 罗马尼亚 | Digi 4K | [Digi 4K](https://www.digi4k.ro/) |
| 土耳其 | Eurosport 1、Eurosport 2 | [TV+ Eurosport 1](https://tvplus.com.tr/canli-tv/yayin-akisi/eurosport-1-hd--77) 与 [Eurosport 2](https://tvplus.com.tr/canli-tv/yayin-akisi/eurosport-2-hd--106) |
| 塞尔维亚 | Eurosport 4K IPTV | [SBB / EON Public EPG](https://epg.sbb.rs/) |

### EE Sky 娱乐频道选择

EE 范围包含 **Sky Mix、Sky Arts、Sky Witness、Sky Atlantic、Sky One、Sky Comedy、Sky Sci-Fi、Sky Crime、Sky Documentaries、Sky History 与 Sky Nature**。若 EE 提供多个版本，Sky Mix 与 Sky Arts 优先选择 DVB／电视版；其余频道使用标准清晰度主服务。HD、+1、辅助服务和其他镜像均不会发布。精确 ID 和显示名见 [CHANNELS.md](CHANNELS.md)。

### ESPN 状态

美国范围刻意限制为未来可能加入的 **ESPN、ESPN2、ESPNEWS、ESPNU**。ABC、CBS、NBC、FOX、USA Network 和其他所有美国频道都已排除。DIRECTV 公开指南确认四个 ESPN 频道，但只提供当前节目；Spectrum 的详细节目表需要账户与服务地址；ESPN 官网排期没有稳定的逐频道结束时间。因此，**当前不发布任何 ESPN 记录**。如日后出现合规节目表，ID 会使用服务商前缀，例如 `directv_espn`。

**Eurosport 4K IPTV** 已通过 SBB 的正常匿名 Public EPG 发布，XMLTV ID 为 `sbb_rs.1082`。该来源提供频道目录、节目标题、开始时间和结束时间。每条原始塞尔维亚语标题均通过严格的确定性规则转换成英文；如果标题无法被可靠识别，SBB 来源会失败，而不是猜测翻译或发布未翻译标题。官方显示名称保持为 `Eurosport 4K IPTV`。

## 自动刷新与校验

`.github/workflows/refresh-epg.yml` 中的 GitHub Actions 工作流每天在 **19:00 UTC** 运行，即北京时间（UTC+8）**次日 03:00**。工作流运行 `epg collect --days 7`，写入节目快照和 XMLTV 文件，并且只在结果变化时提交。若官网暂时无法访问，`data/status.json` 会记录来源失败，绝不使用第三方数据替代。

当前发布只有在以下条件同时满足时才视为有效：`data/epg.xml.gz` 解压后与 `data/epg.xml` 完全一致；所有 XMLTV 频道显示名为官方频道名；Astro 与 now TV 频道都属于明确体育白名单；被禁止的美国服务商 ID 不存在。

## 本地使用

需要 Python 3.11 或更高版本。

```bash
python -m pip install -e .
epg collect --days 7
epg search "Premier League" --provider now_hk --channel 611
```

## 参考资料

[1]: https://ee.co.uk/help/tv-sport/ee-tv-channel-guide "EE TV Channel Guide"
[2]: https://player.ee.co.uk/#/livetv/schedule "EE TV Player — Live TV Schedule"
[3]: https://www.astro.com.my/content/channels "Astro Content Guide"
[4]: https://nowplayer.now.com/tvguide "now TV Hong Kong — TV Guide"
[5]: https://virgintvgo.virginmedia.com/en/epg/initial "Virgin Media TV Go — Guide"
