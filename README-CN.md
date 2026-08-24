# Cathy-epg

**Cathy-epg** 是一个仅从节目运营商官网或官方电视提供商页面收集节目元数据的 XMLTV 工具。它不读取 EPGshare、epg.pw、IPTV 播放列表、第三方节目表镜像或未经授权的数据接口。

> 仓库只保存频道与节目元数据快照，不包含视频流、播放地址、账号信息、会话 Cookie 或规避访问控制的代码。

## 覆盖来源与边界

| 市场 | 频道或服务 | 官方来源 | 当前覆盖 | 语言 |
| --- | --- | --- | --- | --- |
| 马来西亚 | Astro | [Astro Content Guide](https://www.astro.com.my/content/channels) | 完整七日线性节目表 | 来源原文 |
| 香港 | NOW TV | [NOW TV Guide](https://nowplayer.now.com/tvguide) 与[中文频道页](https://nowplayer.now.com/channels?lang=zh&filterType=all) | 完整七日线性节目表；显示名取官方中文名 | 中文为主 |
| 瑞典 | 完整 V Sport 体育频道组合 | [Allente TV Guide](https://www.allente.se/tv-guide/) | 13 条 V Sport 频道的完整七日节目表 | 来源原文 |
| 挪威 | TVNorge HD、REX HD、FEM HD、Eurosport Norge HD | [Allente Norway TV Guide](https://www.allente.no/tv-guide/) | 完整七日频道级节目表；排除字幕与音频描述镜像 | 挪威语／来源原文 |
| 英国 | Sky Sports、TNT Sports 1–4、BBC、ITV、Channel 4 与指定 Sky 娱乐频道 | [EE TV Player Live TV Schedule](https://player.ee.co.uk/#/livetv/schedule) | 31 条去重后的标准清晰度频道，提供完整七日频道级节目表、官方频道名与开始/结束时间 | 英文 |
| 英国 | Sky Sports Ultra HD 1、Sky Sports Ultra HD 2 | [Virgin Media TV Go Guide](https://virgintvgo.virginmedia.com/en/epg/initial) | Guide 正常加载的频道目录和 6 小时时间片提供完整七日节目表；排除隐藏的 Duplicate 镜像 | 英文 |
| 罗马尼亚 | Digi 4K | [Digi 4K](https://www.digi4k.ro/) | 官网公开的连续七日节目表 | 罗马尼亚语 |
| 土耳其 | Eurosport 1、Eurosport 2 | [TV+ Eurosport 1](https://tvplus.com.tr/canli-tv/yayin-akisi/eurosport-1-hd--77) 与 [TV+ Eurosport 2](https://tvplus.com.tr/canli-tv/yayin-akisi/eurosport-2-hd--106) | TV+ 官方页公开的完整当日节目表；每条标题均在写入 XMLTV 前进行贴合赛事语义的土耳其语转英文 | 英文 |

HBO Max 土耳其英文页明确说明 Eurosport 1 与 Eurosport 2 及直播活动在当地方案中提供；该页并不公开逐频道时刻表，因此实际节目条目使用其官方电视提供商 TV+ 的公开节目页，而不是第三方聚合数据。[1]

英国节目表使用 **EE TV Player 匿名公开显示的 Live TV Schedule**。覆盖 TNT Sports 1–4（EE 频道 408–411），Sky Sports News、Main Event、Premier League、Football、Cricket、Golf、F1、Tennis、Action、+、Racing 和 Mix（418–429）；BBC One London、BBC Two、BBC Three、BBC Four、BBC News、BBC Parliament；ITV1 London、ITV2、ITV3、ITV4、ITV Quiz；Channel 4；以及不含电影频道的 Sky Atlantic、Sky One、Sky Crime。XMLTV 的显示名严格使用 EE Player 官方频道目录返回的名称；节目开始时间与时长来自该页面正常加载的公开节目表请求。[2]

为筛除同名实际频道，数据集对每条真实线性频道只保留一个标准清晰度 EE 条目。已明确排除 HD 镜像、+1 服务、辅助服务镜像、旧的 NOW/Sky 活动型来源、Sky Cinema 等电影频道，以及 TNT Sports Ultimate、TNT Sports 5 和临时频道；不会把来自不同平台的同名行合并为重复条目。英国频道稳定使用 `ee_uk.<EE频道号>` 作为 XMLTV ID。

挪威来源使用匿名公开的 Allente Norway TV Guide，保留其标准频道官方名称 **TVNorge HD**、**REX HD**、**FEM HD** 和 **Eurosport Norge HD**，并排除与其并行的字幕及音频描述频道。[9]

Virgin Media 来源仅保留官方目录中可见、非 Duplicate 的两条 Ultra 频道：**Sky Sports Ultra HD 1**（内部 ID `2258`、逻辑频道 515）与 **Sky Sports Ultra HD 2**（内部 ID `2265`、逻辑频道 516）。对应 XMLTV ID 严格为 **`virgin_uk.2258`** 与 **`virgin_uk.2265`**；隐藏的 Duplicate 镜像 `2321`、`2322` 不会收录。[10]

TV+ Eurosport 每次采集均对每个官方标题执行确定性的英文赛事转换。转换仅处理标题中明确出现的运动、赛事、赛段等信息，保留官方赛事名称，绝不补写选手、比分或场地；若出现无法可靠转换的土耳其语标记，该来源会明确失败，而非静默发布未翻译标题。

若官网仅能确认频道存在、却没有可公开复用的频道级节目数据，项目不会创建空频道。目前美国范围仅限 **ESPN、ESPN2、ESPNEWS、ESPNU**。ABC、CBS、NBC、FOX、USA Network 与其他所有美国网络均明确排除，仓库不发布它们的频道或节目记录。ESPN 当前公开页面显示带频道标识的节目开始时间，但尚未确认稳定的频道级结束时间，因此暂未写入 XMLTV。该规则同样适用于 FS1/FS2、TBS/truTV、France 2–5、波兰 Eurosport 1–4 与 NHK 国内频道。Orange Romania TV Go 的正常 **Free User** Guide 已公开显示 Eurosport 4K 的精确节目时间，但按日节目请求绑定运营商动态签发的短期会话；自动刷新工作流不保存或重放会话凭据，因此尚未发布 Orange Eurosport 4K。NHK 国内频道的官方文字节目表还明确规定，节目数据除私人使用外须取得 NHK 许可；公开发布 XMLTV 不属于私人使用，故未收录 NHK G、E、BS、BSP4K、BS8K 的节目条目。

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

频道标识通常稳定使用 `<provider>.<channel-id>`。例如，香港 NOW TV 的频道 ID **`now_hk.138`** 保持不变，显示名已由通用 `CH 138` 改为官网中文名 **`Now爆谷星影台`**。Digi 4K 是用户指定的单频道例外：XMLTV 频道 ID 精确为 **`digi4k_ro`**，显示名保持官方名称 **Digi 4K**。Virgin Media Sky Sports Ultra 严格采用所要求的官方 ID 格式：**Sky Sports Ultra HD 1** 为 **`virgin_uk.2258`**，**Sky Sports Ultra HD 2** 为 **`virgin_uk.2265`**。

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
epg search "BBC" --provider ee_uk
epg search "Eurosport" --provider allente_no
epg search "Ultra" --provider virgin_uk
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
[9]: https://www.allente.no/tv-guide/ "Allente Norway — TV Guide"
[10]: https://virgintvgo.virginmedia.com/en/epg/initial "Virgin Media TV Go — Guide"
