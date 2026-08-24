# Cathy-epg

**Cathy-epg** 是一个仅从节目运营商官网或官方电视提供商页面收集节目元数据的 XMLTV 工具。它不读取 EPGshare、epg.pw、IPTV 播放列表、第三方节目表镜像或未经授权的数据接口。

> 仓库只保存频道与节目元数据快照，不包含视频流、播放地址、账号信息、会话 Cookie 或规避访问控制的代码。

## 覆盖来源与边界

| 市场 | 频道或服务 | 官方来源 | 当前覆盖 | 语言 |
| --- | --- | --- | --- | --- |
| 马来西亚 | Astro | [Astro Content Guide](https://www.astro.com.my/content/channels) | 完整七日线性节目表 | 来源原文 |
| 香港 | NOW TV | [NOW TV Guide](https://nowplayer.now.com/tvguide) 与[中文频道页](https://nowplayer.now.com/channels?lang=zh&filterType=all) | 完整七日线性节目表；显示名取官方中文名 | 中文为主 |
| 瑞典 | V sport ultra HD | [Allente TV Guide](https://www.allente.se/tv-guide/) | 单频道完整七日节目表 | 来源原文 |
| 英国 | NOW Sports 可观看的 Sky Sports 活动 | [Sky Sports live schedule](https://www.sky.com/watch/channel/sky-sports) | Sky 官方公开直播活动、开播时间与频道；并非英国 NOW 全频道的全天 EPG | 英文 |
| 罗马尼亚 | Digi 4K | [Digi 4K](https://www.digi4k.ro/) | 官网公开的连续七日节目表 | 罗马尼亚语 |
| 土耳其 | Eurosport 1、Eurosport 2 | [TV+ Eurosport 1](https://tvplus.com.tr/canli-tv/yayin-akisi/eurosport-1-hd--77) 与 [TV+ Eurosport 2](https://tvplus.com.tr/canli-tv/yayin-akisi/eurosport-2-hd--106) | TV+ 官方页公开的完整当日节目表 | 土耳其语 |

HBO Max 土耳其英文页明确说明 Eurosport 1 与 Eurosport 2 及直播活动在当地方案中提供；该页并不公开逐频道时刻表，因此实际节目条目使用其官方电视提供商 TV+ 的公开节目页，而不是第三方聚合数据。[1]

英国 NOW TV 的官方网站不公开全量线性频道的七日 XMLTV 时刻表。为维持“只用官方来源”的边界，项目仅纳入 Sky 官方页面明确列出的、NOW Sports 所覆盖的 Sky Sports 直播活动；官方页面未给出结束时间时，XMLTV 中会省略 `stop` 属性，而不会推断时长。

## XMLTV 文件与订阅

| 文件 | 说明 |
| --- | --- |
| `data/epg.xml.gz` | 可直接订阅的 gzip 压缩 XMLTV 文件。 |
| `data/epg.xml` | 未压缩 XMLTV 文件，便于审计与调试。 |
| `data/current_week.jsonl` | 标准化原始快照，每行一条节目记录。 |
| `data/status.json` | 本次刷新中每个来源的状态、记录数与总量。 |

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
```

节目排期会临时变更；建议每日执行一次刷新，以维持“当天起未来七天”的滚动窗口。每日运行前应复核相关网站条款、控制访问频率，并在来源不可用时查看 `data/status.json`，而非使用第三方替代数据。

## 参考资料

[1]: https://www.hbomax.com/tr/en "HBO Max Türkiye — English site"
[2]: https://content.astro.com.my/channels "Astro Content Guide — Channel guide"
[3]: https://nowplayer.now.com/tvguide "NOW TV Hong Kong — TV Guide"
[4]: https://www.allente.se/tv-guide/ "Allente — TV Guide"
[5]: https://www.sky.com/watch/channel/sky-sports "Sky Sports — Live schedule"
[6]: https://www.digi4k.ro/ "Digi 4K România"
[7]: https://tvplus.com.tr/canli-tv/yayin-akisi/eurosport-1-hd--77 "TV+ — Eurosport 1 schedule"
[8]: https://tvplus.com.tr/canli-tv/yayin-akisi/eurosport-2-hd--106 "TV+ — Eurosport 2 schedule"
