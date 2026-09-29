#!/usr/bin/env python3
"""手动采集波兰 Canal+ 4K ULTRA HD 的 7 天 EPG。

在你自己电脑上跑（住宅 IP 不会被 Canal+ 封），跑完把生成的
data/canalplus_pl_4k.jsonl 发回来即可。

用法：
    pip install requests
    python3 manual_canalplus_pl_4k.py
"""

import json
import sys
import time
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

import requests

AUTH_URL = (
    "https://hodor.canalplus.pro/api/v2/mycanalint/authenticate.json/webapp/6.0"
    "?experiments=beta-test-one-tv-guide:control"
)
CHANNEL_ID = "21402"
GUIDE_URL = "https://www.canalplus.com/pl/program-tv/"
DAYS = 7
PAUSE = 90  # 秒，Canal+ 限流很严，不要改小

HEADERS = {
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "pl-PL,pl;q=0.6",
    "Origin": "https://www.canalplus.com",
    "Referer": GUIDE_URL,
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/145.0.0.0 Safari/537.36",
}


def get(session, url, **kwargs):
    last = None
    for _ in range(3):
        try:
            r = session.get(url, **kwargs)
            if r.status_code == 403:
                print("  403 被限流，等 65 秒重试…", flush=True)
                time.sleep(65)
                continue
            r.raise_for_status()
            return r
        except (requests.Timeout, requests.ConnectionError) as e:
            last = e
            time.sleep(10)
    raise RuntimeError(f"请求失败: {url} ({last})")


def main():
    session = requests.Session()
    print("1/3 拿 token…", flush=True)
    token = get(session, AUTH_URL, headers=HEADERS, timeout=(5, 20)).json().get("token")
    if not token:
        sys.exit("没拿到 token，退出")
    print("   token ok", flush=True)
    time.sleep(PAUSE)

    zone = ZoneInfo("Europe/Warsaw")
    out = []
    for day in range(DAYS):
        print(f"2/3 拉第 {day + 1}/{DAYS} 天…", flush=True)
        url = (
            f"https://hodor.canalplus.pro/api/v2/mycanalint/channels/"
            f"{token}/{CHANNEL_ID}/broadcasts/day/{day}"
        )
        payload = get(
            session, url,
            params={"channelPosition": 149},
            headers=HEADERS, timeout=(5, 20),
        ).json()
        for sl in payload.get("timeSlices", []):
            for c in sl.get("contents", []) or []:
                title = (c.get("title") or "").strip()
                start_ms, end_ms = c.get("startTime"), c.get("endTime")
                if not title or not isinstance(start_ms, (int, float)):
                    continue
                start = datetime.fromtimestamp(start_ms / 1000, tz=timezone.utc).astimezone(zone)
                end = (datetime.fromtimestamp(end_ms / 1000, tz=timezone.utc).astimezone(zone)
                       if isinstance(end_ms, (int, float)) else None)
                if end is not None and end <= start:
                    continue
                subtitle = (c.get("subtitle") or "").strip()
                if subtitle and subtitle != title:
                    title = f"{title} — {subtitle}"
                out.append({
                    "channel_id": "canal+4k.pl",
                    "channel_name": "CANAL+ 4K ULTRA HD",
                    "title": title,  # 波兰语原标题，后续统一翻译
                    "start_at": start.isoformat(),
                    "end_at": end.isoformat() if end else None,
                })
        time.sleep(PAUSE)

    path = "data/canalplus_pl_4k.jsonl"
    with open(path, "w", encoding="utf-8") as f:
        for row in out:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    print(f"3/3 完成：{len(out)} 条，写到 {path}", flush=True)


if __name__ == "__main__":
    main()
