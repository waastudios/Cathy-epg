"""官方节目表采集与检索命令行工具。"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
from pathlib import Path
import json
import sys

import requests

from .models import read_jsonl, write_jsonl
from .sources import (
    SourceUnavailable,
    collect_astro,
    collect_now_hk,
    import_starhub_authorized_export,
)

DEFAULT_DATASET = Path("data/current_week.jsonl")
DEFAULT_STATUS = Path("data/status.json")


def _collect(args: argparse.Namespace) -> int:
    records = []
    status: dict[str, dict[str, object]] = {}

    for provider, collector in (("astro", lambda: collect_astro(args.days)), ("now_hk", lambda: collect_now_hk(args.days))):
        try:
            result = collector()
            records.extend(result)
            status[provider] = {"status": "ok", "records": len(result)}
        except (SourceUnavailable, OSError, ValueError, requests.RequestException) as exc:
            status[provider] = {"status": "error", "records": 0, "message": str(exc)}

    if args.starhub_export:
        try:
            result = import_starhub_authorized_export(args.starhub_export)
            records.extend(result)
            status["starhub"] = {"status": "ok", "records": len(result), "mode": "user_authorized_export"}
        except (OSError, ValueError) as exc:
            status["starhub"] = {"status": "error", "records": 0, "message": str(exc)}
    else:
        status["starhub"] = {
            "status": "requires_user_authorization",
            "records": 0,
            "message": "StarHub 官方指南在当前访客环境不可读取；本工具不会尝试登录或规避访问限制。",
        }

    count = write_jsonl(records, args.output)
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
                    row.get("end_at", ""),
                    row.get("provider", ""),
                    f"{row.get('channel_number', '')} {row.get('channel_name', '')}".strip(),
                    row.get("title", ""),
                ]
            )
        )
    print(f"{len(results)} result(s)", file=sys.stderr)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Official-source-only weekly EPG collector and search tool")
    commands = parser.add_subparsers(dest="command", required=True)

    collect = commands.add_parser("collect", help="采集 Astro 与 NOW TV 香港官网的一周节目表")
    collect.add_argument("--days", type=int, default=7, choices=range(1, 8), metavar="1..7")
    collect.add_argument("--output", type=Path, default=DEFAULT_DATASET)
    collect.add_argument("--status", type=Path, default=DEFAULT_STATUS)
    collect.add_argument(
        "--starhub-export",
        type=Path,
        help="可选：用户从已授权 StarHub TV+ 会话导出的官方 JSON；不会使用或保存凭据。",
    )
    collect.set_defaults(func=_collect)

    search = commands.add_parser("search", help="检索已采集的节目表快照")
    search.add_argument("query", help="节目名或频道名关键词")
    search.add_argument("--input", type=Path, default=DEFAULT_DATASET)
    search.add_argument("--provider", choices=["astro", "now_hk", "starhub"])
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
