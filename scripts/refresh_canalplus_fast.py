from __future__ import annotations

import json
from pathlib import Path

import epg_tool.sources as sources
from epg_tool.models import Programme, read_jsonl, write_jsonl
from epg_tool.xmltv import write_xmltv

DATA = Path("data/current_week.jsonl")
STATUS = Path("data/status.json")
XML = Path("data/epg.xml")
GZIP = Path("data/epg.xml.gz")

# The programme source is the official Canal+ EPG API (hodor.canalplus.pro).
# A fresh token is fetched from the authenticate endpoint on every run because
# hard-coded tokens are rejected.  Requests are paced 90 seconds apart because
# the official API rate-limits aggressively.  If the official API is unreachable,
# falls back to the epg.pw France XMLTV (both channels, ~2-3 days).  French
# titles are converted to English through the three-tier translation pipeline,
# and a title that cannot be translated only skips that programme, so this
# refresh never waits on a third-party translation service.
new_records = sources.collect_canalplus_fr(days=7)
if not new_records:
    raise RuntimeError("Canal+ official API returned no records")
notes = sources.drain_notes()

previous = [Programme(**row) for row in read_jsonl(DATA)]
kept = [item for item in previous if item.provider != "canalplus_fr"]
records = kept + new_records
write_jsonl(records, DATA)
channels, programme_count = write_xmltv(records, XML, GZIP)
# source_url 区分实际走的是官方 API 还是 epg.pw 兜底。
source_urls = {row.source_url for row in new_records}
if all(url == sources.EPGPW_FR_URL for url in source_urls):
    actual_source = "epg.pw France XMLTV (fallback, ~2-3 days)"
else:
    actual_source = "official_canalplus_epg_api"
status = json.loads(STATUS.read_text(encoding="utf-8"))
entry = {"status": "ok", "records": len(new_records), "source": actual_source}
if notes:
    entry["notes"] = notes
status["canalplus_fr"] = entry
status["xmltv"]["channels"] = channels
status["xmltv"]["programmes"] = programme_count
status["total_records"] = programme_count
STATUS.write_text(json.dumps(status, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(f"canalplus_records={len(new_records)}")
print(f"xmltv_programmes={programme_count}")
