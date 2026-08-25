"""统一节目表记录模型与本地数据集读写。"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
import json
from typing import Iterable


@dataclass(frozen=True)
class Programme:
    """一条可追溯至运营商官方页面的节目记录。"""

    provider: str
    country: str
    timezone: str
    channel_id: str
    channel_number: str
    channel_name: str
    title: str
    start_at: str
    end_at: str | None
    source_url: str
    retrieved_at: str

    def to_dict(self) -> dict[str, str | None]:
        return asdict(self)


def utc_now_iso() -> str:
    """返回无歧义的 UTC 采集时间。"""
    return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"


def write_jsonl(records: Iterable[Programme], destination: Path) -> int:
    """按稳定顺序覆盖写入 JSONL，并返回记录数。"""
    rows = sorted(
        records,
        key=lambda item: (
            item.start_at,
            item.end_at or "",
            item.provider,
            item.channel_number,
            item.title,
        ),
    )
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row.to_dict(), ensure_ascii=False, separators=(",", ":")))
            handle.write("\n")
    return len(rows)


def read_jsonl(source: Path) -> list[dict[str, str]]:
    """读取本工具写入的节目记录。"""
    if not source.exists():
        return []
    with source.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]
