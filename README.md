# Lightroom Photo Grade Skill

A personal Codex skill for safely grading the current Adobe Lightroom Classic
selection through Lightroom MCP. It combines:

- a confirmed, prose-based personal taste layer;
- a strict Lightroom color-only write contract;
- pilot-first approval and deterministic rollback;
- a searchable reference layer derived from public Nikon Imaging Cloud recipes.

## macOS setup

Requires Python 3.9+ (`python3 --version`), Adobe Lightroom **Classic**, and a
separately installed Lightroom MCP plug-in/server connected to your agent. The
cloud-based Lightroom app is not a substitute. This repository does not bundle
the MCP bridge or configure a server endpoint; follow your bridge's macOS setup
instructions and verify that selection reads, preview exports, and partial
develop-setting updates work before grading.

Install the skill in your personal Codex skills folder (choose another directory
if `photo-grade` already exists):

```sh
mkdir -p "$HOME/.codex/skills"
git clone https://github.com/YiKangOY/lightroom-photo-grade-skill.git "$HOME/.codex/skills/photo-grade"
cd "$HOME/.codex/skills/photo-grade"
```

Seed personal taste files without overwriting existing preferences:

```sh
mkdir -p "$HOME/.photo-grade/tastes"
for source in assets/tastes/*.md; do
  target="$HOME/.photo-grade/tastes/$(basename "$source")"
  if [ ! -e "$target" ]; then cp "$source" "$target"; fi
done
```

Restart Codex if the installed skill does not appear. Invoke `$photo-grade` or
“用 skill 调色” with Lightroom Classic open and the intended 4/5-star photos
selected. The workflow still requires approval of the first photo and approval
before applying the remaining batch.

The core helpers and bundled recipe search use only Python's standard library.
They handle macOS paths, spaces, and Chinese filenames without PowerShell:

```sh
python3 scripts/initialize_photo_grade_workspace.py --workspace "/Users/you/Pictures/调色项目"
python3 scripts/validate_photo_grade_proposal.py --path "/Users/you/Pictures/调色项目/.photo-grade/current/proposal.json"
# Only after the user confirms this durable preference:
python3 scripts/add_photo_grade_taste.py --taste-file portrait.md --entry "保留自然肤色，避免橙色过饱和。"
```

The workspace must already exist. Initialization refuses to overwrite existing
sessions, including unfinished batches. After a session is `completed` or
`rolled_back`, pass `--replace-finished` only when its rollback is no longer
needed; the old directory is moved to `.photo-grade/previous-<UTC timestamp>`
instead of deleted. Personal tastes live in `~/.photo-grade/tastes/`, while
per-task previews and rollback data live in `<workspace>/.photo-grade/current/`.
The original `.ps1` scripts remain for existing Windows users; macOS uses the
Python helpers described above.

### Optional full Nikon reference library

Only building the full index from local samples needs Pillow. Use a virtual
environment so the system Python stays untouched:

```sh
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -r requirements.txt
python3 scripts/sync_nikon_recipe_catalog.py --skill-root .
python3 scripts/build_nikon_style_index.py
```

The sync command makes network requests and downloads public reference material.
It is optional; searching the bundled public index works offline without Pillow.

## Nikon reference library

The repository currently indexes 142 public recipes attributed to 66 creators.
The bundled public index contains only recipe identity, source links, and
non-official workflow interpretations. It excludes official descriptions,
Picture Control parameters, signed URLs, camera metadata, hashes, and display
images.

### Obtain the complete local reference set

The full set currently consists of 142 Nikon display samples plus their public
official descriptions. These third-party materials are intentionally not
redistributed or stored in this repository's Git history. Obtain them yourself
from the linked Nikon Imaging Cloud / Nikon Cloud Creation public recipe pages,
subject to the source site's terms and applicable law, then run
`scripts/sync_nikon_recipe_catalog.py` and
`scripts/build_nikon_style_index.py` locally. The resulting samples and full
index stay ignored by Git; the skill automatically prefers that local full
index and falls back to the bundled public index when it is absent.

The workflow never copies Nikon Picture Control values directly into Lightroom.
It searches candidates, visually inspects the best official samples, selects by
compatibility with the source photograph, and translates only the relevant color
relationships into per-photo Lightroom settings.

## Main files

- `SKILL.md` — operating instructions and safety contract
- `references/nikon-cloud/public-style-index.json` — redistribution-conscious recipe interpretations
- `references/nikon-cloud/catalog.md` — human-readable creator catalog
- `scripts/export_public_nikon_index.py` — create the public discovery index
- `scripts/find_nikon_recipe.py` — ranked style search
- `scripts/build_nikon_style_index.py` — deterministic index generation
- `scripts/sync_nikon_recipe_catalog.py` — rate-limited, resumable public-data sync
- `scripts/validate_photo_grade_proposal.py` — cross-platform strict proposal validator
- `scripts/initialize_photo_grade_workspace.py` — session initialization and rollback retention
- `scripts/add_photo_grade_taste.py` — append confirmed preferences

## Example search

```sh
python3 scripts/find_nikon_recipe.py "RED 冷调电影感人像" --limit 5
```

## Validation

```sh
python3 -m compileall -q scripts
python3 -m unittest discover -s tests -v
python3 scripts/validate_photo_grade_proposal.py --path "/path/to/proposal.json"
```

## Rights and provenance

Nikon recipe names remain the property of their respective owners and are used
only for identification and source attribution. Official descriptions, Picture
Control metadata, and display samples are not distributed in this repository.
The workflow interpretations are non-official and must not be presented as
statements by Nikon or the named creators.

Source catalog: <https://imagingcloud.nikon.com.cn/recipe/release/>
