#!/usr/bin/env python3
"""Create local session state without silently discarding rollback data."""
import argparse
import json
from datetime import datetime, timezone
from pathlib import Path


def initialize(workspace: Path, replace_finished: bool = False) -> Path:
    workspace = workspace.expanduser().resolve(strict=True)
    if not workspace.is_dir():
        raise ValueError(f"Workspace is not a directory: {workspace}")
    state = workspace / ".photo-grade"
    if state.is_symlink():
        raise ValueError("The state directory must not be a symbolic link.")
    state.mkdir(exist_ok=True)
    current = state / "current"
    if current.is_symlink():
        raise ValueError("The session directory must not be a symbolic link.")
    if current.exists():
        manifest_path = current / "manifest.json"
        if manifest_path.is_symlink():
            raise ValueError("The manifest must not be a symbolic link.")
        manifest = json.loads(manifest_path.read_text(encoding="utf-8-sig"))
        if not isinstance(manifest, dict) or manifest.get("status") not in {"completed", "rolled_back"}:
            raise ValueError("Existing session may need rollback; complete or roll it back first.")
        if not replace_finished:
            raise ValueError("Finished session retained for rollback. Use --replace-finished only when it is no longer needed.")
        # Preserve even an explicitly replaced session instead of deleting it.
        archive = state / ("previous-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ"))
        current.rename(archive)
    current.mkdir()
    (current / "before").mkdir()
    (current / "after").mkdir()
    now = datetime.now(timezone.utc).isoformat()
    manifest = dict(schema_version=1, status="planned", created_at=now, updated_at=now,
                    selected_count=0, photos=[], applied_photo_ids=[], errors=[])
    (current / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    (current / "style-intent.md").write_text("# Style intent\n\n", encoding="utf-8")
    return current


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", required=True, type=Path)
    parser.add_argument("--replace-finished", action="store_true",
                        help="Archive a completed/rolled-back session and start another")
    args = parser.parse_args()
    try:
        print(initialize(args.workspace, args.replace_finished))
    except (OSError, ValueError) as exc:
        parser.exit(1, f"Initialization failed: {exc}\n")


if __name__ == "__main__":
    main()
