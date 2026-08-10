#!/usr/bin/env python3
"""Synchronize Nikon Imaging Cloud's public recipe catalog at a polite rate."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


CATALOG_URL = "https://api.user.cwp.imagingcloud.nikon.com.cn/bff/recipe/release"
USERINFO_URL = "https://api.user.ir.imagingcloud.nikon.com.cn/info/userinfo"
DETAIL_URL = "https://api.user.ir.imagingcloud.nikon.com.cn/publicrecipe/{owner}/{recipe_id}?sortType=0&isPagenation=false"
SOURCE_PAGE = "https://imagingcloud.nikon.com.cn/recipe/release/?bookId={book_id}"
DETAIL_PAGE = "https://imagingcloud.nikon.com.cn/recipe/release/detail/?id={recipe_id}&sortType=0&recipe_lang=zh-cn"
DEFAULT_BOOK_ID = "01HXDNNTHY1AZ6RVMMXSXY3BTK"
USER_AGENT = "photo-grade-nikon-public-catalog/1.0 (personal reference sync)"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--skill-root", type=Path, required=True)
    parser.add_argument("--book-id", default=DEFAULT_BOOK_ID)
    parser.add_argument("--delay", type=float, default=1.25, help="Seconds between requests")
    parser.add_argument("--max-items", type=int, default=0, help="0 means the complete public catalog")
    parser.add_argument("--refresh", action="store_true", help="Refresh existing detail JSON and samples")
    return parser.parse_args()


def atomic_write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_bytes(data)
    temporary.replace(path)


def write_json(path: Path, value: Any) -> None:
    atomic_write(path, (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))


class PoliteClient:
    def __init__(self, delay: float) -> None:
        if delay < 0.5:
            raise ValueError("Delay must be at least 0.5 seconds")
        self.delay = delay
        self.last_request = 0.0

    def _wait(self) -> None:
        remaining = self.delay - (time.monotonic() - self.last_request)
        if remaining > 0:
            time.sleep(remaining)

    def request(self, url: str, *, method: str = "GET", body: dict[str, Any] | None = None) -> bytes:
        payload = None if body is None else json.dumps(body, ensure_ascii=False).encode("utf-8")
        headers = {
            "User-Agent": USER_AGENT,
            "Accept-Language": "zh-cn",
            "Origin": "https://imagingcloud.nikon.com.cn",
            "Referer": "https://imagingcloud.nikon.com.cn/",
        }
        if payload is not None:
            headers["Content-Type"] = "application/json"
            headers["access_token"] = "null"
        for attempt in range(4):
            self._wait()
            try:
                request = urllib.request.Request(url, data=payload, headers=headers, method=method)
                with urllib.request.urlopen(request, timeout=45) as response:
                    result = response.read()
                self.last_request = time.monotonic()
                return result
            except (urllib.error.URLError, TimeoutError) as exc:
                self.last_request = time.monotonic()
                if attempt == 3:
                    raise RuntimeError(f"Request failed after retries: {url}") from exc
                time.sleep(2 ** attempt)
        raise AssertionError("unreachable")

    def json(self, url: str, *, method: str = "GET", body: dict[str, Any] | None = None) -> Any:
        return json.loads(self.request(url, method=method, body=body).decode("utf-8"))


def photographer_from_name(name: str) -> str:
    match = re.search(r"\s+by\s+(.+)$", name, flags=re.IGNORECASE)
    return match.group(1).strip() if match else "Nikon"


def compact_detail(detail: dict[str, Any], image_path: str, sha256: str) -> dict[str, Any]:
    return {
        "id": detail.get("id"),
        "name": detail.get("name"),
        "photographer": photographer_from_name(detail.get("name", "")),
        "public_date": detail.get("publicDate"),
        "official_outline": detail.get("recipeOutline") or "",
        "official_description": detail.get("recipeDetail") or "",
        "picture_control_name": detail.get("pictureControlName") or "",
        "picture_control": detail.get("pictureControl") or {},
        "tags": detail.get("tags") or [],
        "camera": detail.get("camera") or "",
        "lens": detail.get("lens") or "",
        "exif": detail.get("exif") or {},
        "sample": {
            "local_path": image_path,
            "sha256": sha256,
            "source_url": detail.get("thumbnail") or "",
        },
        "source_page": DETAIL_PAGE.format(recipe_id=detail.get("id", "")),
    }


def main() -> int:
    args = parse_args()
    skill_root = args.skill_root.resolve()
    if not (skill_root / "SKILL.md").is_file():
        raise SystemExit(f"Not a skill root: {skill_root}")

    reference_root = skill_root / "references" / "nikon-cloud"
    raw_root = reference_root / "raw"
    sample_root = skill_root / "assets" / "nikon-cloud" / "samples"
    raw_root.mkdir(parents=True, exist_ok=True)
    sample_root.mkdir(parents=True, exist_ok=True)
    client = PoliteClient(args.delay)

    user_info = client.json(USERINFO_URL)
    owner = str(user_info["nikonUserId"])
    catalog = client.json(
        CATALOG_URL,
        method="POST",
        body={
            "ownerUserId": owner,
            "bookId": args.book_id,
            "sortType": 0,
            "lang_code": "zh-cn",
            "country": "CN",
        },
    )
    recipes = list(catalog.get("recipe") or [])
    if args.max_items > 0:
        recipes = recipes[: args.max_items]
    if not recipes:
        raise RuntimeError("The public catalog returned no recipes")

    entries: list[dict[str, Any]] = []
    failures: list[dict[str, str]] = []
    total = len(recipes)
    for position, item in enumerate(recipes, start=1):
        recipe_id = str(item["id"])
        raw_path = raw_root / f"{recipe_id}.json"
        image_path = sample_root / f"{recipe_id}.jpg"
        print(f"[{position:03d}/{total:03d}] {recipe_id} {item.get('name', '')}", flush=True)
        try:
            if raw_path.exists() and not args.refresh:
                detail = json.loads(raw_path.read_text(encoding="utf-8"))
            else:
                detail = client.json(DETAIL_URL.format(owner=owner, recipe_id=recipe_id))
                write_json(raw_path, detail)

            image_url = detail.get("thumbnail") or (item.get("img") or {}).get("url")
            if not image_url:
                raise RuntimeError("No public sample image URL")
            if not image_path.exists() or args.refresh:
                image_bytes = client.request(image_url)
                if len(image_bytes) < 4096:
                    raise RuntimeError("Downloaded sample is unexpectedly small")
                atomic_write(image_path, image_bytes)
            image_bytes = image_path.read_bytes()
            image_hash = hashlib.sha256(image_bytes).hexdigest()
            local_reference = f"../../assets/nikon-cloud/samples/{image_path.name}"
            entries.append(compact_detail(detail, local_reference, image_hash))
        except Exception as exc:  # keep the crawl resumable and report every failure
            failures.append({"id": recipe_id, "name": str(item.get("name", "")), "error": str(exc)})
            print(f"  ERROR: {exc}", file=sys.stderr, flush=True)

    entries.sort(key=lambda value: (value["photographer"].casefold(), value["name"].casefold()))
    synced_at = datetime.now(timezone.utc).isoformat()
    write_json(
        reference_root / "catalog-source.json",
        {
            "schema_version": 1,
            "source": SOURCE_PAGE.format(book_id=args.book_id),
            "language": "zh-cn",
            "synced_at": synced_at,
            "expected_count": total,
            "collected_count": len(entries),
            "failure_count": len(failures),
            "entries": entries,
        },
    )
    write_json(
        reference_root / "sync-report.json",
        {
            "synced_at": synced_at,
            "expected_count": total,
            "collected_count": len(entries),
            "failures": failures,
        },
    )
    print(f"Collected {len(entries)}/{total}; failures: {len(failures)}")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
