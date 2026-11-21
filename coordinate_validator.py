"""Coordinate and motion validators for scene specs."""

from typing import Any

from scene_schema import (
    FRAME_HEIGHT,
    FRAME_WIDTH,
    GROUND_BASELINE,
    MOTION_CONSTRAINTS,
    SAFE_MARGIN_X,
    SAFE_MARGIN_Y,
    validate_coordinates_in_frame,
)


class CoordinateValidator:
    """Validate entity coordinates and positions."""

    def __init__(self):
        self.frame_width = FRAME_WIDTH
        self.frame_height = FRAME_HEIGHT
        self.ground_baseline = GROUND_BASELINE
        self.safe_margin_x = SAFE_MARGIN_X
        self.safe_margin_y = SAFE_MARGIN_Y

    def validate_entity_position(
        self,
        x: float,
        y: float,
        width: float,
        height: float,
        anchor: str,
    ) -> tuple[bool, str]:
        """Validate that entity position is within frame bounds."""
        # Calculate bounding box based on anchor
        if anchor == "bottom":
            # Bottom of entity at y, extends upward
            entity_bottom = y
            entity_top = y + height
            entity_left = x - width / 2
            entity_right = x + width / 2
        elif anchor == "top":
            # Top of entity at y, extends downward
            entity_bottom = y - height
            entity_top = y
            entity_left = x - width / 2
            entity_right = x + width / 2
        else:  # center
            entity_bottom = y - height / 2
            entity_top = y + height / 2
            entity_left = x - width / 2
            entity_right = x + width / 2

        # Frame bounds with safe margins
        frame_left = -self.frame_width / 2 + (self.safe_margin_x * self.frame_width)
        frame_right = self.frame_width / 2 - (self.safe_margin_x * self.frame_width)
        frame_bottom = -self.frame_height / 2 + (self.safe_margin_y * self.frame_height)
        frame_top = self.frame_height / 2 - (self.safe_margin_y * self.frame_height)

        # Check if entity is within frame
        if entity_left < frame_left:
            return False, f"Entity left edge {entity_left:.2f} outside frame left {frame_left:.2f}"
        if entity_right > frame_right:
            return False, f"Entity right edge {entity_right:.2f} outside frame right {frame_right:.2f}"
        if entity_bottom < frame_bottom:
            return False, f"Entity bottom edge {entity_bottom:.2f} outside frame bottom {frame_bottom:.2f}"
        if entity_top > frame_top:
            return False, f"Entity top edge {entity_top:.2f} outside frame top {frame_top:.2f}"

        return True, ""

    def validate_motion_target(
        self,
        start_x: float,
        start_y: float,
        target_x: float,
        target_y: float,
        motion_type: str,
    ) -> tuple[bool, str]:
        """Validate that motion target is reachable and within frame."""
        # Check if target is within frame
        if not validate_coordinates_in_frame(target_x, target_y):
            return False, f"Motion target ({target_x:.2f}, {target_y:.2f}) outside frame bounds"

        # Check motion distance
        distance = ((target_x - start_x) ** 2 + (target_y - start_y) ** 2) ** 0.5
        max_distance = self.frame_width  # Allow motion up to frame width

        if distance > max_distance:
            return False, f"Motion distance {distance:.2f} exceeds maximum {max_distance:.2f}"

        return True, ""

    def calculate_safe_position(
        self,
        desired_x: float,
        desired_y: float,
        width: float,
        height: float,
        anchor: str,
    ) -> tuple[float, float]:
        """Calculate safe position within frame bounds."""
        # Frame bounds with safe margins
        frame_left = -self.frame_width / 2 + (self.safe_margin_x * self.frame_width)
        frame_right = self.frame_width / 2 - (self.safe_margin_x * self.frame_width)
        frame_bottom = -self.frame_height / 2 + (self.safe_margin_y * self.frame_height)
        frame_top = self.frame_height / 2 - (self.safe_margin_y * self.frame_height)

        # Calculate entity bounds
        if anchor == "bottom":
            entity_bottom = desired_y
            entity_top = desired_y + height
        elif anchor == "top":
            entity_bottom = desired_y - height
            entity_top = desired_y
        else:  # center
            entity_bottom = desired_y - height / 2
            entity_top = desired_y + height / 2

        entity_left = desired_x - width / 2
        entity_right = desired_x + width / 2

        # Clamp to frame bounds
        safe_x = desired_x
        safe_y = desired_y

        # Adjust x if needed
        if entity_left < frame_left:
            safe_x = frame_left + width / 2
        elif entity_right > frame_right:
            safe_x = frame_right - width / 2

        # Adjust y if needed
        if entity_bottom < frame_bottom:
            safe_y = frame_bottom + height / 2 if anchor == "center" else frame_bottom
        elif entity_top > frame_top:
            safe_y = frame_top - height / 2 if anchor == "center" else frame_top

        return safe_x, safe_y


class MotionValidator:
    """Validate motion parameters and feasibility."""

    def __init__(self):
        self.max_speed = MOTION_CONSTRAINTS["max_speed"]
        self.min_run_time = MOTION_CONSTRAINTS["min_run_time"]
        self.max_run_time = MOTION_CONSTRAINTS["max_run_time"]

    def validate_motion_speed(
        self,
        distance: float,
        run_time: float,
    ) -> tuple[bool, str]:
        """Validate that motion speed is reasonable."""
        if run_time <= 0:
            return False, "Run time must be positive"

        speed = distance / run_time
        if speed > self.max_speed:
            return False, f"Motion speed {speed:.2f} exceeds maximum {self.max_speed:.2f}"

        return True, ""

    def validate_motion_duration(
        self,
        run_time: float,
    ) -> tuple[bool, str]:
        """Validate that motion duration is within bounds."""
        if run_time < self.min_run_time:
            return False, f"Run time {run_time:.2f} below minimum {self.min_run_time:.2f}"

        if run_time > self.max_run_time:
            return False, f"Run time {run_time:.2f} above maximum {self.max_run_time:.2f}"

        return True, ""

    def validate_motion_type(
        self,
        motion_type: str,
        has_target_x: bool,
        has_target_y: bool,
    ) -> tuple[bool, str]:
        """Validate that motion type has required parameters."""
        if motion_type == "translate_x" and not has_target_x:
            return False, "translate_x motion requires motion_target_x"

        if motion_type == "translate_y" and not has_target_y:
            return False, "translate_y motion requires motion_target_y"

        if motion_type == "scale" and not (has_target_x or has_target_y):
            return False, "scale motion requires motion_target_x or motion_target_y"

        return True, ""

    def calculate_motion_distance(
        self,
        start_x: float,
        start_y: float,
        target_x: float,
        target_y: float,
        motion_type: str,
    ) -> float:
        """Calculate motion distance based on type."""
        if motion_type == "translate_x":
            return abs(target_x - start_x)
        elif motion_type == "translate_y":
            return abs(target_y - start_y)
        elif motion_type == "scale":
            # For scale, distance is the scale factor change
            return abs(target_x - start_x) if has_target_x else abs(target_y - start_y)
        else:
            return 0.0


class SceneCoordinateValidator:
    """Comprehensive coordinate validator for scene specs."""

    def __init__(self):
        self.coord_validator = CoordinateValidator()
        self.motion_validator = MotionValidator()

    def validate_spec_coordinates(self, spec: dict[str, Any]) -> list[str]:
        """Validate all coordinates in scene spec."""
        errors = []

        for i, entity in enumerate(spec.get("entities", [])):
            # Validate offsets
            x_offset = entity.get("x_offset", 0.0)
            y_offset = entity.get("y_offset", 0.0)

            if abs(x_offset) > 10.0:
                errors.append(f"entities[{i}]: x_offset {x_offset} out of bounds (-10 to 10)")

            if abs(y_offset) > 10.0:
                errors.append(f"entities[{i}]: y_offset {y_offset} out of bounds (-10 to 10)")

            # Validate motion targets
            motion_type = entity.get("motion_type", "static")
            motion_target_x = entity.get("motion_target_x")
            motion_target_y = entity.get("motion_target_y")
            motion_run_time = entity.get("motion_run_time", 1.8)

            if motion_type in ["translate_x", "translate_y", "scale"]:
                # Check if required targets are present
                has_target_x = motion_target_x is not None
                has_target_y = motion_target_y is not None

                is_valid, error_msg = self.motion_validator.validate_motion_type(
                    motion_type, has_target_x, has_target_y
                )
                if not is_valid:
                    errors.append(f"entities[{i}]: {error_msg}")

                # Validate motion duration
                is_valid, error_msg = self.motion_validator.validate_motion_duration(motion_run_time)
                if not is_valid:
                    errors.append(f"entities[{i}]: {error_msg}")

                # Validate motion targets are within frame
                if motion_target_x is not None and abs(motion_target_x) > 10.0:
                    errors.append(f"entities[{i}]: motion_target_x {motion_target_x} out of bounds")

                if motion_target_y is not None and abs(motion_target_y) > 10.0:
                    errors.append(f"entities[{i}]: motion_target_y {motion_target_y} out of bounds")

        return errors
