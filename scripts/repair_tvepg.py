from pathlib import Path

# The workflow's AST translation hardening can rebuild function bodies; keep the SBB exact map explicit.
SBB_GUARD = r'''
_SBB_EUROSPORT_4K_TITLE_EXACT: dict[str, str] = {
    "Discovery Golf": "Discovery Golf",
    "Magazin: Cycling Show": "Magazine: Cycling Show",
    "NFL Hard Knocks": "NFL Hard Knocks",
    "UEC BMX Racing European Championship - Pregled": "UEC BMX Racing European Championship - Highlights",
}
'''
path = Path("src/epg_tool/sources.py")
source = path.read_text(encoding="utf-8")
source += "\n" + SBB_GUARD
source = source.replace(
    'TVEPG_EUROSPORT_1_GUIDE = "https://tvepg.eu/en/switzerland/channel/eurosport-1-e"',
    'TVEPG_EUROSPORT_1_GUIDE = "https://tvepg.eu/en/switzerland/c/eurosport-1-e"',
)

start = source.find("def collect_tvepg_eurosport_1(")
if start < 0:
    raise SystemExit("collect_tvepg_eurosport_1 not found")

next_def = source.find("\ndef ", start + 5)
if next_def < 0:
    next_def = len(source)

replacement = r'''def collect_tvepg_eurosport_1(days: int = 7) -> list[Programme]:
    if days not in range(1, 8):
        raise ValueError("TVEpg Eurosport 1 采集天数必须为 1–7。")
    session = _session()
    session.headers.update({
        "Accept": "text/html,application/xhtml+xml",
        "Referer": "https://tvepg.eu/en/switzerland/",
    })
    zone = ZoneInfo("Europe/Zurich")
    today = datetime.now(zone).date()
    last_day = today + timedelta(days=days)

    response = session.get(TVEPG_EUROSPORT_1_GUIDE, timeout=30)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")

    records: list[Programme] = []
    current_date = None
    pending: list[tuple[datetime, str]] = []

    def flush() -> None:
        nonlocal pending
        for index, (start, title) in enumerate(pending):
            end = pending[index + 1][0] if index + 1 < len(pending) else start + timedelta(hours=2)
            if end <= start:
                continue
            if today <= start.date() < last_day:
                records.append(
                    Programme(
                        provider="tvepg_eurosport",
                        country="CH",
                        timezone="Europe/Zurich",
                        channel_id="eurosport.1",
                        channel_number="eurosport.1",
                        channel_name="Eurosport 1",
                        title=title,
                        start_at=start.isoformat(),
                        end_at=end.isoformat(),
                        source_url=TVEPG_EUROSPORT_1_GUIDE,
                        retrieved_at=utc_now_iso(),
                    )
                )
        pending = []

    for element in soup.find_all(["h1", "h2", "h3", "h4", "h5", "h6", "a"]):
        if element.name in {"h1", "h2", "h3", "h4", "h5", "h6"}:
            heading = element.get_text(" ", strip=True)
            match = re.search(r"(Today|Tomorrow)\s*-\s*(\d{2}/\d{2}/\d{4})\s*-", heading, re.I)
            if match:
                flush()
                current_date = datetime.strptime(match.group(2), "%d/%m/%Y").date()
            continue

        if current_date is None:
            continue
        text = element.get_text(" ", strip=True)
        match = re.match(r"^(\d{2}:\d{2})\s+(.+)$", text)
        if not match:
            continue
        title = match.group(2).strip()
        if not title:
            continue
        start = datetime.combine(
            current_date,
            datetime.strptime(match.group(1), "%H:%M").time(),
            tzinfo=zone,
        )
        pending.append((start, title))

    flush()
    records = _deduplicate(records)
    if not records:
        raise SourceUnavailable("TVEpg Eurosport 1 官方频道页未返回目标日期节目。")
    return records
'''

path.write_text(source[:start] + replacement + source[next_def:] + "\n", encoding="utf-8")
print("TVEpg Eurosport 1 collector repaired.")
