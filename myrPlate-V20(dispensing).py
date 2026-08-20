# -*- coding: utf-8 -*-
"""
myrPlate V20-Disp Dispensing
------------------------------
Feeds fresh media into a myrPlate that was cast in 4-well column segments
with myrPlate_tissue_casting-1Ch1ml_V20.py. Uses the same single channel
pipette and target-segment addressing as V20, aspirating from a 12-well
media reservoir and dispensing along the identical elliptical route into
each of the 4 wells in the chosen segment.

Because full media volumes (up to 485 uL/well) do not allow batching all
4 wells into a single 1000 uL tip the way V20's smaller 200 uL casting
volume does, this protocol re-aspirates (with the same tip) before each
well, using V20's pre-wet anti-bubble handling each time.
"""
from opentrons import protocol_api
import numpy as np
from opentrons.types import Point

metadata = {
    "protocolName": "myrPlate V20-Disp Dispensing",
    "description": "Feeds fresh media into a V20-cast 4-well segment along the same elliptical route",
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
            "4-well segment to feed. A1-A6 = rows A,B,C,D of that "
            "column; E1-E6 = rows E,F,G,H."
        ),
        choices=_target_segment_choices(),
        default="A4",
    )

    parameters.add_int(
        variable_name="aspirate_location_Index",
        display_name="Reservoir well# A1-A12",
        description="Media well# in the nest_12_reservoir_15ml to aspirate from",
        default=1,
        minimum=1,
        maximum=12,
    )

    parameters.add_float(
        variable_name="aspirate_rate_uLs",
        display_name="Aspirate rate (uL/s)",
        description="Absolute aspirate flow rate",
        default=80,
        minimum=5,
        maximum=200,
        unit="uL/s"
    )

    parameters.add_float(
        variable_name="dispense_rate_uLs",
        display_name="Dispense rate (uL/s)",
        description="Absolute dispense flow rate",
        default=65,
        minimum=5,
        maximum=200,
        unit="uL/s"
    )

    parameters.add_float(
        variable_name="z_height",
        display_name="Z height",
        description="Dispense height from bottom",
        default=5,
        minimum=0.00,
        maximum=15.00,
        unit="mm"
    )

    parameters.add_float(
        variable_name="travel_height_mm",
        display_name="Travel height",
        description="Clearance over the plate",
        default=20,
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
        default=6,
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
        description="Volume to dispense per well",
        default=400,
        minimum=100,
        maximum=485,
        unit="uL"
    )


def generate_ellipse_points(num_points, overlap):
    """Identical ellipse equation to V20 (fixed 5.5/2.85 mm semi-axes),
    so fresh media is delivered along the same path the tissue was cast
    along."""
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

    col_wells = plate.columns()[col_num - 1]
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
            protocol.delay(seconds=1)
        elif i == len(ellipse_points) // 2:
            protocol.delay(seconds=0.5)

        if total_dispensed >= volume:
            break


def run(protocol: protocol_api.ProtocolContext):
    p = protocol.params

    wait_time_aspirate = 4
    wait_time_prewet_return = 1

    # Load labware - same tip rack/plate slots as V20, plus a 12-well
    # media reservoir at D2 (as in the original V1 dispensing protocol)
    tip_rack = protocol.load_labware("opentrons_flex_96_tiprack_1000ul", "C2")
    pipette = protocol.load_instrument("flex_1channel_1000", "left", tip_racks=[tip_rack])
    plate = protocol.load_labware("myrplate_48_wellplate_800ul", "D3")
    media_rack = protocol.load_labware("nest_12_reservoir_15ml", "D2")
    protocol.load_trash_bin("A3")

    # Absolute flow rates in uL/s (not a multiplier), as in V20
    pipette.flow_rate.aspirate = p.aspirate_rate_uLs
    pipette.flow_rate.dispense = p.dispense_rate_uLs

    Media = protocol.define_liquid(
        name="EHMM",
        description="Engineered Heart Myocardium Media solution for feeding myrPlates",
        display_color="#0000FF"
    )
    aspiration_location = f"A{p.aspirate_location_Index}"
    media_rack[aspiration_location].load_liquid(Media, volume=10000)
    aspirate_well = media_rack[aspiration_location]

    target_wells = get_target_wells(plate, p.target_segment)
    ellipse_points, updated_num_points = generate_ellipse_points(p.num_points, p.overlap)

    if p.volume_per_well + p.pre_wet_volume > 1000:
        raise ValueError(
            "volume_per_well + pre_wet_volume exceeds the 1000uL pipette "
            "capacity; lower one of these parameters."
        )

    pipette.pick_up_tip()

    for well in target_wells:
        # --- Aspiration with anti-bubble handling (per well, same tip) ---
        pipette.move_to(aspirate_well.bottom(z=0.2))
        pipette.aspirate(p.volume_per_well + p.pre_wet_volume, aspirate_well)
        protocol.delay(seconds=wait_time_aspirate)

        # Reverse pre-wet: clear trapped air / normalize meniscus
        pipette.dispense(p.pre_wet_volume / 2, aspirate_well)
        protocol.delay(seconds=wait_time_prewet_return)

        pipette.move_to(aspirate_well.top(z=5), speed=20)
        pipette.touch_tip(aspirate_well)

        dispense_into_well(
            pipette, well, protocol, p.volume_per_well,
            ellipse_points, updated_num_points,
            p.z_height, p.travel_height_mm
        )
        pipette.move_to(well.top(z=p.travel_height_mm))

        # Clear the remaining pre-wet buffer before the next aspirate cycle
        pipette.move_to(aspirate_well.top(z=5))
        pipette.blow_out(aspirate_well)

    pipette.drop_tip()
