"""官方节目表采集与检索命令行工具。"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
from pathlib import Path
import json
import sys

import requests

from .models import read_jsonl, write_jsonl
from .xmltv import write_xmltv
from .tvguide_images import enrich_tvguide_uk_images
from .sources import (
    SourceUnavailable,
    collect_allente_no,
    collect_allente_v_sport,
    collect_astro,
    collect_digi4k,
    collect_ee_uk_channels,
    collect_magenta_tv_sky_de,
    collect_now_hk,
    collect_sbb_eurosport_4k,
    collect_tvplus_eurosport,
    collect_virgin_uk_ultra,
)

DEFAULT_DATASET = Path("data/current_week.jsonl")
DEFAULT_STATUS = Path("data/status.json")
DEFAULT_XML = Path("data/epg.xml")
DEFAULT_XML_GZIP = Path("data/epg.xml.gz")


def _collect(args: argparse.Namespace) -> int:
    records = []
    status: dict[str, dict[str, object]] = {}

    collectors = (
        ("astro", lambda: collect_astro(args.days)),
        ("now_hk", lambda: collect_now_hk(args.days)),
        ("allente_se", lambda: collect_allente_v_sport(args.days)),
        ("allente_no", lambda: collect_allente_no(args.days)),
        # EE TV Player 提供完整频道级 start/stop；只保留 SD 主频道，避免 HD／+1 镜像重复。
        ("ee_uk", lambda: collect_ee_uk_channels(args.days)),
        # Telekom MagentaTV 的匿名官方生产节目表；XMLTV ID 使用用户指定 Sky Germany 频道号。
        ("sky_de", lambda: collect_magenta_tv_sky_de(args.days)),
        ("digi4k_ro", lambda: collect_digi4k(args.days)),
        ("tvplus_tr", lambda: collect_tvplus_eurosport(args.days)),
        ("sbb_rs", lambda: collect_sbb_eurosport_4k(args.days)),
        ("virgin_uk", lambda: collect_virgin_uk_ultra(args.days)),
    )
    for provider, collector in collectors:
        try:
            result = collector()
            records.extend(result)
            status[provider] = {"status": "ok", "records": len(result)}
        except (SourceUnavailable, OSError, ValueError, requests.RequestException) as exc:
            status[provider] = {"status": "error", "records": 0, "message": str(exc)}

    # The user has obtained permission from TVGuide.co.uk to link programme artwork.
    # Image matching is optional enrichment: source EPG collection remains publishable
    # if the third-party artwork service is temporarily unavailable.
    try:
        records, image_stats = enrich_tvguide_uk_images(records)
        status["tvguide_images"] = {"status": "ok", **image_stats}
    except (OSError, ValueError, requests.RequestException) as exc:
        status["tvguide_images"] = {"status": "error", "message": str(exc)}

    count = write_jsonl(records, args.output)
    channel_count, programme_count = write_xmltv(records, args.xml_output, args.xml_gzip_output)
    status["xmltv"] = {
        "status": "ok",
        "channels": channel_count,
        "programmes": programme_count,
        "xml_file": str(args.xml_output),
        "gzip_file": str(args.xml_gzip_output),
    }
    status["generated_at"] = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    status["total_records"] = count
    args.status.parent.mkdir(parents=True, exist_ok=True)
    args.status.write_text(json.dumps(status, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(status, ensure_ascii=False, indent=2))
    return 0 if count else 2


def _search(args: argparse.Namespace) -> int:
    query = args.query.casefold()
    rows = read_jsonl(args.input)
    results = []
    for row in rows:
        if args.provider and row.get("provider") != args.provider:
            continue
        if args.channel and row.get("channel_number") != args.channel:
            continue
        if args.date and not row.get("start_at", "").startswith(args.date):
            continue
        searchable = f"{row.get('title', '')} {row.get('channel_name', '')}".casefold()
        if query in searchable:
            results.append(row)
    for row in results:
        print(
            "\t".join(
                [
                    row.get("start_at", ""),
                    row.get("end_at") or "",
                    row.get("provider", ""),
                    f"{row.get('channel_number', '')} {row.get('channel_name', '')}".strip(),
                    row.get("title", ""),
                ]
            )
        )
    print(f"{len(results)} result(s)", file=sys.stderr)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Weekly XMLTV collector with user-authorised UK programme artwork linking")
    commands = parser.add_subparsers(dest="command", required=True)

    collect = commands.add_parser("collect", help="采集官方节目来源的一周节目表")
    collect.add_argument("--days", type=int, default=7, choices=range(1, 8), metavar="1..7")
    collect.add_argument("--output", type=Path, default=DEFAULT_DATASET)
    collect.add_argument("--status", type=Path, default=DEFAULT_STATUS)
    collect.add_argument("--xml-output", type=Path, default=DEFAULT_XML)
    collect.add_argument("--xml-gzip-output", type=Path, default=DEFAULT_XML_GZIP)
    collect.set_defaults(func=_collect)

    search = commands.add_parser("search", help="检索已采集的节目表快照")
    search.add_argument("query", help="节目名或频道名关键词")
    search.add_argument("--input", type=Path, default=DEFAULT_DATASET)
    search.add_argument("--provider", choices=["astro", "now_hk", "allente_se", "allente_no", "ee_uk", "sky_de", "digi4k_ro", "tvplus_tr", "sbb_rs", "virgin_uk"])
    search.add_argument("--channel")
    search.add_argument("--date", help="节目开始日期，格式 YYYY-MM-DD")
    search.set_defaults(func=_search)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        return args.func(args)
    except BrokenPipeError:
        # 允许 `epg search ... | head` 等常用管道写法正常结束。
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
