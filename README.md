# Official EPG Search

这是一个**仅使用运营商官网**的一周节目表采集与本地搜索原型。它当前面向 Astro（马来西亚）、NOW TV（香港）和 StarHub（新加坡），并明确不读取 EPGshare、epg.pw、IPTV 播放列表或任何第三方节目表镜像。

> 本仓库保存的是节目元数据快照，不包含视频流、播放地址、账号信息、会话 Cookie 或绕过访问限制的逻辑。

## 可行性与来源边界

| 运营商 | 官方节目表来源 | 七天采集状态 | 原型处理 |
| --- | --- | --- | --- |
| Astro | [Content Guide — Channels](https://content.astro.com.my/channels) | 可行。频道页的官方前端调用 `contenthub-api.eco.astro.com.my` 的线性节目接口。 | 直接低频读取官网公开响应。 |
| NOW TV（香港） | [TV Guide](https://nowplayer.now.com/tvguide) | 可行。官网 TV Guide 提供连续七日标签，官方页面脚本按频道号与 Day 1–7 请求节目列表。 | 先从官网指南获得频道号，再请求官网节目列表。 |
| StarHub | [TV+ Guide](https://www.starhubtvplus.com/guide) | **需要用户授权**。StarHub 官方 FAQ 说明指南可浏览未来七天，但当前访客环境无法读取交互式节目表。 | 只接收用户从其已授权会话导出的官方 JSON；不登录、不保存凭据、不规避地域、订阅或反自动化限制。 |

Astro 官网的 TV Schedule 前端将选定日期传入 `scheduleDate`，并将当天与翌日的节目段拼接为日视图；NOW TV 官网的电视指南提供 “Today” 至第七天的日期选择。[1] [2] StarHub 官方 FAQ 将其指南描述为可浏览未来 7 天节目的入口。[3]

## 安装与首次采集

需要 Python 3.11 或更高版本。安装项目后，执行以下命令将从 Astro 和 NOW TV（香港）官网采集未来一周节目表，并生成可提交到 GitHub 的当前快照。

```bash
python -m pip install -e .
epg collect --days 7
```

运行完成后会更新两个文件：

| 文件 | 作用 |
| --- | --- |
| `data/current_week.jsonl` | 标准化的一周节目记录；每行是一条 JSON 记录。 |
| `data/status.json` | 每个来源的成功、失败或授权状态，以及记录数。 |

要在用户自行登录并获得授权的 StarHub 环境中添加 StarHub 记录，可将**只含节目元数据**的官方 JSON 导出传给工具：

```bash
epg collect --days 7 --starhub-export /safe/path/starhub_official_export.json
```

导入格式是 JSON 数组；每项应有 `channel_number`、`channel_name`、`title`、`start_at` 和 `end_at` 字段，可选 `channel_id`。不要提交 Cookie、授权头、播放 URL、Hub iD、密码或任何个人信息。

## 搜索

采集完成后，搜索完全在本地 JSONL 快照上运行，不会访问任何第三方服务。

```bash
epg search "Premier League"
epg search "News" --provider now_hk
epg search "Drama" --date 2026-08-25 --channel 104
```

搜索输出依次为开始时间、结束时间、来源、频道和节目标题。节目时段随运营商排期调整而变化，因此结果应视为快照，并以记录中的 `source_url` 回溯核对。

## 统一数据模型

每条记录包含 `provider`、`country`、`timezone`、`channel_id`、`channel_number`、`channel_name`、`title`、`start_at`、`end_at`、`source_url` 与 `retrieved_at`。完整设计、字段解释和数据保留策略见 [DESIGN.md](DESIGN.md)。

## GitHub 使用方式

本原型建议将 `data/current_week.jsonl` 与 `data/status.json` 作为仓库中的**滚动当前快照**提交，而不要无限叠加每日全量历史。这样 GitHub 可同时承担版本控制、审阅与分发的角色。可在确认各官网使用条款、访问频率和运行环境稳定性后，再为仓库配置由维护者触发的更新工作流。

| 方式 | 优点 | 代价 | 适用场景 |
| --- | --- | --- | --- |
| 本地或服务器定时运行后提交 GitHub | 完全掌控网络位置、访问频率和 StarHub 已授权会话；能在失败时保留诊断。 | 需要维护运行环境。 | 需要 StarHub 授权数据或要长期稳定更新。 |
| 仅手动运行并提交 GitHub | 最简单，不依赖后台服务；适合先验证数据质量。 | 数据不会自动刷新。 | 当前原型与首周数据验收。 |

## 合规原则

本项目只读取运营商自己公开提供的节目指南或由用户自行授权导出的官方结果。任何来源一旦要求登录、订阅、地域校验、验证码或其他访问控制，工具都会报告状态，而不是尝试规避。使用者应在实际自动化前审阅相关运营商条款，并按合理频率请求官网。

## 参考资料

[1]: https://content.astro.com.my/channels "Astro Content Guide — Channel guide"
[2]: https://nowplayer.now.com/tvguide "NOW TV — TV Guide"
[3]: https://www.starhub.com/personal/support/article.html?id=yIYIAKiQcF7ou6fXL9BGH7 "StarHub TV+ App and Web Portal FAQs"
