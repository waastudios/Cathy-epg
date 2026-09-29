#!/usr/bin/env python3
"""从 programtv.naziemna.info 抓取 Canal+ 4K Ultra HD 节目单（7天）。

输出 data/canalplus_pl_4k.jsonl，每行: {"start": "ISO", "end": "ISO", "title": "波兰语原标题"}
"""
import re
import sys
import json
import time
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import requests

BASE = "https://programtv.naziemna.info"
STATION = "canalplus4kultrahd"
TZ = ZoneInfo("Europe/Warsaw")

# 波兰语月份 -> 数字
MONTHS = {
    "stycznia": 1, "lutego": 2, "marca": 3, "kwietnia": 4,
    "maja": 5, "czerwca": 6, "lipca": 7, "sierpnia": 8,
    "września": 9, "października": 10, "listopada": 11, "grudnia": 12,
}

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
}


def fetch(url: str) -> str:
    r = requests.get(url, headers=HEADERS, timeout=30)
    r.raise_for_status()
    return r.text


def parse_programs(html: str, day: datetime):
    """解析一天的节目，返回 [(start_dt, title)]"""
    # 匹配 <span class="text-monospace">HH:MM</span> <strong>标题</strong>
    pattern = re.compile(
        r'<span class="text-monospace">(\d{2}:\d{2})</span>\s*<strong>([^<]+)</strong>'
    )
    results = []
    for m in pattern.finditer(html):
        t, title = m.group(1), m.group(2).strip()
        h, mi = int(t[:2]), int(t[3:])
        # 凌晨节目（00:00-05:59）可能属于第二天，简单处理：如果比前一条早很多则+1天
        dt = day.replace(hour=h, minute=mi, second=0, microsecond=0, tzinfo=TZ)
        results.append((dt, title))
    return results


def get_day_links(html: str):
    """从页面提取可用的日期链接"""
    links = re.findall(
        r'href="/program/stacja/canalplus4kultrahd,([^"]+)"', html
    )
    return sorted(set(links))


def main():
    out_path = Path("data/canalplus_pl_4k.jsonl")
    out_path.parent.mkdir(parents=True, exist_ok=True)

    # 先抓今天，拿到日期导航
    today_url = f"{BASE}/program/stacja/{STATION}"
    html = fetch(today_url)
    day_links = get_day_links(html)

    today = datetime.now(TZ).replace(hour=0, minute=0, second=0, microsecond=0)
    all_programs = []

    # 今天
    all_programs.extend(parse_programs(html, today))
    print(f"今天 ({today.date()}): {len(all_programs)} 档", flush=True)

    # 其他日期
    for link in day_links:
        m = re.match(r"(\d+)-(\w+)", link)
        if not m:
            continue
        d, mon_name = int(m.group(1)), m.group(2)
        mon = MONTHS.get(mon_name)
        if not mon:
            continue
        day = today.replace(day=d, month=mon)
        # 只取未来7天
        if not (0 < (day - today).days <= 7):
            continue
        url = f"{BASE}/program/stacja/{STATION},{link}"
        try:
            h = fetch(url)
            progs = parse_programs(h, day)
            all_programs.extend(progs)
            print(f"{day.date()}: {len(progs)} 档", flush=True)
        except Exception as e:
            print(f"{day.date()}: 失败 {e}", flush=True)
        time.sleep(3)

    # 排序，去重
    all_programs.sort(key=lambda x: x[0])
    seen = set()
    unique = []
    for dt, title in all_programs:
        key = (dt.isoformat(), title)
        if key not in seen:
            seen.add(key)
            unique.append((dt, title))

    # 写 jsonl（start/end，end 暂用下一档的 start）
    with open(out_path, "w", encoding="utf-8") as f:
        for i, (dt, title) in enumerate(unique):
            end = unique[i + 1][0] if i + 1 < len(unique) else dt + timedelta(hours=2)
            f.write(json.dumps({
                "start": dt.isoformat(),
                "end": end.isoformat(),
                "title": title,
            }, ensure_ascii=False) + "\n")

    print(f"\n共 {len(unique)} 档 -> {out_path}")


if __name__ == "__main__":
    main()
