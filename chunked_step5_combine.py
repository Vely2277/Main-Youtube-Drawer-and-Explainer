"""Chunked Ollama workflow - Step 5: Combine into scene spec."""

import json
from pathlib import Path
from typing import Any

from asset_registry import AssetRegistry


def step5_combine_spec(
    elements: list[str],
    assignments: dict[str, str],
    coordinates: dict[str, list],
    motion: dict[str, str],
) -> dict[str, Any]:
    """Step 5: Combine all data into final scene spec."""
    print("\n" + "="*60)
    print("[Step 5/5] Combining into scene spec...")
    print("="*60)
    print(f"Elements: {len(elements)}")
    print(f"Assignments: {len(assignments)}")
    print(f"Coordinates: {len(coordinates)}")
    print(f"Motion: {len(motion)}")
    print("\nBuilding entities...")

    asset_dir = Path("assets/svgs")
    registry = AssetRegistry(asset_dir)

    # Build entities list
    entities = []
    for i, element in enumerate(elements):
        print(f"  [{i+1}/{len(elements)}] Processing '{element}'...")

        role = assignments.get(element, "prop")
        x, y = coordinates.get(element, [0, 0])
        motion_type = motion.get(element, "static")

        # Find matching asset
        asset_path = registry.get_default_asset_for_role(role)
        if not asset_path:
            # Fallback to known assets
            if role == "sky_entity":
                if element == "plane":
                    asset_path = "tabler/outline/plane-inflight.svg"
                elif element == "cloud":
                    asset_path = "tabler/outline/cloud.svg"
                elif element == "sun":
                    asset_path = "tabler/outline/sun.svg"
                else:
                    asset_path = "tabler/outline/cloud.svg"
            elif role == "character":
                asset_path = "open_peeps/templates_standing/peep-standing-standing-blazer-1-buns-smile-teeth-gap-none.svg"
            else:
                asset_path = "tabler/outline/cloud.svg"

        # Determine zone from role
        if role == "sky_entity":
            zone = "sky"
        else:
            zone = "ground"

        # Determine scale from role
        if role == "sky_entity":
            scale = 0.15
        elif role == "character":
            scale = 0.12
        else:
            scale = 0.10

        # Build entity
        entity = {
            "asset": asset_path,
            "role": role,
            "zone": zone,
            "anchor": "center",
            "scale_fraction": scale,
            "x_offset": x,
            "y_offset": y,
            "motion_type": motion_type,
            "animation": "draw_border",
            "run_time": 1.0,
            "z_index": 5 if role == "character" else 1,
        }

        # Add motion target if needed
        if motion_type == "translate_y":
            entity["motion_target_y"] = y + 1.5
            entity["motion_run_time"] = 2.0
        elif motion_type == "translate_x":
            entity["motion_target_x"] = x + 1.0
            entity["motion_run_time"] = 2.0

        entities.append(entity)
        print(f"      -> Asset: {asset_path}")
        print(f"      -> Role: {role}, Zone: {zone}")
        print(f"      -> Position: ({x}, {y})")
        print(f"      -> Motion: {motion_type}")

    spec = {
        "scene_name": "Generated Scene",
        "entities": entities,
    }

    print(f"\n[OK] Generated {len(entities)} entities")
    print("="*60 + "\n")

    return spec


if __name__ == "__main__":
    elements = ["plane", "people", "cloud", "sun"]
    assignments = {"plane": "sky_entity", "people": "character", "cloud": "sky_entity", "sun": "sky_entity"}
    coordinates = {"plane": [0, 2], "people": [-2, -2], "cloud": [3, 1], "sun": [-3, 2]}
    motion = {"plane": "translate_y", "people": "static", "cloud": "static", "sun": "static"}

    result = step5_combine_spec(elements, assignments, coordinates, motion)
    print(json.dumps(result, indent=2))
