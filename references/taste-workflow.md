# Taste and workflow rules

## Precedence

Resolve conflicts in this order:

1. Hard safety rules and the strict Lightroom allowlist.
2. The user's explicit instruction for the current task.
3. A relevant genre taste file.
4. The default taste file.

Taste is guidance, not a preset. Translate it into per-photo decisions after inspecting the actual images.

## Reference interpretation

When a reference image is present, describe it semantically before proposing values:

- exposure placement and highlight rolloff;
- black-point depth and shadow openness;
- global contrast character;
- white-balance direction and neutral treatment;
- skin, foliage, sky, and other dominant color relationships;
- saturation hierarchy rather than total saturation alone.

Do not perform literal pixel, histogram, or parameter transfer. Different capture conditions require different final Lightroom values.

## Lightweight session state

Use only `<workspace>\.photo-grade\current`:

- `manifest.json`: selection, status, timestamps, applied-photo list, errors;
- `proposal.json`: baseline values and proposed absolute settings;
- `style-intent.md`: short explanation of the intended look;
- `before\` and `after\`: exported previews for visual review.

Reject duplicate case-insensitive basenames. This keeps preview matching deterministic without a mapping database. The directory represents one task only. Do not overwrite a session whose status indicates that edits may need rollback.

Suggested states are `planned`, `pilot_applied`, `pilot_approved`, `batch_applied`, `completed`, and `rolled_back`.

## Taste learning

Taste files contain durable preferences, not session logs. At the end of a successful or corrected grade:

1. Summarize what the user's feedback implies.
2. Propose zero, one, or two reusable statements.
3. Ask for confirmation.
4. Append only the confirmed statements, with a date.

Avoid adding image-specific facts, Lightroom parameter values, filenames, or transient corrections to a taste file.
