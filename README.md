# Official EPG Search

这是一个**仅使用运营商官网**的一周节目表采集、XMLTV 导出与本地搜索工具。当前只保留 **Astro（马来西亚）** 与 **NOW TV（香港）** 两个官方来源；它不会读取 EPGshare、epg.pw、IPTV 播放列表或任何第三方节目表镜像。

> 本仓库仅保存频道和节目元数据快照，不包含视频流、播放地址、账号信息、会话 Cookie 或绕过访问限制的逻辑。

## 官方来源

| 运营商 | 官方节目表来源 | 七天采集方式 |
| --- | --- | --- |
| Astro | [Content Guide — Channels](https://content.astro.com.my/channels) | 使用官网频道页所调用的公开线性节目接口，按 `scheduleDate` 拉取。 |
| NOW TV（香港） | [TV Guide](https://nowplayer.now.com/tvguide) | 先从官网 TV Guide 读取频道号，再按官网页面脚本的 Day 1–7 节目表请求获取排期。 |

Astro 官网 TV Schedule 会把选择的日期作为 `scheduleDate` 传入节目接口；NOW TV 官网 TV Guide 提供连续七天日期选择。[1] [2]

## 数据文件与订阅

| 文件 | 内容 | 用途 |
| --- | --- | --- |
| `data/current_week.jsonl` | 标准化的当前一周节目记录，每行一条 JSON。 | 本地搜索与审计。 |
| `data/epg.xml.gz` | 压缩的标准 XMLTV 文件。 | 供支持 XMLTV 的播放器或媒体服务器订阅。 |
| `data/status.json` | 各官方来源的采集状态和记录数。 | 运行健康检查。 |

XMLTV 中的频道 ID 采用 `astro.<频道号>` 与 `now_hk.<频道号>` 形式。所有节目保留相应时区的开始与结束时间，并写入官方节目指南 URL 作为来源追溯信息。

## 安装与刷新

需要 Python 3.11 或更高版本。以下命令从两家官网采集未来一周节目表，并生成 JSONL、`epg.xml` 和 `epg.xml.gz`。

```bash
python -m pip install -e .
epg collect --days 7
```

## 本地搜索

搜索只读取本地 JSONL 快照，不访问第三方网站。

```bash
epg search "Premier League"
epg search "News" --provider now_hk
epg search "Drama" --date 2026-08-25 --channel 104
```

节目时段会随运营商排期临时调整。建议每日刷新一次，以维持“当天起未来 7 天”的滚动窗口。

## XMLTV 订阅地址

发布后，可将以下链接直接添加到支持 XMLTV gzip 的播放器或媒体服务器：

```text
https://raw.githubusercontent.com/waastudios/official-epg-search/master/data/epg.xml.gz
```

仓库维护的是当前周滚动快照，而不是无限累积每日历史数据。建议每日刷新一次，以更新“当天起未来 7 天”的节目表。自动化刷新前应审阅运营商相关条款、控制访问频率，并检查定时环境对官网的可达性。

## 参考资料

[1]: https://content.astro.com.my/channels "Astro Content Guide — Channel guide"
[2]: https://nowplayer.now.com/tvguide "NOW TV — TV Guide"
