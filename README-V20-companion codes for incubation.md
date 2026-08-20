# myrPlate V20-Asp / V20-Disp Protocols

Companion Opentrons Flex protocols for `myrPlate_tissue_casting-1Ch1ml_V20.py`.
Use these on a myrPlate that has already been cast with V20 to perform a
media exchange on one 4-well column segment at a time: aspirate spent media,
then feed fresh media.

## Files

| File | Purpose |
|---|---|
| `myrPlate_V20-Asp_aspiration.py` | Aspirates spent media from a 4-well segment, disposes into block C3, fresh tip per well |
| `myrPlate_V20-Disp_dispensing.py` | Aspirates fresh media from a 12-well reservoir and dispenses into all 4 wells of a segment |

## What matches V20

- **Single-channel pipette** (`flex_1channel_1000`, left mount) and the
  **same 4-well segment addressing** as V20 (`target_segment`, e.g. `A4`
  fills rows A/B/C/D of column 4; `E4` fills rows E/F/G/H) via the identical
  `get_target_wells()` helper.
- **Identical elliptical route**: same fixed equation as V20
  (`x = 5.5·cos(t)`, `y = 2.85·sin(t)`, not exposed as a tunable parameter,
  matching V20's own choice to keep it fixed) so both scripts stay on the
  exact path the tissue was cast along.
- **Absolute flow rates** (`aspirate_rate_uLs` / `dispense_rate_uLs`) set
  directly on `pipette.flow_rate`, and `travel_height_mm` for clearance
  moves - both carried over from V20.
- Dispensing keeps V20's **pre-wet anti-bubble handling** (aspirate extra,
  return half, touch tip) before delivering media.

## What's adapted from the original V3 / V1 protocols

- **Aspiration** keeps V3's fresh-tip-per-well and disposal-into-C3
  behavior, run once per well in the chosen 4-well segment.
- **Dispensing** keeps V1's reservoir-based media source (12-well reservoir,
  `EHMM` liquid definition), but re-aspirates with the same tip before each
  of the 4 wells rather than batching all 4 into one aspiration - a full
  media volume (up to 485 µL/well) doesn't fit 4 wells in a single 1000 µL
  tip the way V20's smaller 200 µL casting volume does.

## Requirements

- Opentrons Flex, API level 2.18
- `flex_1channel_1000` pipette, left mount
- `opentrons_flex_96_tiprack_1000ul` in slot C2
- `myrplate_48_wellplate_800ul` in slot D3
- Aspiration: `nest_1_reservoir_195ml` (waste) in slot C3, trash bin in A3
- Dispensing: `nest_12_reservoir_15ml` (media) in slot D2, trash bin in A3

## Typical workflow

1. Cast a 4-well segment with `myrPlate_tissue_casting-1Ch1ml_V20.py`
   (repeat per segment as needed).
2. On your media-exchange schedule, run `myrPlate_V20-Asp_aspiration.py`
   with the matching `target_segment` to remove spent media.
3. Run `myrPlate_V20-Disp_dispensing.py` with the same `target_segment` to
   feed fresh media.
4. Repeat per segment, per exchange.
