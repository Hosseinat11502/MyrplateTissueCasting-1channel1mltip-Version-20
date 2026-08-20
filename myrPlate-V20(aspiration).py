# -*- coding: utf-8 -*-
"""
myrPlate V20-Asp Aspiration
-----------------------------
Aspirates spent media from a myrPlate that was cast in 4-well column
segments with myrPlate_tissue_casting-1Ch1ml_V20.py. Uses the same single
channel pipette and target-segment addressing as V20 (top A-D or bottom
E-H quarter of a column), sweeps the identical elliptical route to clear
media without disturbing the tissue, and disposes into a waste reservoir
at C3 with a fresh tip per well (as in the original V3 aspiration
protocol).
"""
from opentrons import protocol_api
import numpy as np
from opentrons.types import Point

metadata = {
    "protocolName": "myrPlate V20-Asp Aspiration",
    "description": "Aspirates spent media from a V20-cast 4-well segment, disposing into block C3",
    "author": "HGH"
}
requirements = {"robotType": "Flex", "apiLevel": "2.18"}


def _target_segment_choices():
    """A1..A6 (fills A/B/C/D of that column) and E1..E6 (fills E/F/G/H) -
    identical choice set to V20 so the same segment naming is used."""
    choices = []
    for row in ("A", "E"):
        for col in range(1, 7):
            name = f"{row}{col}"
            choices.append({"display_name": name, "value": name})
    return choices


def add_parameters(parameters: protocol_api.Parameters):
    parameters.add_str(
        variable_name="target_segment",
        display_name="Target well segment",
        description=(
            "4-well segment to aspirate. A1-A6 = rows A,B,C,D of that "
            "column; E1-E6 = rows E,F,G,H."
        ),
        choices=_target_segment_choices(),
        default="A4",
    )

    parameters.add_float(
        variable_name="aspirate_rate_uLs",
        display_name="Aspirate rate (uL/s)",
        description="Absolute aspirate flow rate",
        default=40,
        minimum=5,
        maximum=200,
        unit="uL/s"
    )

    parameters.add_float(
        variable_name="dispense_rate_uLs",
        display_name="Dispense rate (uL/s)",
        description="Absolute dispense/blow-out flow rate",
        default=60,
        minimum=5,
        maximum=200,
        unit="uL/s"
    )

    parameters.add_float(
        variable_name="z_height",
        display_name="Z height",
        description="Aspirate height above well bottom",
        default=1.5,
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

    parameters.add_int(
        variable_name="num_points",
        display_name="Ellipse points/well",
        description="Points on ellipse per well",
        default=8,
        minimum=1,
        maximum=32,
    )

    parameters.add_float(
        variable_name="overlap",
        display_name="Overlap ratio",
        description="0=no overlap,1=full 2nd sweep",
        default=0,
        minimum=0,
        maximum=10,
    )

    parameters.add_float(
        variable_name="volume_per_well",
        display_name="Volume per well",
        description="Volume to aspirate per well",
        default=400,
        minimum=100,
        maximum=485,
        unit="uL"
    )


def generate_ellipse_points(num_points, overlap):
    """Identical ellipse equation to V20 (fixed 5.5/2.85 mm semi-axes),
    so aspiration follows the same path the tissue was cast along."""
    num_points = int(num_points)
    base_t = np.linspace(np.pi / 2, 2 * np.pi + np.pi / 2, num_points, endpoint=False)
    total_sweeps = 1 + int(overlap)
    t = np.concatenate([base_t + (i * (2 * np.pi / num_points)) for i in range(total_sweeps)])
    updated_num_points = len(t)
    x = 5.5 * np.cos(t)
    y = 2.85 * np.sin(t)
    return list(zip(x, y)), updated_num_points


def get_target_wells(plate, target_segment):
    """Same addressing as V20: the letter selects the top half (A,B,C,D)
    or bottom half (E,F,G,H) of the column, the number selects the column."""
    row_letter = target_segment[0]
    col_num = int(target_segment[1:])

    col_wells = plate.columns()[col_num - 1]  # 8 wells, ordered A->H
    start_idx = 0 if row_letter == "A" else 4
    return col_wells[start_idx:start_idx + 4]


def aspirate_from_well(pipette, well, protocol, volume, ellipse_points,
                        updated_num_points, z_height, travel_height):
    pipette.move_to(well.top(z=travel_height))
    total_aspirated = 0
    for i, (x, y) in enumerate(ellipse_points):
        position = well.bottom(z=z_height).move(Point(x, y, 0))
        pipette.move_to(position, speed=50)
        vol = volume / updated_num_points
        pipette.aspirate(vol)
        total_aspirated += vol

        if total_aspirated >= volume:
            break


def run(protocol: protocol_api.ProtocolContext):
    p = protocol.params

    wait_time_aspirate = 1

    # Load labware - same tip rack/plate slots as V20, plus a waste
    # reservoir at C3 (as in the original V3 aspiration protocol)
    tip_rack = protocol.load_labware("opentrons_flex_96_tiprack_1000ul", "C2")
    pipette = protocol.load_instrument("flex_1channel_1000", "left", tip_racks=[tip_rack])
    plate = protocol.load_labware("myrplate_48_wellplate_800ul", "D3")
    disposal_block = protocol.load_labware("nest_1_reservoir_195ml", "C3")
    protocol.load_trash_bin("A3")

    # Absolute flow rates in uL/s (not a multiplier), as in V20
    pipette.flow_rate.aspirate = p.aspirate_rate_uLs
    pipette.flow_rate.dispense = p.dispense_rate_uLs

    target_wells = get_target_wells(plate, p.target_segment)
    ellipse_points, updated_num_points = generate_ellipse_points(p.num_points, p.overlap)

    disposal_well = disposal_block["A1"]

    for well in target_wells:
        pipette.pick_up_tip()

        aspirate_from_well(
            pipette, well, protocol, p.volume_per_well,
            ellipse_points, updated_num_points,
            p.z_height, p.travel_height_mm
        )
        protocol.delay(seconds=wait_time_aspirate)

        pipette.move_to(well.top(z=p.travel_height_mm))
        pipette.move_to(disposal_well.top(z=3))
        pipette.blow_out()

        pipette.drop_tip()
