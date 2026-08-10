#!/usr/bin/env python3
"""Export a redistribution-conscious Nikon recipe discovery index.

The public index retains recipe identity, source links, and original workflow
interpretations. It excludes official descriptions, Picture Control values,
image statistics, hashes, camera metadata, and display-image files.
"""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FULL_INDEX = ROOT / "references" / "nikon-cloud" / "style-index.json"
PUBLIC_INDEX = ROOT / "references" / "nikon-cloud" / "public-style-index.json"
PUBLIC_CATALOG = ROOT / "references" / "nikon-cloud" / "catalog.md"


def clean_summary(text: str) -> str:
    return re.sub(r"官方描述核心：.*$", "", text).rstrip("。；， ") + "。"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=FULL_INDEX)
    parser.add_argument("--output", type=Path, default=PUBLIC_INDEX)
    parser.add_argument("--catalog", type=Path, default=PUBLIC_CATALOG)
    args = parser.parse_args()
    full = json.loads(args.input.read_text(encoding="utf-8"))
    records = []
    for source in full["records"]:
        analysis = dict(source["analysis"])
        analysis["summary_zh"] = clean_summary(analysis["summary_zh"])
        records.append({
            "id": source["id"],
            "name": source["name"],
            "photographer": source["photographer"],
            "public_date": source.get("public_date"),
            "source_page": source["source_page"],
            "sample_path": source["sample_path"],
            "analysis": analysis,
        })
    public = {
        "schema_version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "record_count": len(records),
        "source_url": full["source_url"],
        "notice": "Discovery index containing non-official workflow interpretations. Official descriptions, parameters, metadata, signed URLs, hashes, and display images are excluded.",
        "records": records,
    }
    args.output.write_text(json.dumps(public, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    lines = [
        "# Nikon Imaging Cloud 风格解读目录",
        "",
        f"共 {len(records)} 个公开配方。以下文字是非官方工作流解读；配方名称和来源链接用于识别与溯源。",
        "",
    ]
    for item in sorted(records, key=lambda x: (x["photographer"].casefold(), x["name"].casefold())):
        lines.append(f"- **{item['name']}** — {item['photographer']}：{item['analysis']['summary_zh']} [来源]({item['source_page']})")
    args.catalog.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Exported {len(records)} public discovery records")


if __name__ == "__main__":
    main()
