# Cathy-epg 交付报告

## 本次交付

本次更新将项目扩展为六类官方来源，并保持 **不使用 EPGshare、epg.pw 或其他第三方节目表聚合接口** 的约束。已生成新的 `data/epg.xml.gz`，并将仓库目标名称设为 **Cathy-epg**。

| 来源键 | 市场与范围 | 本次记录数 | 官方数据页面 | 覆盖说明 |
| --- | --- | --- | --- | --- |
| `astro` | 马来西亚 Astro | 29,166 | [Astro Content Guide](https://www.astro.com.my/content/channels) | 七日线性节目表 |
| `now_hk` | 香港 NOW TV | 22,899 | [NOW TV Guide](https://nowplayer.now.com/tvguide) | 七日线性节目表；官网中文频道名 |
| [`allente_se`] | 瑞典完整 V Sport 体育频道组合 | 901 | [Allente TV Guide](https://www.allente.se/tv-guide/) | 13 个频道的七日节目表 |
| `now_uk` | 英国 NOW Sports / Sky Sports | 123 | [Sky Sports live schedule](https://www.sky.com/watch/channel/sky-sports) | 官方直播活动；无全频道全天 EPG |
| `digi4k_ro` | 罗马尼亚 Digi 4K | 115 | [Digi 4K](https://www.digi4k.ro/) | 官网连续七日节目表 |
| `tvplus_tr` | 土耳其 Eurosport 1、2 | 34 | [TV+ Eurosport 1](https://tvplus.com.tr/canli-tv/yayin-akisi/eurosport-1-hd--77)、[TV+ Eurosport 2](https://tvplus.com.tr/canli-tv/yayin-akisi/eurosport-2-hd--106) | 官方电视提供商公开的当日完整节目表 |

HBO Max 土耳其英文页用于验证当地提供 Eurosport 1 与 Eurosport 2；因该页不提供逐频道时刻表，节目明细来自同一市场官方电视提供商 TV+ 的公开节目页面。[1]

## 生成与验证

最新快照生成于 **2026-08-24 13:54:49 UTC**。`data/status.json` 显示全部六个来源采集成功，共写入 **53,180** 条节目、**311** 个 XMLTV 频道。`gzip -t data/epg.xml.gz` 已通过，说明压缩文件可正常解压。Allente 来源现覆盖 13 条官方 V Sport 体育频道，并写入 **901** 条七日节目记录。

瑞典 Allente 官方频道集合现包括 **V sport extra HD、premium HD、football HD、vinter HD、motor HD、V sport 1 HD、ultra HD、golf HD 与 V sport live 1–5**；所有频道保留 Allente 的稳定频道 ID。香港频道的 XMLTV ID 没有变更：`now_hk.138` 仍为该 ID；其显示名已改为 NOW TV 官网中文名称 **Now爆谷星影台**。该变化仅影响 `display-name`，不破坏使用稳定频道 ID 的订阅端配置。

## 订阅地址

```
https://raw.githubusercontent.com/waastudios/Cathy-epg/master/data/epg.xml.gz
```

该文件是当前起未来七天的滚动快照 。建议每日刷新；土耳其 TV+ 的匿名公开 SSR 页面当前稳定提供当日节目，其后续日排期在官网浏览器会话中动态加载，因此本快照不会伪造未来的 Eurosport 时段。

## 参考资料

[1]: https://www.hbomax.com/tr/en "HBO Max Türkiye — English site"

[2]: https://www.digi4k.ro/ "Digi 4K România"

[3]: https://tvplus.com.tr/canli-tv/yayin-akisi/eurosport-1-hd--77 "TV+ — Eurosport 1 schedule"

[4]: https://tvplus.com.tr/canli-tv/yayin-akisi/eurosport-2-hd--106 "TV+ — Eurosport 2 schedule"
[5]: https://www.allente.se/tv-guide/ "Allente — TV Guide"

