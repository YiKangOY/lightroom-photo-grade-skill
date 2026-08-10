# Lightroom Photo Grade Skill

A personal Codex skill for safely grading the current Adobe Lightroom Classic
selection through Lightroom MCP. It combines:

- a confirmed, prose-based personal taste layer;
- a strict Lightroom color-only write contract;
- pilot-first approval and deterministic rollback;
- a searchable reference layer derived from public Nikon Imaging Cloud recipes.

## Nikon reference library

The repository currently indexes 142 public recipes attributed to 66 creators.
The bundled public index contains only recipe identity, source links, and
non-official workflow interpretations. It excludes official descriptions,
Picture Control parameters, signed URLs, camera metadata, hashes, and display
images. Users may run the synchronization and build scripts locally when they
need the complete visual-reference workflow.

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
- `scripts/Test-PhotoGradeProposal.ps1` — strict proposal validator

## Example search

```powershell
python scripts/find_nikon_recipe.py "RED 冷调电影感人像" --limit 5
```

## Validation

```powershell
python -m py_compile scripts/sync_nikon_recipe_catalog.py scripts/build_nikon_style_index.py scripts/find_nikon_recipe.py
powershell -File scripts/Test-PhotoGradeProposal.ps1 -Path <proposal.json>
```

## Rights and provenance

Nikon recipe names remain the property of their respective owners and are used
only for identification and source attribution. Official descriptions, Picture
Control metadata, and display samples are not distributed in this repository.
The workflow interpretations are non-official and must not be presented as
statements by Nikon or the named creators.

Source catalog: <https://imagingcloud.nikon.com.cn/recipe/release/?bookId=01HXDNNTHY1AZ6RVMMXSXY3BTK>
