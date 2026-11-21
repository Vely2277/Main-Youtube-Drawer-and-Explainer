"""Validation engine for scene specs."""

from pathlib import Path
from typing import Any

from asset_registry import AssetRegistry
from scene_schema import (
    FRAME_HEIGHT,
    FRAME_WIDTH,
    GROUND_BASELINE,
    MOTION_CONSTRAINTS,
    ROLE_SCALE_RANGES,
    SAFE_MARGIN_X,
    SAFE_MARGIN_Y,
    validate_coordinates_in_frame,
    validate_role_scale,
    validate_schema,
    validate_zone_y,
    ZONE_Y_RULES,
)


class SceneValidator:
    """Comprehensive validator for scene specs."""

    def __init__(self, asset_dir: Path):
        self.asset_dir = asset_dir
        self.asset_registry = AssetRegistry(asset_dir)

    def validate_spec(self, spec: dict[str, Any]) -> list[str]:
        """Validate complete scene spec and return list of errors."""
        errors = []

        # Schema validation
        schema_errors = validate_schema(spec)
        errors.extend(schema_errors)

        # If schema validation failed, return early
        if schema_errors:
            return errors

        # Asset validation
        asset_errors = self._validate_assets(spec)
        errors.extend(asset_errors)

        # Coordinate validation
        coord_errors = self._validate_coordinates(spec)
        errors.extend(coord_errors)

        # Scale validation
        scale_errors = self._validate_scales(spec)
        errors.extend(scale_errors)

        # Motion validation
        motion_errors = self._validate_motions(spec)
        errors.extend(motion_errors)

        # Collision detection
        collision_errors = self._detect_collisions(spec)
        errors.extend(collision_errors)

        # Zone consistency
        zone_errors = self._validate_zone_consistency(spec)
        errors.extend(zone_errors)

        return errors

    def _validate_assets(self, spec: dict[str, Any]) -> list[str]:
        """Validate all asset paths exist."""
        errors = []

        for i, entity in enumerate(spec["entities"]):
            asset_path = entity.get("asset", "")
            is_valid, error_msg = self.asset_registry.validate_asset_path(asset_path)
            if not is_valid:
                errors.append(f"entities[{i}]: {error_msg}")

            # Check parent_asset if present
            parent_asset = entity.get("parent_asset")
            if parent_asset:
                is_valid, error_msg = self.asset_registry.validate_asset_path(parent_asset)
                if not is_valid:
                    errors.append(f"entities[{i}].parent_asset: {error_msg}")

        return errors

    def _validate_coordinates(self, spec: dict[str, Any]) -> list[str]:
        """Validate entity coordinates are within frame."""
        errors = []

        # This is a simplified check - actual coordinates are computed by solver
        # We validate that offsets are reasonable
        for i, entity in enumerate(spec["entities"]):
            x_offset = entity.get("x_offset", 0.0)
            y_offset = entity.get("y_offset", 0.0)

            if abs(x_offset) > 10.0:
                errors.append(f"entities[{i}]: x_offset too large ({x_offset})")

            if abs(y_offset) > 10.0:
                errors.append(f"entities[{i}]: y_offset too large ({y_offset})")

        return errors

    def _validate_scales(self, spec: dict[str, Any]) -> list[str]:
        """Validate scale fractions are within role-specific ranges."""
        errors = []

        for i, entity in enumerate(spec["entities"]):
            role = entity.get("role", "")
            scale = entity.get("scale_fraction", 0.0)

            if not validate_role_scale(role, scale):
                if role in ROLE_SCALE_RANGES:
                    min_scale, max_scale = ROLE_SCALE_RANGES[role]
                    errors.append(
                        f"entities[{i}]: scale_fraction {scale} outside range "
                        f"[{min_scale}, {max_scale}] for role '{role}'"
                    )

        return errors

    def _validate_motions(self, spec: dict[str, Any]) -> list[str]:
        """Validate motion parameters."""
        errors = []

        for i, entity in enumerate(spec["entities"]):
            motion_type = entity.get("motion_type", "static")
            motion_run_time = entity.get("motion_run_time", 1.8)
            run_time = entity.get("run_time", 1.0)

            # Validate motion run time
            if motion_run_time < MOTION_CONSTRAINTS["min_run_time"]:
                errors.append(
                    f"entities[{i}]: motion_run_time {motion_run_time} below minimum "
                    f"{MOTION_CONSTRAINTS['min_run_time']}"
                )

            if motion_run_time > MOTION_CONSTRAINTS["max_run_time"]:
                errors.append(
                    f"entities[{i}]: motion_run_time {motion_run_time} above maximum "
                    f"{MOTION_CONSTRAINTS['max_run_time']}"
                )

            # Validate run time
            if run_time < 0.1:
                errors.append(f"entities[{i}]: run_time {run_time} below minimum 0.1")

            if run_time > 10.0:
                errors.append(f"entities[{i}]: run_time {run_time} above maximum 10.0")

            # Validate motion targets
            if motion_type in ["translate_x", "translate_y"]:
                target_x = entity.get("motion_target_x")
                target_y = entity.get("motion_target_y")

                if motion_type == "translate_x" and target_x is None:
                    errors.append(f"entities[{i}]: translate_x motion requires motion_target_x")

                if motion_type == "translate_y" and target_y is None:
                    errors.append(f"entities[{i}]: translate_y motion requires motion_target_y")

                # Check if targets are within reasonable bounds
                if target_x is not None and abs(target_x) > 10.0:
                    errors.append(f"entities[{i}]: motion_target_x {target_x} out of bounds")

                if target_y is not None and abs(target_y) > 10.0:
                    errors.append(f"entities[{i}]: motion_target_y {target_y} out of bounds")

        return errors

    def _detect_collisions(self, spec: dict[str, Any]) -> list[str]:
        """Detect potential collisions between entities."""
        errors = []

        # This is a simplified collision check
        # In practice, we'd need actual computed positions from solver
        # For now, we check for entities with same motion_group that might overlap

        motion_groups: dict[str, list[int]] = {}
        for i, entity in enumerate(spec["entities"]):
            motion_group = entity.get("motion_group")
            if motion_group:
                if motion_group not in motion_groups:
                    motion_groups[motion_group] = []
                motion_groups[motion_group].append(i)

        # Check for entities in same motion group with similar scales
        for group_name, indices in motion_groups.items():
            if len(indices) > 1:
                # Check if scales are too similar (might overlap)
                scales = [spec["entities"][i].get("scale_fraction", 0.0) for i in indices]
                if len(set(scales)) == 1:
                    # All same scale - potential overlap
                    errors.append(
                        f"Motion group '{group_name}' has {len(indices)} entities "
                        f"with identical scale_fraction {scales[0]} - potential overlap"
                    )

        return errors

    def _validate_zone_consistency(self, spec: dict[str, Any]) -> list[str]:
        """Validate zone assignments are consistent with roles."""
        errors = []

        role_zone_map = {
            "character": "ground",
            "prop": "ground",
            "structure": "ground",
            "sky_entity": "sky",
            "background": "background",
            "foreground": "foreground",
        }

        for i, entity in enumerate(spec["entities"]):
            role = entity.get("role", "")
            zone = entity.get("zone", "")

            expected_zone = role_zone_map.get(role)
            if expected_zone and zone != expected_zone:
                # Allow some flexibility - not all characters must be ground
                if role == "character" and zone == "sky":
                    # Flying character is okay
                    pass
                elif role == "sky_entity" and zone == "ground":
                    # Ground-level sky entity is unusual but not invalid
                    pass
                else:
                    errors.append(
                        f"entities[{i}]: role '{role}' typically uses zone '{expected_zone}', "
                        f"but got '{zone}'"
                    )

        return errors

    def get_validation_summary(self, spec: dict[str, Any]) -> dict[str, Any]:
        """Get a summary of validation results."""
        errors = self.validate_spec(spec)

        return {
            "is_valid": len(errors) == 0,
            "error_count": len(errors),
            "errors": errors,
            "entity_count": len(spec.get("entities", [])),
            "scene_name": spec.get("scene_name", "unknown"),
        }

    def suggest_fixes(self, spec: dict[str, Any], errors: list[str]) -> list[str]:
        """Suggest fixes for validation errors."""
        suggestions = []

        for error in errors:
            if "asset not found" in error.lower():
                # Extract asset path from error
                parts = error.split(":")
                if len(parts) > 1:
                    asset_path = parts[-1].strip()
                    suggestions.extend(self.asset_registry.get_asset_suggestions(asset_path))

            elif "scale_fraction" in error and "outside range" in error:
                suggestions.append("Adjust scale_fraction to be within role-specific range")

            elif "motion_target" in error:
                suggestions.append("Ensure motion_target_x/y are within frame bounds (-10 to 10)")

            elif "collision" in error.lower() or "overlap" in error.lower():
                suggestions.append("Adjust entity positions or scales to avoid overlap")

        return suggestions
