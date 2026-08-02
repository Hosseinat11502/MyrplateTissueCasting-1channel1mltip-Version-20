# -*- coding: utf-8 -*-

from opentrons import protocol_api
import numpy as np
from opentrons.types import Point

metadata = {
    "protocolName": "myrPlate cast v20",
    "description": "Deep-well D2 source (selectable well), fills one 4-well column segment of myrPlate per run",
    "author": "HGH"
}
requirements = {"robotType": "Flex", "apiLevel": "2.18"}


def _target_segment_choices():
    """A1..A6 (fills A/B/C/D of that column) and E1..E6 (fills E/F/G/H)."""
    choices = []
    for row in ("A", "E"):
        for col in range(1, 7):
            name = f"{row}{col}"
            choices.append({"display_name": name, "value": name})
    return choices


def _source_well_choices():
    """All 96 wells of the NEST deep-well plate at D2: A1..H12."""
    choices = []
    for col in range(1, 13):
        for row in "ABCDEFGH":
            name = f"{row}{col}"
            choices.append({"display_name": name, "value": name})
    return choices


def add_parameters(parameters: protocol_api.Parameters):
    parameters.add_str(
        variable_name="target_segment",
        display_name="Target well segment",
        description=(
            "Top well of the 4-well column segment to fill on the myrPlate. "
            "A1-A6 fills rows A,B,C,D of that column; E1-E6 fills rows E,F,G,H."
        ),
        choices=_target_segment_choices(),
        default="A4",
    )

    parameters.add_str(
        variable_name="source_well",
        display_name="D2 source well",
        description="Which well of the D2 deep-well plate to aspirate master mix from",
        choices=_source_well_choices(),
        default="B2",
    )

    parameters.add_float(
        variable_name="aspirate_rate_uLs",
        display_name="Aspirate rate (uL/s)",
        description="Absolute aspirate flow rate",
        default=30,
        minimum=5,
        maximum=200,
        unit="uL/s"
    )

    parameters.add_float(
        variable_name="dispense_rate_uLs",
        display_name="Dispense rate (uL/s)",
        description="Absolute dispense flow rate",
        default=60,
        minimum=5,
        maximum=200,
        unit="uL/s"
    )

    parameters.add_float(
        variable_name="z_height",
        display_name="Z height",
        description="Dispense height from bottom",
        default=0.5,
        minimum=0.00,
        maximum=15.00,
        unit="mm"
    )

    parameters.add_float(
        variable_name="travel_height_mm",
        display_name="Travel height",
        description="Clearance over the plate",
        default=15,
        minimum=5,
        maximum=40,
        unit="mm"
    )

    parameters.add_float(
        variable_name="pre_wet_volume",
        display_name="Pre-wet volume",
        description="Extra vol to clear air lock",
        default=10,
        minimum=0,
        maximum=30,
        unit="uL"
    )

    parameters.add_int(
        variable_name="num_points",
        display_name="Ellipse points/well",
        description="Points on ellipse per well",
        default=10,
        minimum=1,
        maximum=32,
    )

    parameters.add_float(
        variable_name="overlap",
        display_name="Overlap ratio",
        description="0=no overlap,1=full 2nd sweep",
        default=2,
        minimum=0,
        maximum=10,
    )

    parameters.add_float(
        variable_name="volume_per_well",
        display_name="Volume per well",
        description="Volume to dispense per well",
        default=193,
        minimum=50,
        maximum=200,
        unit="uL"
    )


def generate_ellipse_points(num_points, overlap):
    num_points = int(num_points)
    base_t = np.linspace(np.pi / 2, 2 * np.pi + np.pi / 2, num_points, endpoint=False)
    total_sweeps = 1 + int(overlap)
    t = np.concatenate([base_t + (i * (2 * np.pi / num_points)) for i in range(total_sweeps)])
    updated_num_points = len(t)
    x = 5.5 * np.cos(t)
    y = 2.85 * np.sin(t)
    return list(zip(x, y)), updated_num_points


def get_target_wells(plate, target_segment):
    """Return the 4 well objects for the chosen column segment.

    target_segment is like 'A4' or 'E2': the letter selects whether the
    top half (A,B,C,D) or bottom half (E,F,G,H) of that column is filled,
    and the number selects the column (1-6).
    """
    row_letter = target_segment[0]
    col_num = int(target_segment[1:])

    col_wells = plate.columns()[col_num - 1]  # 8 wells, ordered A->H
    start_idx = 0 if row_letter == "A" else 4
    return col_wells[start_idx:start_idx + 4]


def dispense_into_well(pipette, well, protocol, volume, ellipse_points,
                        updated_num_points, z_height, travel_height):
    pipette.move_to(well.top(z=travel_height))
    total_dispensed = 0
    for i, (x, y) in enumerate(ellipse_points):
        position = well.bottom(z=z_height).move(Point(x, y, 0))
        pipette.move_to(position, speed=50)
        vol = volume / updated_num_points
        pipette.dispense(vol)
        total_dispensed += vol

        if i == 0:
            protocol.delay(seconds=0.5)
        elif i == len(ellipse_points) // 2:
            protocol.delay(seconds=0.5)

        if total_dispensed >= volume:
            break


def run(protocol: protocol_api.ProtocolContext):
    p = protocol.params

    wait_time_aspirate = 2
    wait_time_prewet_return = 1
    n_wells = 4  # fixed: one column segment (A-D or E-H) per run

    # Load labware
    tip_rack = protocol.load_labware("opentrons_flex_96_tiprack_1000ul", "C2")
    pipette = protocol.load_instrument("flex_1channel_1000", "left", tip_racks=[tip_rack])
    plate = protocol.load_labware("myrplate_48_wellplate_800ul", "D3")
    # NEST 2 mL 96-well deep well plate (cat. 503501) at D2. The operator
    # picks which single well to aspirate the master-mix aliquot from.
    # Recommended fill: enough to cover (volume_per_well * 4) + pre-wet
    # volume + dead volume near the V-bottom tip, safely under the 2 mL cap.
    source_plate = protocol.load_labware("nest_96_wellplate_2ml_deep", "D2")
    protocol.load_trash_bin("A3")

    # Absolute flow rates in uL/s (not a multiplier)
    pipette.flow_rate.aspirate = p.aspirate_rate_uLs
    pipette.flow_rate.dispense = p.dispense_rate_uLs

    media = protocol.define_liquid(
        name="Master Mix",
        description="Cell-laden collagen mix",
        display_color="#0000FF"
    )

    target_wells = get_target_wells(plate, p.target_segment)
    ellipse_points, updated_num_points = generate_ellipse_points(p.num_points, p.overlap)

    source_well = source_plate.wells_by_name()[p.source_well]

    # A tip now fills all 4 target wells, so it must aspirate roughly
    # volume_per_well * 4 (e.g. 200 uL/well -> ~800 uL) from the D2 source.
    total_dispense_volume = p.volume_per_well * n_wells
    dispense_volume_per_well = p.volume_per_well
    batch_total_aspirate = total_dispense_volume + p.pre_wet_volume

    if batch_total_aspirate > 1000:
        raise ValueError(
            "Aspirate volume (volume_per_well * 4 + pre_wet_volume) exceeds "
            "the 1000uL pipette capacity; lower volume_per_well or pre_wet_volume."
        )

    source_well.load_liquid(media, volume=max(1100, batch_total_aspirate + 100))

    pipette.pick_up_tip()

    # --- Aspiration with anti-bubble handling ---
    pipette.move_to(source_well.bottom(z=1.5))
    pipette.aspirate(batch_total_aspirate, source_well)
    protocol.delay(seconds=wait_time_aspirate)

    # Reverse pre-wet: clear trapped air / normalize meniscus
    pipette.dispense(p.pre_wet_volume, source_well)
    protocol.delay(seconds=wait_time_prewet_return)

    pipette.move_to(source_well.top(z=5), speed=20)
    pipette.touch_tip(source_well)

    for well in target_wells:
        dispense_into_well(
            pipette, well, protocol, dispense_volume_per_well,
            ellipse_points, updated_num_points,
            p.z_height, p.travel_height_mm
        )
        pipette.move_to(well.top(z=p.travel_height_mm))

    pipette.drop_tip()
