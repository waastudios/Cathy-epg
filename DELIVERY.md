# 官方节目表搜索工具：交付报告

**交付日期：** 2026-08-24（GMT+8）  
**仓库：** <https://github.com/waastudios/official-epg-search>（私有）

## 结论

该方案**可行**，并且已经完成一个只使用运营商官网的一周节目表采集与本地搜索原型。原型没有使用 EPGshare、epg.pw、IPTV 社区库或其他第三方节目表聚合站。

Astro 和 NOW TV（香港）已成功从其官网公开节目指南路径生成一周数据快照。StarHub 的官方说明确认 TV Guide 可以浏览未来七天节目，但在当前未登录访客环境中没有取得可解析的节目表；因此仓库将 StarHub 设计为**仅接受用户在已授权会话内自行导出的官方节目元数据**，不会处理登录、Cookie、付费订阅、地域限制、验证码或反自动化规避。

## 本次一周快照

采集于 2026-08-24，节目开始日期覆盖 2026-08-24 至 2026-08-30。数据位于仓库的 `data/current_week.jsonl`，来源运行状态位于 `data/status.json`。

| 来源 | 市场 | 记录数 | 状态 | 官方入口 |
| --- | --- | ---: | --- | --- |
| Astro | 马来西亚 | 29,157 | 成功 | [Content Guide — Channels](https://content.astro.com.my/channels) |
| NOW TV | 香港 | 23,035 | 成功 | [TV Guide](https://nowplayer.now.com/tvguide) |
| StarHub TV+ | 新加坡 | 0 | 需要用户授权 | [TV+ Guide](https://www.starhubtvplus.com/guide) |
| **合计** |  | **52,192** | 部分完成 |  |

> StarHub 的 0 条记录不是来自第三方替代源，而是有意遵守其官方网关与授权边界的结果。

## 已交付内容

| 内容 | 位置 | 说明 |
| --- | --- | --- |
| 官网采集器 | `src/epg_tool/sources.py` | Astro 与 NOW TV（香港）的官网一周采集；StarHub 官方授权导入入口。 |
| 本地搜索工具 | `src/epg_tool/cli.py` | 按关键词、来源、日期及频道搜索当前快照。 |
| 统一数据规范 | `DESIGN.md` | 字段、可追溯来源和合规边界。 |
| 操作指南 | `README.md` | 安装、采集、搜索与 GitHub 使用说明。 |
| 当前周数据 | `data/current_week.jsonl` | 52,192 条已验证 JSONL 记录。 |
| 来源状态 | `data/status.json` | 记录各来源成功、失败与授权状态。 |

## 运行方法

安装依赖后，以下命令会刷新 Astro 和 NOW TV（香港）未来 1–7 天的节目表数据。

```bash
python -m pip install -e .
epg collect --days 7
```

以下命令检索已采集数据，不访问第三方网站。

```bash
epg search "Premier League"
epg search "News" --provider now_hk
epg search "Drama" --date 2026-08-25 --channel 104
```

如要加入 StarHub，维护者需要在自己已授权的 StarHub TV+ 会话中，以合规方式导出**仅含节目元数据**的 JSON，然后运行：

```bash
epg collect --days 7 --starhub-export /safe/path/starhub_official_export.json
```

导出文件不得包含 Cookie、访问令牌、Hub iD、密码、视频地址或任何个人资料。

## 建议的后续路线

| 方式 | 结果 | 适用性 |
| --- | --- | --- |
| 保持手动刷新并提交当前周快照 | 最低维护成本，最适合先验证字段和搜索体验。 | 当前阶段推荐。 |
| 在可控运行环境中每日刷新并自动提交 | 数据更及时，但需先审阅官网条款、访问频率与网络可靠性；StarHub 仍必须由用户授权。 | 数据质量验收后再启用。 |
| 在此数据层上增加静态搜索页面 | 可为公众提供浏览界面，但应先决定许可证、缓存时长和节目元数据的分发边界。 | 产品化阶段。 |

## 参考资料

[1]: https://content.astro.com.my/channels "Astro Content Guide — Channel guide"
[2]: https://nowplayer.now.com/tvguide "NOW TV — TV Guide"
[3]: https://www.starhub.com/personal/support/article.html?id=yIYIAKiQcF7ou6fXL9BGH7 "StarHub TV+ App and Web Portal FAQs"
