#!/usr/bin/env python3
"""将 Canal+ 4K 数据并入现有 EPG（current_week.jsonl / epg.xml / status.json）。"""
import json
from pathlib import Path

from epg_tool.models import Programme
from epg_tool.sources import collect_canalplus_pl_4k
from epg_tool.xmltv import write_xmltv

DATA = Path("data")
DATASET = DATA / "current_week.jsonl"
STATUS = DATA / "status.json"
XML = DATA / "epg.xml"
XML_GZ = DATA / "epg.xml.gz"


def load_records(path: Path) -> list[Programme]:
    records = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            records.append(Programme(**json.loads(line)))
    return records


def main():
    # 1. 采集 Canal+ 4K（官方优先，自动兜底 naziemna）
    new_recs = collect_canalplus_pl_4k(days=2)
    print(f"Canal+ 4K 新采集: {len(new_recs)} 档")

    # 2. 加载现有数据，剔除旧的 canalplus_pl_4k
    all_recs = load_records(DATASET)
    kept = [r for r in all_recs if r.provider != "canalplus_pl_4k"]
    print(f"现有: {len(all_recs)} 档，剔除旧 4K 后: {len(kept)} 档")

    merged = kept + new_recs
    merged.sort(key=lambda r: (r.start_at, r.channel_id))

    # 3. 写回 jsonl（先写临时文件，成功再替换）
    tmp = DATASET.with_suffix(".jsonl.tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        for r in merged:
            f.write(json.dumps(r.to_dict(), ensure_ascii=False) + "\n")
    tmp.replace(DATASET)

    # 4. 重新生成 XML
    ch, prog = write_xmltv(merged, XML, XML_GZ)
    print(f"XML: {ch} 频道, {prog} 节目")

    # 5. 更新 status.json
    status = json.loads(STATUS.read_text(encoding="utf-8"))
    status["canalplus_pl_4k"] = {"status": "ok", "records": len(new_recs)}
    STATUS.write_text(json.dumps(status, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"合并完成: {len(merged)} 档")


if __name__ == "__main__":
    main()
