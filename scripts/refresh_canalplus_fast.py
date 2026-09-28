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

# The programme source is the tvepg.eu France Canal+ public listing (today +
# tomorrow); the official Canal+ JSON API blocks datacenter IPs.  French titles
# are converted to English through the three-tier translation pipeline, and a
# title that cannot be translated only skips that programme, so this refresh
# never waits on a third-party translation service.
new_records = sources.collect_canalplus_fr(days=7)
if not new_records:
    raise RuntimeError("Canal+ official API returned no records")

previous = [Programme(**row) for row in read_jsonl(DATA)]
kept = [item for item in previous if item.provider != "canalplus_fr"]
records = kept + new_records
write_jsonl(records, DATA)
channels, programme_count = write_xmltv(records, XML, GZIP)
status = json.loads(STATUS.read_text(encoding="utf-8"))
status["canalplus_fr"] = {"status": "ok", "records": len(new_records), "source": "tvepg.eu France Canal+ (public listing)"}
status["xmltv"]["channels"] = channels
status["xmltv"]["programmes"] = programme_count
status["total_records"] = programme_count
STATUS.write_text(json.dumps(status, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(f"canalplus_records={len(new_records)}")
print(f"xmltv_programmes={programme_count}")
