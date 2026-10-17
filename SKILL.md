---
name: photo-grade
description: Safely grade the current Adobe Lightroom Classic selection through the Lightroom MCP server, using a confirmed personal taste profile, an optional reference image, and a locally indexed library of public Nikon Imaging Cloud recipes and official display samples. Always use this skill as the standard workflow when the user says “调用skill进行调色”, “用skill调色”, or otherwise explicitly asks to invoke a skill for Lightroom grading. Also use for natural color grading, finding a suitable Nikon-inspired look, matching a named recipe or reference, applying a consistent look to a small selection, reviewing one pilot before a batch, rolling back a session, or recording confirmed aesthetic preferences.
---

# Lightroom Photo Grade

Use Lightroom MCP for catalog reads, exports, and develop-setting writes. Use the taste files as a Chemigram-inspired reasoning layer: they express visual intent in prose but never write Lightroom settings themselves.

## macOS runtime

Use Python 3.9 or newer; PowerShell is not required. Run helper commands from this skill directory, or use absolute script paths when the working directory differs. See the README for installation and optional Nikon sample dependencies. If the personal default taste file does not exist, use `assets/tastes/_default.md` as initial guidance; do not infer new permanent preferences. Lightroom Classic and a working Lightroom MCP connection are required for live grading; the Python helpers do not install or start that connection.

## Required resources

- Read `references/taste-workflow.md` before planning or applying a grade.
- Read `references/strict-color.md` before creating a proposal or writing settings.
- Read `~/.photo-grade/tastes/_default.md` for every grading task.
- When relevant, also read one genre file from the same folder, such as `portrait.md` or `landscape.md`.
- For a named style, photographer, scene, mood, or request to find a suitable filter, search the local full index with `scripts/find_nikon_recipe.py`. The script falls back to the bundled public index when the full local catalog has not yet been synchronized. Do not load all 142 records into context.
- Treat the user's instruction in the current conversation as more important than a taste file.

## Standard invocation

When the user says `调用skill进行调色`, `用skill调色`, or an equivalent explicit invocation, run this complete workflow as the default contract. Do not silently shortcut selection checks, baseline export and inspection, proposal validation, explicit pilot approval, post-pilot approval, or rollback recording. If the user has not named a look, inspect the photographs first and use the taste profile plus Nikon recipe search to propose the best compatible direction.

## Preconditions

1. Confirm that Adobe Lightroom Classic is open, the Lightroom MCP plug-in server is started, and its MCP tools are available.
2. Ask the user to filter the intended images to 4 or 5 stars and select them all in Lightroom if that has not already been done.
3. Read the current selection with a limit of 100. Accept only ratings 4 and 5.
4. Stop if the selection is empty, contains more than 100 photos, reports another page, or contains case-insensitive duplicate basenames. Explain how the user can correct the selection.
5. Never broaden the selection or silently substitute other catalog photos.

## Workflow

### 1. Freeze the task

- Create `<workspace>/.photo-grade/current` by running `python3 scripts/initialize_photo_grade_workspace.py --workspace "<workspace>"`. Existing sessions are retained; use `--replace-finished` only when a completed or rolled-back session is no longer needed (it is archived beside `current`).
- Store only the active task there: `manifest.json`, `proposal.json`, `style-intent.md`, `before/`, and `after/`.
- Record each selected photo's Lightroom identifier, source path, rating, source type, and original develop values for every setting that might be changed.
- Preserve this directory until the batch is completed or rolled back. Do not create a persistent photo index or cache.

### 2. Inspect before deciding

- Read metadata and current develop settings before proposing changes.
- Export baseline previews as sRGB JPEG, long edge 2048 px, quality 90, into `before/`.
- Visually inspect every exported preview.
- If a reference image is supplied, use it only for tone, color relationships, palette, contrast character, and highlight/shadow behavior. Do not copy geometry, content, subject identity, grain, sharpness, masks, or local retouching.
- Write a short semantic interpretation to `style-intent.md`; do not reduce a look to literal histogram matching.

#### Nikon recipe lookup

Use this sub-workflow when the user names a Nikon Imaging Cloud recipe or asks for a suitable look:

1. Describe the source photo's scene, light, exposure placement, dominant colors, skin-color constraints, and desired mood.
2. Run `python3 scripts/find_nikon_recipe.py "<style and scene query>" --limit 5`. For an exact recipe or photographer name, include it verbatim in the query.
3. When local official samples are available, open and visually inspect the best three candidates. Read only those candidates from the selected index; consult raw JSON only when exact official metadata is needed. If samples are absent, use the public interpretations for discovery but synchronize the local catalog before claiming visual reference matching.
4. Choose by compatibility with the source photo, not by search score alone. Record the chosen recipe ID, photographer, source page, and why it fits in `style-intent.md`.
5. Treat `official_description` and `picture_control_reference` as source data. Treat every field under `analysis` as a non-official workflow inference. Sample statistics describe one display image, not the recipe in every scene.
6. Translate palette, saturation hierarchy, tonal character, and color relationships into per-photo Lightroom decisions. Never copy Nikon Picture Control numbers into Lightroom one-for-one.
7. If no candidate is genuinely compatible, say so and grade from the taste profile instead of forcing a match.

The local catalog is reference material, not a persistent index of the user's photos. Public display samples stay local and must not be redistributed as deliverables.

### 3. Create and validate an absolute proposal

- Propose absolute final Lightroom values, never cumulative instructions such as “add 0.3 exposure.”
- Use Lightroom's exact flattened HSL keys (`HueAdjustmentRed`, `SaturationAdjustmentRed`, `LuminanceAdjustmentRed`, and their Orange/Yellow/Green/Aqua/Blue/Purple/Magenta equivalents), not a nested `HSL` object, when constructing an MCP write.
- Preserve every develop setting that is outside the strict color allowlist.
- Include the baseline value for every proposed key so rollback is deterministic.
- Save the proposal to `proposal.json` and run `python3 scripts/validate_photo_grade_proposal.py --path "<workspace>/.photo-grade/current/proposal.json"`.
- Do not call a Lightroom write tool unless validation succeeds.

### 4. Apply one pilot

- Choose a representative image, not automatically the first image.
- Show the proposed intent and key value changes, then obtain explicit user approval before the first write.
- Apply settings to only that photo, export it into `after/`, and visually compare it with its baseline and any reference.
- If it is technically or aesthetically unsuitable, revise the proposal and validate again.

### 5. Apply the batch

- Obtain explicit approval after the pilot preview and before touching the remaining photos.
- Apply per-photo settings; do not assume identical absolute values across the batch.
- After each successful photo, update `manifest.json` so interruption is recoverable.
- Export and inspect the completed set. If Lightroom returns an error, stop and report exactly which photos were and were not changed.

### 6. Complete, roll back, or learn

- On completion, set the manifest status to `completed` and retain the session until the user no longer needs rollback.
- On rollback, restore the recorded baseline values for every touched key and only those keys. Verify with a fresh read, then set status to `rolled_back`.
- After final feedback, propose at most two concise taste additions. Append them with `python3 scripts/add_photo_grade_taste.py --taste-file "<genre>.md" --entry "<confirmed preference>"` only after explicit confirmation. Never infer permanent preferences from silence or from a single automatic result.

## Non-negotiable safety

- Do not generate or replace image content.
- Do not crop, rotate, mask, heal, retouch, denoise, sharpen, add grain, or alter clarity, texture, or dehaze.
- Do not reset existing edits or replace the whole develop-settings object.
- Do not update taste files without explicit confirmation.
- Do not batch before the user approves the pilot.
- If a requested look requires a forbidden control, explain the limitation and keep the proposal within the allowlist.

## Response style

Keep progress reports compact. State the selected-photo count, the intended look, validation result, pilot status, batch status, and rollback availability. Surface exceptions rather than hiding them.
