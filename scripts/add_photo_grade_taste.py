#!/usr/bin/env python3
"""Append an already-confirmed preference to ~/.photo-grade/tastes."""
import argparse
import re
from datetime import date
from pathlib import Path


def append_taste(taste_file: str, entry: str) -> str:
    if not re.fullmatch(r"[A-Za-z0-9_-]+\.md", taste_file):
        raise ValueError("Taste file must be a plain Markdown filename, e.g. portrait.md.")
    clean = re.sub(r"[\r\n]+", " ", entry).strip()
    if not clean:
        raise ValueError("Taste entry is empty.")
    root = Path.home() / ".photo-grade" / "tastes"
    if (Path.home() / ".photo-grade").is_symlink() or root.is_symlink():
        raise ValueError("Taste directories must not be symbolic links.")
    root.mkdir(parents=True, exist_ok=True)
    target = root / taste_file
    if target.is_symlink():
        raise ValueError("Taste file must not be a symbolic link.")
    existing = target.read_text(encoding="utf-8-sig") if target.exists() else "# Confirmed taste\n\n"
    if clean in existing:
        return f"Already present: {target}"
    with target.open("w", encoding="utf-8") as stream:
        stream.write(existing.rstrip() + f"\n\n- {date.today().isoformat()}: {clean}\n")
    return f"Appended confirmed taste: {target}"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--taste-file", required=True)
    parser.add_argument("--entry", required=True)
    args = parser.parse_args()
    try:
        print(append_taste(args.taste_file, args.entry))
    except (OSError, ValueError) as exc:
        parser.exit(1, f"Taste update failed: {exc}\n")


if __name__ == "__main__":
    main()
