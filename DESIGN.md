# 官方节目表聚合：数据设计与采集边界

本工具把 **Astro（马来西亚）** 与 **NOW TV（香港）** 的官网节目表整理为可版本控制的统一数据集，并同时生成标准 XMLTV 文件。程序只请求两家运营商的官网或官方子域；它明确拒绝读取 EPGshare、epg.pw、IPTV 社区库或任何第三方节目表镜像。

## 统一记录模型

每一条节目记录都保留来源链接与采集时间，确保可以回溯至运营商官方节目指南。

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `provider` | string | `astro` 或 `now_hk`。 |
| `country` | string | 服务市场的 ISO 3166-1 两位代码：`MY` 或 `HK`。 |
| `timezone` | string | 运营商节目时间的 IANA 时区。 |
| `channel_id` | string | 来源方原始频道标识。 |
| `channel_number` | string | 面向用户展示的频道号码。 |
| `channel_name` | string | 频道名称。 |
| `title` | string | 节目标题。 |
| `start_at` | string | ISO 8601 含时区的开始时间。 |
| `end_at` | string | ISO 8601 含时区的结束时间。 |
| `source_url` | string | 对应官方节目页或官方节目指南 URL。 |
| `retrieved_at` | string | 采集时间（UTC、ISO 8601）。 |

## 官方来源与访问策略

| 来源 | 官方入口／接口 | 七天能力 | 原型处理方式 |
| --- | --- | --- | --- |
| Astro | `contenthub-api.eco.astro.com.my/api/v2/search-linear` | 官网 TV Schedule 界面按日期读取节目表。 | 以低频公开 GET 请求，使用 `scheduleDate`、`channelLimit` 与 `channelPage` 获取并标准化。 |
| NOW TV（香港） | `nowplayer.now.com/tvguide/epglist` | 官方 TV Guide 提供 Day 1–7 日期切换。 | 先从官方 TV Guide HTML 获得频道号，再依官网脚本的 `channelIdList` 与 `day` 参数请求节目表。 |

## 文件输出

每次采集覆盖更新以下滚动快照，避免在 Git 历史中无限累积重复全量节目表。

| 文件 | 格式 | 用途 |
| --- | --- | --- |
| `data/current_week.jsonl` | JSON Lines | 统一记录、审计与本地搜索。 |
| `data/epg.xml` | XMLTV | 解压后的标准节目表。 |
| `data/epg.xml.gz` | gzip 压缩 XMLTV | 适合 XMLTV 客户端订阅。 |
| `data/status.json` | JSON | 两个来源的成功或失败状态及记录数。 |

XMLTV 中每个频道会生成稳定 ID：`astro.<频道号>` 或 `now_hk.<频道号>`。每个 `<programme>` 保留 `start`、`stop`、标题及官方来源 URL；文件的 `generator-info-name` 标示为 `official-epg-search`。

## 合规与可靠性原则

节目数据以运营商网页在采集时公开呈现的结果为准，节目时段可能临时调整。对官方页面应使用低频、带标识的请求，并以失败状态替代重试风暴。发布到 GitHub 的数据只应包含必要的频道和节目元数据，不应提交账号资料、会话 Cookie、令牌、视频播放地址或受保护节目内容。
