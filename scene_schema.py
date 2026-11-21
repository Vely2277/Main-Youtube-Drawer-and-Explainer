"""Scene spec schema definition for validation."""

from typing import Any


# JSON Schema for scene spec validation
SCENE_SPEC_SCHEMA = {
    "type": "object",
    "required": ["scene_name", "entities"],
    "properties": {
        "scene_name": {
            "type": "string",
            "minLength": 1,
            "maxLength": 100,
        },
        "entities": {
            "type": "array",
            "minItems": 1,
            "items": {
                "type": "object",
                "required": [
                    "asset",
                    "role",
                    "zone",
                    "anchor",
                    "scale_fraction",
                ],
                "properties": {
                    "asset": {
                        "type": "string",
                        "pattern": r"^[a-zA-Z0-9_\-/]+\.svg$",
                        "description": "Path to SVG file relative to assets/svgs/",
                    },
                    "role": {
                        "type": "string",
                        "enum": [
                            "character",
                            "prop",
                            "structure",
                            "sky_entity",
                            "background",
                            "foreground",
                        ],
                    },
                    "zone": {
                        "type": "string",
                        "enum": ["sky", "ground", "background", "foreground"],
                    },
                    "anchor": {
                        "type": "string",
                        "enum": ["bottom", "center", "top"],
                    },
                    "scale_fraction": {
                        "type": "number",
                        "minimum": 0.01,
                        "maximum": 1.0,
                    },
                    "parent_asset": {
                        "type": ["string", "null"],
                        "pattern": r"^[a-zA-Z0-9_\-/]+\.svg$",
                    },
                    "relative_offset_x": {
                        "type": "number",
                        "minimum": -10.0,
                        "maximum": 10.0,
                    },
                    "relative_offset_y": {
                        "type": "number",
                        "minimum": -10.0,
                        "maximum": 10.0,
                    },
                    "relative_anchor": {
                        "type": "string",
                        "enum": ["bottom", "center", "top"],
                    },
                    "composition_context": {
                        "type": ["string", "null"],
                        "maxLength": 500,
                    },
                    "motion_group": {
                        "type": ["string", "null"],
                        "maxLength": 50,
                    },
                    "motion_type": {
                        "type": "string",
                        "enum": ["static", "translate_x", "translate_y", "scale", "fade"],
                    },
                    "motion_target_x": {
                        "type": ["number", "null"],
                        "minimum": -10.0,
                        "maximum": 10.0,
                    },
                    "motion_target_y": {
                        "type": ["number", "null"],
                        "minimum": -10.0,
                        "maximum": 10.0,
                    },
                    "motion_run_time": {
                        "type": "number",
                        "minimum": 0.1,
                        "maximum": 10.0,
                    },
                    "animation": {
                        "type": "string",
                        "enum": ["create", "draw_border"],
                    },
                    "run_time": {
                        "type": "number",
                        "minimum": 0.1,
                        "maximum": 10.0,
                    },
                    "wait_after": {
                        "type": "number",
                        "minimum": 0.0,
                        "maximum": 5.0,
                    },
                    "z_index": {
                        "type": "integer",
                        "minimum": 0,
                        "maximum": 100,
                    },
                    "x_offset": {
                        "type": "number",
                        "minimum": -10.0,
                        "maximum": 10.0,
                    },
                    "y_offset": {
                        "type": "number",
                        "minimum": -10.0,
                        "maximum": 10.0,
                    },
                },
                "additionalProperties": False,
            },
        },
    },
    "additionalProperties": False,
}


# Role-specific scale ranges
ROLE_SCALE_RANGES = {
    "character": (0.20, 0.40),
    "prop": (0.05, 0.20),
    "structure": (0.25, 0.60),
    "sky_entity": (0.08, 0.30),
    "background": (0.30, 0.80),
    "foreground": (0.15, 0.50),
}


# Zone-specific y-coordinate rules
ZONE_Y_RULES = {
    "sky": (0.0, 4.0),  # y > 0
    "ground": (-4.0, 0.0),  # y < 0
    "background": (-4.0, 4.0),  # any y
    "foreground": (-4.0, 4.0),  # any y
}


# Frame constants
FRAME_WIDTH = 14.22
FRAME_HEIGHT = 8.0
GROUND_BASELINE = -2.35
SAFE_MARGIN_X = 0.08  # 8% of frame width
SAFE_MARGIN_Y = 0.10  # 10% of frame height


# Motion constraints
MOTION_CONSTRAINTS = {
    "max_speed": 5.0,  # units per second
    "min_run_time": 0.1,
    "max_run_time": 10.0,
}


def validate_schema(spec: dict[str, Any]) -> list[str]:
    """Validate scene spec against JSON schema."""
    errors = []

    # Check required top-level fields
    if "scene_name" not in spec:
        errors.append("Missing required field: scene_name")
    elif not isinstance(spec["scene_name"], str) or not spec["scene_name"].strip():
        errors.append("scene_name must be a non-empty string")

    if "entities" not in spec:
        errors.append("Missing required field: entities")
    elif not isinstance(spec["entities"], list):
        errors.append("entities must be an array")
    elif len(spec["entities"]) == 0:
        errors.append("entities array cannot be empty")

    # Validate each entity
    if "entities" in spec and isinstance(spec["entities"], list):
        for i, entity in enumerate(spec["entities"]):
            entity_errors = _validate_entity(entity, i)
            errors.extend(entity_errors)

    return errors


def _validate_entity(entity: dict[str, Any], index: int) -> list[str]:
    """Validate a single entity."""
    errors = []
    prefix = f"entities[{index}]"

    # Check required fields
    required_fields = ["asset", "role", "zone", "anchor", "scale_fraction"]
    for field in required_fields:
        if field not in entity:
            errors.append(f"{prefix}: Missing required field '{field}'")

    # Validate asset path
    if "asset" in entity:
        asset = entity["asset"]
        if not isinstance(asset, str):
            errors.append(f"{prefix}: asset must be a string")
        elif not asset.endswith(".svg"):
            errors.append(f"{prefix}: asset must end with .svg")
        elif ".." in asset or asset.startswith("/") or asset.startswith("\\"):
            errors.append(f"{prefix}: asset path cannot contain '..' or start with '/' or '\\'")

    # Validate role
    if "role" in entity:
        role = entity["role"]
        valid_roles = ["character", "prop", "structure", "sky_entity", "background", "foreground"]
        if role not in valid_roles:
            errors.append(f"{prefix}: role must be one of {valid_roles}")

    # Validate zone
    if "zone" in entity:
        zone = entity["zone"]
        valid_zones = ["sky", "ground", "background", "foreground"]
        if zone not in valid_zones:
            errors.append(f"{prefix}: zone must be one of {valid_zones}")

    # Validate anchor
    if "anchor" in entity:
        anchor = entity["anchor"]
        valid_anchors = ["bottom", "center", "top"]
        if anchor not in valid_anchors:
            errors.append(f"{prefix}: anchor must be one of {valid_anchors}")

    # Validate scale_fraction
    if "scale_fraction" in entity:
        scale = entity["scale_fraction"]
        if not isinstance(scale, (int, float)):
            errors.append(f"{prefix}: scale_fraction must be a number")
        elif scale < 0.01 or scale > 1.0:
            errors.append(f"{prefix}: scale_fraction must be between 0.01 and 1.0")

    # Validate optional fields
    optional_fields = {
        "parent_asset": str,
        "relative_offset_x": (int, float),
        "relative_offset_y": (int, float),
        "relative_anchor": str,
        "composition_context": str,
        "motion_group": str,
        "motion_type": str,
        "motion_target_x": (int, float),
        "motion_target_y": (int, float),
        "motion_run_time": (int, float),
        "animation": str,
        "run_time": (int, float),
        "wait_after": (int, float),
        "z_index": int,
        "x_offset": (int, float),
        "y_offset": (int, float),
    }

    for field, expected_type in optional_fields.items():
        if field in entity and entity[field] is not None:
            if not isinstance(entity[field], expected_type):
                errors.append(f"{prefix}: {field} must be of type {expected_type}")

    # Validate motion_type enum
    if "motion_type" in entity and entity["motion_type"] is not None:
        motion_type = entity["motion_type"]
        valid_motion_types = ["static", "translate_x", "translate_y", "scale", "fade"]
        if motion_type not in valid_motion_types:
            errors.append(f"{prefix}: motion_type must be one of {valid_motion_types}")

    # Validate animation enum
    if "animation" in entity and entity["animation"] is not None:
        animation = entity["animation"]
        valid_animations = ["create", "draw_border"]
        if animation not in valid_animations:
            errors.append(f"{prefix}: animation must be one of {valid_animations}")

    return errors


def validate_role_scale(role: str, scale_fraction: float) -> bool:
    """Validate that scale_fraction is within role-specific range."""
    if role not in ROLE_SCALE_RANGES:
        return True  # No range defined, allow any scale

    min_scale, max_scale = ROLE_SCALE_RANGES[role]
    return min_scale <= scale_fraction <= max_scale


def validate_zone_y(zone: str, y: float) -> bool:
    """Validate that y coordinate matches zone rules."""
    if zone not in ZONE_Y_RULES:
        return True  # No rule defined, allow any y

    min_y, max_y = ZONE_Y_RULES[zone]
    return min_y <= y <= max_y


def validate_coordinates_in_frame(x: float, y: float) -> bool:
    """Validate that coordinates are within frame bounds."""
    half_width = FRAME_WIDTH / 2
    half_height = FRAME_HEIGHT / 2

    # Apply safe margins
    min_x = -half_width + (SAFE_MARGIN_X * FRAME_WIDTH)
    max_x = half_width - (SAFE_MARGIN_X * FRAME_WIDTH)
    min_y = -half_height + (SAFE_MARGIN_Y * FRAME_HEIGHT)
    max_y = half_height - (SAFE_MARGIN_Y * FRAME_HEIGHT)

    return min_x <= x <= max_x and min_y <= y <= max_y
