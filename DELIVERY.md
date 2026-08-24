# 官方 XMLTV 节目表：交付报告

**项目范围：** Astro（马来西亚）与 NOW TV（香港）官网节目表。  
**仓库：** <https://github.com/waastudios/official-epg-search>  
**XMLTV 订阅地址：** `https://raw.githubusercontent.com/waastudios/official-epg-search/master/data/epg.xml.gz`

## 已交付内容

本次已删除 StarHub 采集、导入与文档内容。仓库现在只保留 Astro 和 NOW TV（香港）两个运营商官网来源；未使用 EPGshare、epg.pw、IPTV 社区库或其他第三方节目表聚合站。

| 来源 | 市场 | 官方入口 | 本次记录数 |
| --- | --- | --- | ---: |
| Astro | 马来西亚 | [Content Guide — Channels](https://content.astro.com.my/channels) | 29,157 |
| NOW TV | 香港 | [TV Guide](https://nowplayer.now.com/tvguide) | 23,035 |
| **合计** |  |  | **52,192** |

## XMLTV 文件

| 文件 | 大小 | 验证结果 |
| --- | ---: | --- |
| `data/epg.xml` | 约 11 MB | 标准 XMLTV 文本输出。 |
| `data/epg.xml.gz` | 约 571 KB | 已通过 gzip 完整性测试。 |

导出的 XMLTV 包含 **284 个频道**和 **52,192 条节目**。频道 ID 使用 `astro.<频道号>` 与 `now_hk.<频道号>` 的稳定形式；节目 `start`、`stop` 时间保留 `+0800` 时区偏移。

## 订阅与刷新

支持 XMLTV gzip 的客户端可直接使用以下地址：

```text
https://raw.githubusercontent.com/waastudios/official-epg-search/master/data/epg.xml.gz
```

建议每天刷新一次，以维持“当天起未来 7 天”的滚动节目表。刷新的命令如下：

```bash
python -m pip install -e .
epg collect --days 7
```

> 仓库现已公开，且订阅地址已验证可在无需认证的情况下返回 HTTP 200 与完整 gzip 内容。

## 参考资料

[1]: https://content.astro.com.my/channels "Astro Content Guide — Channel guide"
[2]: https://nowplayer.now.com/tvguide "NOW TV — TV Guide"
