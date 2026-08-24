# Cathy-epg

**Cathy-epg** 是一个仅从节目运营商官网或官方电视提供商页面收集节目元数据的 XMLTV 工具。它不读取 EPGshare、epg.pw、IPTV 播放列表、第三方节目表镜像或未经授权的数据接口。

> 仓库只保存频道与节目元数据快照，不包含视频流、播放地址、账号信息、会话 Cookie 或规避访问控制的代码。

## 覆盖来源与边界

| 市场 | 频道或服务 | 官方来源 | 当前覆盖 | 语言 |
| --- | --- | --- | --- | --- |
| 马来西亚 | Astro | [Astro Content Guide](https://www.astro.com.my/content/channels) | 完整七日线性节目表 | 来源原文 |
| 香港 | NOW TV | [NOW TV Guide](https://nowplayer.now.com/tvguide) 与[中文频道页](https://nowplayer.now.com/channels?lang=zh&filterType=all) | 完整七日线性节目表；显示名取官方中文名 | 中文为主 |
| 瑞典 | 完整 V Sport 体育频道组合 | [Allente TV Guide](https://www.allente.se/tv-guide/) | 13 条 V Sport 频道的完整七日节目表 | 来源原文 |
| 英国 | Sky Sports 与 TNT Sports 1–4 | [EE TV Player Live TV Schedule](https://player.ee.co.uk/#/livetv/schedule) | 16 条去重后的标准清晰度体育频道，提供完整七日频道级节目表、官方频道名与开始/结束时间 | 英文 |
| 罗马尼亚 | Digi 4K | [Digi 4K](https://www.digi4k.ro/) | 官网公开的连续七日节目表 | 罗马尼亚语 |
| 土耳其 | Eurosport 1、Eurosport 2 | [TV+ Eurosport 1](https://tvplus.com.tr/canli-tv/yayin-akisi/eurosport-1-hd--77) 与 [TV+ Eurosport 2](https://tvplus.com.tr/canli-tv/yayin-akisi/eurosport-2-hd--106) | TV+ 官方页公开的完整当日节目表 | 土耳其语 |

HBO Max 土耳其英文页明确说明 Eurosport 1 与 Eurosport 2 及直播活动在当地方案中提供；该页并不公开逐频道时刻表，因此实际节目条目使用其官方电视提供商 TV+ 的公开节目页，而不是第三方聚合数据。[1]

英国节目表改用 **EE TV Player 匿名公开显示的 Live TV Schedule**。覆盖 TNT Sports 1–4（EE 频道 408–411），以及 Sky Sports News、Main Event、Premier League、Football、Cricket、Golf、F1、Tennis、Action、+、Racing 和 Mix（418–429）。XMLTV 的显示名严格使用 EE Player 官方频道目录返回的名称；节目开始时间与时长来自该页面正常加载的公开节目表请求。[2]

为筛除同名实际频道，数据集对每条真实线性频道只保留一个标准清晰度 EE 条目。已明确排除对应的 HD 镜像（TNT 430–432/434，Sky 438–449）、旧的 NOW/Sky 活动型来源，以及 TNT Sports Ultimate、TNT Sports 5 和临时频道；不会把来自不同平台的同名行合并为重复条目。英国频道稳定使用 `ee_uk.<EE频道号>` 作为 XMLTV ID。

## XMLTV 文件与订阅

| 文件 | 说明 |
| --- | --- |
| `data/epg.xml.gz` | 可直接订阅的 gzip 压缩 XMLTV 文件。 |
| `data/epg.xml` | 未压缩 XMLTV 文件，便于审计与调试。 |
| `data/current_week.jsonl` | 标准化原始快照，每行一条节目记录。 |
| `data/status.json` | 本次刷新中每个来源的状态、记录数与总量。 |

瑞典集合包括 **V sport extra HD、premium HD、football HD、vinter HD、motor HD、V sport 1 HD、ultra HD、golf HD 与 V sport live 1–5**，保留 Allente 官方的稳定频道 ID。

订阅地址如下：

```text
https://raw.githubusercontent.com/waastudios/Cathy-epg/master/data/epg.xml.gz
```

频道标识稳定使用 `<provider>.<channel-id>`。例如，香港 NOW TV 的频道 ID **`now_hk.138`** 保持不变，显示名已由通用 `CH 138` 改为官网中文名 **`Now爆谷星影台`**。

## 本地运行

项目需要 Python 3.11 或更高版本。以下命令刷新可取得的官方节目表并写出 JSONL、XMLTV 和 gzip 文件。

```bash
python -m pip install -e .
epg collect --days 7
```

本地搜索只读取已生成的 JSONL 快照：

```bash
epg search "Premier League"
epg search "Now爆谷" --provider now_hk --channel 138
epg search "Eurosport" --provider tvplus_tr
epg search "TNT Sports" --provider ee_uk
```

节目排期会临时变更；建议每日执行一次刷新，以维持“当天起未来七天”的滚动窗口。每日运行前应复核相关网站条款、控制访问频率，并在来源不可用时查看 `data/status.json`，而非使用第三方替代数据。

## 参考资料

[1]: https://www.hbomax.com/tr/en "HBO Max Türkiye — English site"
[2]: https://player.ee.co.uk/#/livetv/schedule "EE TV Player — Live TV Schedule"
[3]: https://content.astro.com.my/channels "Astro Content Guide — Channel guide"
[4]: https://nowplayer.now.com/tvguide "NOW TV Hong Kong — TV Guide"
[5]: https://www.allente.se/tv-guide/ "Allente — TV Guide"
[6]: https://www.digi4k.ro/ "Digi 4K România"
[7]: https://tvplus.com.tr/canli-tv/yayin-akisi/eurosport-1-hd--77 "TV+ — Eurosport 1 schedule"
[8]: https://tvplus.com.tr/canli-tv/yayin-akisi/eurosport-2-hd--106 "TV+ — Eurosport 2 schedule"
