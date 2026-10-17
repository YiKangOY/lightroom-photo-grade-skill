#!/usr/bin/env python3
"""Validate absolute Lightroom color settings and their rollback baselines."""
import argparse
import json
import math
from pathlib import Path

RULES = {
    "Exposure2012": (-5, 5, 1.25), "Contrast2012": (-100, 100, 50),
    "Highlights2012": (-100, 100, 60), "Shadows2012": (-100, 100, 60),
    "Whites2012": (-100, 100, 50), "Blacks2012": (-100, 100, 50),
    "Vibrance": (-100, 100, 35), "Saturation": (-100, 100, 30),
    "Tint": (-150, 150, 25),
    **{f"Parametric{x}": (-100, 100, 40) for x in ("Shadows", "Darks", "Lights", "Highlights")},
}
COLORS = ("Red", "Orange", "Yellow", "Green", "Aqua", "Blue", "Purple", "Magenta")
HSL_KEYS = {f"{axis}Adjustment{color}" for axis in ("Hue", "Saturation", "Luminance") for color in COLORS}
ALLOWED = set(RULES) | HSL_KEYS | {"WhiteBalance", "Temperature", "HSL"}


def finite(value):
    return type(value) in (int, float) and (not isinstance(value, float) or math.isfinite(value))


def validate(document):
    errors = []
    photos = document.get("photos") if isinstance(document, dict) else None
    if not isinstance(photos, list) or not 1 <= len(photos) <= 100:
        return ["photos must be an array containing 1–100 items."]
    seen = set()

    def check(label, old, new, bounds):
        if not finite(old) or not finite(new):
            errors.append(f"{label} requires finite numeric baseline and proposed values.")
            return
        low, high, delta = bounds
        if not low <= new <= high or abs(new - old) > delta:
            errors.append(f"{label} exceeds its bound or delta limit.")

    for photo in photos:
        if not isinstance(photo, dict):
            errors.append("Every photo must be an object.")
            continue
        photo_id = photo.get("photo_id")
        if type(photo_id) not in (str, int) or not str(photo_id).strip():
            errors.append("Every photo requires a string or integer photo_id.")
            continue
        identity = str(photo_id).casefold()
        if identity in seen:
            errors.append(f"Duplicate photo_id: {photo_id}")
        seen.add(identity)
        baseline, proposed = photo.get("baseline_develop"), photo.get("proposed_settings")
        if not isinstance(baseline, dict) or not isinstance(proposed, dict) or not proposed:
            errors.append(f"{photo_id} requires baseline_develop and nonempty proposed_settings objects.")
            continue
        for key, new in proposed.items():
            label = f"{photo_id} {key}"
            if key not in ALLOWED:
                errors.append(f"{label} is forbidden.")
                continue
            if key not in baseline:
                errors.append(f"{label} has no baseline value.")
                continue
            old = baseline[key]
            if key == "WhiteBalance":
                if not isinstance(old, str) or not isinstance(new, str) or (new != old and new != "Custom"):
                    errors.append(f"{label} must stay unchanged or be Custom, with a string baseline.")
            elif key == "HSL":
                # Read legacy sessions; all new MCP writes must use flat keys.
                if not isinstance(old, dict) or not isinstance(new, dict) or not new:
                    errors.append(f"{label} requires nonempty HSL objects.")
                    continue
                for axis, channels in new.items():
                    old_axis = old.get(axis)
                    if axis not in {"Hue", "Saturation", "Luminance"} or not isinstance(channels, dict) or not channels or not isinstance(old_axis, dict):
                        errors.append(f"{label}.{axis} is invalid or has no baseline object.")
                        continue
                    for color, value in channels.items():
                        if color not in COLORS or color not in old_axis:
                            errors.append(f"{label}.{axis}.{color} is invalid or has no baseline.")
                        else:
                            check(f"{label}.{axis}.{color}", old_axis[color], value, (-100, 100, 35))
            elif key == "Temperature":
                if not finite(old):
                    errors.append(f"{label} requires a finite numeric baseline.")
                    continue
                bounds = (2000, 50000, 2500) if abs(old) > 500 else (-100, 100, 35 if str(photo.get("source_type", "")).lower() == "raw" else 20)
                check(label, old, new, bounds)
            else:
                check(label, old, new, (-100, 100, 35) if key in HSL_KEYS else RULES[key])
    return errors


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--path", required=True, type=Path)
    args = parser.parse_args()
    try:
        document = json.loads(args.path.expanduser().read_text(encoding="utf-8-sig"))
        errors = validate(document)
    except (OSError, ValueError) as exc:
        parser.exit(1, f"Cannot read proposal: {exc}\n")
    if errors:
        parser.exit(1, "Proposal validation failed:\n" + "\n".join(f"- {e}" for e in errors) + "\n")
    print(f"Proposal valid: {len(document['photos'])} photo(s), strict color contract satisfied.")


if __name__ == "__main__":
    main()
