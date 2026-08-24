# 官方节目表聚合原型：数据设计与采集边界

本原型的目标是把 **StarHub（新加坡）**、**Astro（马来西亚）** 和 **NOW TV（香港）** 的官网节目表整理为可版本控制的统一数据集，供本地命令行检索和后续 GitHub Pages／API 前端使用。程序只请求各运营商官网或其官方子域，明确拒绝读取 EPGshare、epg.pw、IPTV 社区库或任何第三方节目表镜像。

## 统一记录模型

每一条节目记录以 JSON 表示，并保留来源链接与采集时间，确保可以追溯回运营商官方节目指南。

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `provider` | string | `astro`、`now_hk` 或 `starhub`。 |
| `country` | string | 服务市场的 ISO 3166-1 两位代码：`MY`、`HK` 或 `SG`。 |
| `timezone` | string | 运营商节目时间的 IANA 时区，例如 `Asia/Kuala_Lumpur`。 |
| `channel_id` | string | 来源方原始频道标识。 |
| `channel_number` | string | 面向用户展示的频道号码。 |
| `channel_name` | string | 频道名称。 |
| `title` | string | 节目标题。 |
| `start_at` | string | ISO 8601 含时区的开始时间。 |
| `end_at` | string | ISO 8601 含时区的结束时间。 |
| `source_url` | string | 对应官方节目页或官方节目指南的 URL。 |
| `retrieved_at` | string | 数据采集时间（UTC、ISO 8601）。 |

> 节目数据以运营商网页在采集时公开呈现的结果为准。节目时段会临时调整，因此数据集应视为可更新的快照，而非永久节目档案。

## 官方来源与访问策略

| 来源 | 官方入口／接口 | 七天能力 | 原型处理方式 |
| --- | --- | --- | --- |
| Astro | `contenthub-api.eco.astro.com.my/api/v2/search-linear` | 官网 TV Schedule 界面请求选中日期及翌日数据。 | 无需账户的公开 GET 请求；用 `scheduleDate`、`channelLimit` 与 `channelPage` 拉取并标准化。 |
| NOW TV（香港） | `nowplayer.now.com/tvguide/epglist` | 官方 TV Guide 的 Day 1–7 切换。 | 先从官方 TV Guide HTML 获得频道号；再依官方页面脚本所用的 `channelIdList` 与 `day` 参数获取节目表。 |
| StarHub | `starhubtvplus.com/guide` | 官方 FAQ 写明可浏览未来 7 天。 | 仅当用户在自己的已授权 StarHub 会话内导出官方指南响应时接入；采集器不得保存 Hub iD、密码、Cookie 或规避地域、订阅、反机器人等限制。 |

## GitHub 存储策略

原型每次运行仅更新 `data/current_week.jsonl` 与 `data/status.json`。这避免将重复的每日完整节目表不断累积到 Git 历史中。`data/current_week.jsonl` 只保存本次可读来源的一周记录；`data/status.json` 明确标记每个运营商的成功、部分成功或“需要用户授权”状态。GitHub Actions 的定时运行可作为后续增强，但应先验证运营商条款、速率限制以及运行环境的访问可靠性。

## 搜索行为

`python -m epg_tool search <关键词>` 以大小写不敏感方式检索节目标题与频道名称，并允许以 `--provider`、`--date`、`--channel` 限定结果。工具从本地 JSONL 读取，因而搜索无需访问第三方数据源。

## 合规与可靠性原则

本项目不提供或暗示规避登录、付费订阅、地理限制、验证码或反自动化机制的方法。对官方页面应使用低频、带标识的请求，并以失败状态替代重试风暴。发布到 GitHub 的数据集应只包含必要的频道和节目元数据，绝不提交会话 Cookie、令牌、账号资料、视频播放地址或受保护的节目内容。
