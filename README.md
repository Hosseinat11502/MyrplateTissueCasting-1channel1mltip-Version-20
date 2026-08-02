# myrPlate Tissue Casting — Opentrons Flex Protocol (V20)

Automated dispensing of cell-laden collagen master mix into a 48-well **myrPlate**
(`myrplate_48_wellplate_800ul`) using an Opentrons **Flex** with a single-channel
1000 µL pipette. Each tip aspirates once from a user-selected well of a NEST 2 mL
96-well deep-well source plate and dispenses into one 4-well column segment of the
myrPlate, tracing a small ellipse per well to reduce bubble/edge artifacts.

📄 **Preprint / manuscript:** `[DOI or bioRxiv link — add once posted]`
🎥 **Video of a live run:** `[YouTube/Figshare link — add once filmed]`

---

## What it does

- Operator selects **one 4-well target segment** on the myrPlate (`A1`–`A6` fills
  rows A–D of that column; `E1`–`E6` fills rows E–H) and **one source well**
  (`A1`–`H12`) on the D2 deep-well plate.
- One tip aspirates enough volume for all 4 target wells in a single draw
  (`volume_per_well × 4 + pre_wet_volume`), performs a reverse pre-wet to clear
  trapped air, then dispenses into each of the 4 wells along an ellipse path.
- Fresh tip and single aspirate per run — no cross-contamination between segments.

## Requirements

- Opentrons **Flex**, API level `2.18`
- `flex_1channel_1000` pipette (left mount)
- `opentrons_flex_96_tiprack_1000ul` at **C2**
- `myrplate_48_wellplate_800ul` at **D3**
- `nest_96_wellplate_2ml_deep` at **D2**
- Trash bin at **A3**

## Runtime parameters (set in the Opentrons App before each run)

| Parameter | Default | Description |
|---|---|---|
| `target_segment` | `A4` | Top well of the 4-well column segment to fill (A1–A6 → rows A–D; E1–E6 → rows E–H) |
| `source_well` | `B2` | Well on the D2 deep-well plate to aspirate from |
| `aspirate_rate_uLs` | 30 | Absolute aspirate flow rate (µL/s) |
| `dispense_rate_uLs` | 60 | Absolute dispense flow rate (µL/s) |
| `z_height` | 0.5 mm | Dispense height from well bottom |
| `travel_height_mm` | 15 mm | Clearance height over the plate |
| `pre_wet_volume` | 10 µL | Reverse pre-wet volume to clear the air lock |
| `num_points` | 10 | Ellipse points per well (before overlap sweeps) |
| `overlap` | 2 | Extra full sweeps around the ellipse (0 = single pass) |
| `volume_per_well` | 193 µL | Dispense volume per myrPlate well |

## Estimated run time

Based purely on the protocol's own declared flow rates and built-in delays
(aspirate action + 2 s settle, reverse pre-wet + 1 s settle, touch-tip, tip
pickup/drop, and the 4-well dispense loop at default parameters):

**≈ 60–70 seconds of pipetting action** (excludes Flex homing/deck-scan and
gantry travel time, which the app adds on top). This is a lower-bound estimate,
not a measured value.

> **TODO:** replace with the actual run time from the Opentrons App run summary
> after filming, e.g. *"Total run time: Xm Ys (measured, N=1, \[date])."*

## Usage

1. Load labware in the slots above; load the D2 source well(s) with ≥
   `volume_per_well × 4 + pre_wet_volume + 100` µL of master mix.
2. Upload `myrPlate_tissue_casting-1Ch1ml_V20.py` in the Opentrons App.
3. Set `target_segment` and `source_well` (and any other parameters) before starting.
4. Run.

## Repo contents

```
myrPlate_tissue_casting-1Ch1ml_V20.py   # protocol
README.md
LICENSE
CITATION.cff
```

## Citation

If you use this protocol, please cite the preprint (see `CITATION.cff` — update
the DOI once assigned) and/or this repository.

## License

MIT — see `LICENSE`. Change this before publishing if your institution requires
a different license.
