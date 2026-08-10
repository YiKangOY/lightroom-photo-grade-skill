# Strict color-edit contract

Every write must be a partial update containing only keys from this allowlist. Preserve all other Lightroom settings.

## Allowed global keys

- `WhiteBalance`
- `Temperature`
- `Tint`
- `Exposure2012`
- `Contrast2012`
- `Highlights2012`
- `Shadows2012`
- `Whites2012`
- `Blacks2012`
- `Vibrance`
- `Saturation`
- `ParametricShadows`
- `ParametricDarks`
- `ParametricLights`
- `ParametricHighlights`

`WhiteBalance` may remain unchanged or be set to `Custom`; do not switch to another named preset automatically.

## Allowed HSL keys

Lightroom MCP exposes HSL as flattened develop keys. Use only keys formed from these axes and colors:

- axes: `HueAdjustment`, `SaturationAdjustment`, `LuminanceAdjustment`
- colors: `Red`, `Orange`, `Yellow`, `Green`, `Aqua`, `Blue`, `Purple`, `Magenta`

Examples: `HueAdjustmentRed`, `SaturationAdjustmentAqua`, `LuminanceAdjustmentBlue`.

The proposal validator still accepts the legacy nested `HSL` object for existing saved sessions, but new proposals and MCP writes must use the flattened keys.

## Validation bounds

| Setting | Absolute bounds | Maximum change from baseline |
|---|---:|---:|
| Exposure2012 | -5 to 5 | 1.25 |
| Contrast2012 | -100 to 100 | 50 |
| Highlights2012, Shadows2012 | -100 to 100 | 60 |
| Whites2012, Blacks2012 | -100 to 100 | 50 |
| Vibrance | -100 to 100 | 35 |
| Saturation | -100 to 100 | 30 |
| Tint | -150 to 150 | 25 |
| Parametric tone values | -100 to 100 | 40 |
| Every HSL channel | -100 to 100 | 35 |

For `Temperature`, detect the scale from the baseline. If its absolute value is greater than 500, require 2000–50000 K and a maximum delta of 2500 K. Otherwise require -100–100 and a maximum delta of 35 for raw sources or 20 for rendered sources.

The validator is a last safety gate, not an aesthetic target. Prefer smaller moves when they achieve the intent.
