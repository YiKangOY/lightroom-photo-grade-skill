#!/usr/bin/env python3
"""Rank locally indexed Nikon Imaging Cloud recipes for a style request."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / "references" / "nikon-cloud" / "style-index.json"
PUBLIC_INDEX = ROOT / "references" / "nikon-cloud" / "public-style-index.json"

SYNONYMS = {
    "电影": ["电影感", "cinematic", "filmic", "movie", "cine"],
    "冷": ["冷调", "冷色", "青", "蓝", "忧郁"],
    "暖": ["暖调", "温暖", "金色", "橙", "黄", "琥珀"],
    "复古": ["胶片", "怀旧", "film", "vintage"],
    "人像": ["人物", "肤色", "肖像", "portrait"],
    "夜景": ["夜间", "霓虹", "低光", "蓝调时刻"],
    "自然": ["森林", "植物", "花卉", "风景", "户外"],
    "黑白": ["黒白", "灰度", "achromic", "monochrome"],
    "清透": ["通透", "透明感", "清新", "澄澈"],
    "柔和": ["低对比", "梦幻", "细腻", "温柔", "粉彩"],
    "强烈": ["高反差", "高对比", "张力", "冲击", "前卫"],
}


def tokens(query: str) -> list[str]:
    base = [x.lower() for x in re.findall(r"[\w&+-]+|[\u4e00-\u9fff]{1,4}", query)]
    expanded = list(base)
    for key, values in SYNONYMS.items():
        if key in query or any(v.lower() in query.lower() for v in values):
            expanded.extend([key, *values])
    return list(dict.fromkeys(x.lower() for x in expanded if x))


def score(record: dict, query: str) -> tuple[float, list[str]]:
    a = record["analysis"]
    fields = {
        "name": record["name"], "photographer": record["photographer"],
        "tags": " ".join(a["scene_tags"] + a["mood_tags"] + a["palette"]),
        "summary": a["summary_zh"], "use": a["best_for"],
        "official": record.get("official_description", ""),
    }
    weights = {"name": 8, "photographer": 7, "tags": 5, "summary": 3, "use": 2, "official": 1}
    total, hits = 0.0, []
    qlower = query.lower().strip()
    if qlower and (qlower in fields["name"].lower() or qlower in fields["photographer"].lower()):
        total += 30
        hits.append("精确名称/作者")
    all_text = " ".join(fields.values()).lower()
    for concept, related in SYNONYMS.items():
        if concept in qlower:
            candidates = [concept, *related]
            if any(candidate.lower() in all_text for candidate in candidates):
                total += 18
                hits.append(f"概念:{concept}")
    for token in tokens(query):
        matched = False
        for field, value in fields.items():
            if token in value.lower():
                total += weights[field]
                matched = True
        if matched:
            hits.append(token)
    return total, list(dict.fromkeys(hits))


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("query", help="中文或英文风格、场景、摄影师、配方名")
    p.add_argument("--limit", type=int, default=5)
    p.add_argument("--json", action="store_true")
    p.add_argument("--index", type=Path, default=None)
    args = p.parse_args()
    index_path = args.index or (INDEX if INDEX.exists() else PUBLIC_INDEX)
    data = json.loads(index_path.read_text(encoding="utf-8"))
    ranked = []
    for record in data["records"]:
        points, hits = score(record, args.query)
        if points > 0:
            ranked.append((points, record, hits))
    ranked.sort(key=lambda x: (-x[0], x[1]["name"].casefold()))
    results = []
    for points, record, hits in ranked[: max(1, args.limit)]:
        sample = (index_path.parent / record["sample_path"]).resolve()
        results.append({
            "score": round(points, 1), "matched": hits,
            "id": record["id"], "name": record["name"], "photographer": record["photographer"],
            "summary_zh": record["analysis"]["summary_zh"],
            "best_for": record["analysis"]["best_for"], "avoid_when": record["analysis"]["avoid_when"],
            "sample_path": str(sample) if sample.is_file() else None,
            "sample_status": "available" if sample.is_file() else "run sync_nikon_recipe_catalog.py and build_nikon_style_index.py",
            "source_page": record["source_page"],
        })
    if args.json:
        print(json.dumps(results, ensure_ascii=False, indent=2))
    else:
        print(f"查询：{args.query}（返回 {len(results)} 条）")
        for i, item in enumerate(results, 1):
            sample_text = item["sample_path"] or f"未同步（{item['sample_status']}）"
            print(f"\n{i}. {item['name']} — {item['photographer']}  [score {item['score']}]\n   {item['summary_zh']}\n   适用：{item['best_for']}\n   避免：{item['avoid_when']}\n   样张：{sample_text}\n   来源：{item['source_page']}")


if __name__ == "__main__":
    main()
