"""Layout solver - calculates coordinates and handles containment."""

import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from scene_parser import SceneSpec, Entity
from scene_dictionaries import ENTITY_DICTIONARY


# Frame constants
FRAME_WIDTH = 14.22
FRAME_HEIGHT = 8.0
GROUND_Y = -2.35
SKY_Y_MIN = 0.0
SKY_Y_MAX = 4.0
GROUND_Y_MIN = -4.0
GROUND_Y_MAX = -0.5
SAFE_MARGIN_X = 0.5
SAFE_MARGIN_Y = 0.5


@dataclass
class LayoutResult:
    """Result of layout calculation."""
    entity: Entity
    x: float
    y: float
    width: float
    height: float
    anchor: str
    scale: float
    z_index: int
    contained_in: str | None = None
    window_slot: int | None = None


class LayoutSolver:
    """Solves layout for scene entities."""

    def __init__(self, asset_dir: Path | None = None):
        self.asset_dir = asset_dir or Path("assets/svgs")
        self.entity_dict = ENTITY_DICTIONARY
        self.frame_width = FRAME_WIDTH
        self.frame_height = FRAME_HEIGHT
        self.ground_y = GROUND_Y
        self.sky_y_min = SKY_Y_MIN
        self.sky_y_max = SKY_Y_MAX
        self.ground_y_min = GROUND_Y_MIN
        self.ground_y_max = GROUND_Y_MAX
        self.safe_margin_x = SAFE_MARGIN_X
        self.safe_margin_y = SAFE_MARGIN_Y

    def solve(self, spec: SceneSpec) -> list[LayoutResult]:
        """Solve layout for all entities in the scene."""
        layouts = []

        # Expand entities based on count
        expanded_entities = self._expand_entities(spec.entities)

        # Separate entities by zone
        sky_entities = [e for e in expanded_entities if e.zone == "sky"]
        ground_entities = [e for e in expanded_entities if e.zone == "ground"]

        # Solve sky entities
        sky_layouts = self._solve_zone_entities(sky_entities, "sky")
        layouts.extend(sky_layouts)

        # Solve ground entities
        ground_layouts = self._solve_zone_entities(ground_entities, "ground")
        layouts.extend(ground_layouts)

        # Handle containment relationships
        layouts = self._handle_containment(layouts, expanded_entities)

        # Resolve collisions
        layouts = self._resolve_collisions(layouts)

        # Assign z-indices
        layouts = self._assign_z_indices(layouts)

        return layouts

    def _expand_entities(self, entities: list[Entity]) -> list[Entity]:
        """Expand entities based on count (e.g., count=2 → 2 separate entities)."""
        expanded = []
        for entity in entities:
            for i in range(entity.count):
                # Create a copy of the entity
                new_entity = Entity(
                    name=entity.name,
                    count=1,  # Each expanded entity has count 1
                    asset=entity.asset,
                    role=entity.role,
                    zone=entity.zone,
                    default_scale=entity.default_scale,
                    category=entity.category,
                    can_contain=entity.can_contain,
                    container_type=entity.container_type,
                    default_relation=entity.default_relation,
                    action=entity.action,
                    motion_type=entity.motion_type,
                    motion_direction=entity.motion_direction,
                    motion_speed=entity.motion_speed,
                    relation=entity.relation,
                    relation_target=entity.relation_target,
                    relation_clip=entity.relation_clip,
                    relation_anchor=entity.relation_anchor,
                    x_offset=entity.x_offset,
                    y_offset=entity.y_offset,
                    z_index=entity.z_index,
                )
                # Add instance suffix to name for tracking
                if entity.count > 1:
                    new_entity.name = f"{entity.name}_{i+1}"
                expanded.append(new_entity)
        return expanded

    def _solve_zone_entities(self, entities: list[Entity], zone: str) -> list[LayoutResult]:
        """Solve layout for entities in a specific zone."""
        layouts = []

        if zone == "sky":
            layouts = self._solve_sky_entities(entities)
        elif zone == "ground":
            layouts = self._solve_ground_entities(entities)

        return layouts

    def _solve_sky_entities(self, entities: list[Entity]) -> list[LayoutResult]:
        """Solve layout for sky entities."""
        layouts = []
        count = len(entities)

        if count == 0:
            return layouts

        # Distribute entities across sky
        for i, entity in enumerate(entities):
            # Calculate x position (spread across frame)
            if count == 1:
                x = 0.0
            else:
                x = -self.frame_width / 2 + self.safe_margin_x + (i * (self.frame_width - 2 * self.safe_margin_x) / (count - 1))

            # Calculate y position (vary heights)
            y_variation = math.sin(i * math.pi / max(count, 1)) * 0.5
            y = 2.0 + y_variation

            # Clamp to sky bounds
            y = max(self.sky_y_min + self.safe_margin_y, min(self.sky_y_max - self.safe_margin_y, y))

            # Get asset dimensions
            width, height = self._get_asset_dimensions(entity.asset, entity.default_scale)

            layout = LayoutResult(
                entity=entity,
                x=x,
                y=y,
                width=width,
                height=height,
                anchor="center",
                scale=entity.default_scale,
                z_index=1,
            )
            layouts.append(layout)

        return layouts

    def _solve_ground_entities(self, entities: list[Entity]) -> list[LayoutResult]:
        """Solve layout for ground entities."""
        layouts = []
        count = len(entities)

        if count == 0:
            return layouts

        # Separate by category
        characters = [e for e in entities if e.category == "character"]
        structures = [e for e in entities if e.category == "structure"]
        props = [e for e in entities if e.category == "prop"]
        vehicles = [e for e in entities if e.category == "vehicle"]

        # Solve characters
        char_layouts = self._solve_characters(characters)
        layouts.extend(char_layouts)

        # Solve structures
        struct_layouts = self._solve_structures(structures)
        layouts.extend(struct_layouts)

        # Solve props
        prop_layouts = self._solve_props(props)
        layouts.extend(prop_layouts)

        # Solve vehicles
        vehicle_layouts = self._solve_vehicles(vehicles)
        layouts.extend(vehicle_layouts)

        return layouts

    def _solve_characters(self, characters: list[Entity]) -> list[LayoutResult]:
        """Solve layout for character entities."""
        layouts = []
        count = len(characters)

        if count == 0:
            return layouts

        # Distribute characters across ground
        for i, entity in enumerate(characters):
            # Calculate x position
            if count == 1:
                x = 0.0
            else:
                x = -self.frame_width / 2 + self.safe_margin_x + (i * (self.frame_width - 2 * self.safe_margin_x) / (count - 1))

            # Characters stand on ground
            y = self.ground_y

            # Get asset dimensions
            width, height = self._get_asset_dimensions(entity.asset, entity.default_scale)

            layout = LayoutResult(
                entity=entity,
                x=x,
                y=y,
                width=width,
                height=height,
                anchor="bottom",
                scale=entity.default_scale,
                z_index=5,
            )
            layouts.append(layout)

        return layouts

    def _solve_structures(self, structures: list[Entity]) -> list[LayoutResult]:
        """Solve layout for structure entities."""
        layouts = []
        count = len(structures)

        if count == 0:
            return layouts

        # Distribute structures across ground (background)
        for i, entity in enumerate(structures):
            # Calculate x position (spread wider)
            if count == 1:
                x = -self.frame_width / 4  # Offset to left
            else:
                x = -self.frame_width / 2 + self.safe_margin_x + (i * (self.frame_width - 2 * self.safe_margin_x) / (count - 1))

            # Structures sit on ground
            y = self.ground_y

            # Get asset dimensions
            width, height = self._get_asset_dimensions(entity.asset, entity.default_scale)

            layout = LayoutResult(
                entity=entity,
                x=x,
                y=y,
                width=width,
                height=height,
                anchor="bottom",
                scale=entity.default_scale,
                z_index=1,
            )
            layouts.append(layout)

        return layouts

    def _solve_props(self, props: list[Entity]) -> list[LayoutResult]:
        """Solve layout for prop entities."""
        layouts = []
        count = len(props)

        if count == 0:
            return layouts

        # Distribute props near characters or on ground
        for i, entity in enumerate(props):
            # Calculate x position (cluster near center)
            if count == 1:
                x = 0.5  # Slightly right of center
            else:
                x = -1.0 + (i * 2.0 / max(count - 1, 1))

            # Props sit on ground
            y = self.ground_y

            # Get asset dimensions
            width, height = self._get_asset_dimensions(entity.asset, entity.default_scale)

            layout = LayoutResult(
                entity=entity,
                x=x,
                y=y,
                width=width,
                height=height,
                anchor="bottom",
                scale=entity.default_scale,
                z_index=3,
            )
            layouts.append(layout)

        return layouts

    def _solve_vehicles(self, vehicles: list[Entity]) -> list[LayoutResult]:
        """Solve layout for vehicle entities."""
        layouts = []
        count = len(vehicles)

        if count == 0:
            return layouts

        # Distribute vehicles across ground
        for i, entity in enumerate(vehicles):
            # Calculate x position
            if count == 1:
                x = 0.0
            else:
                x = -self.frame_width / 2 + self.safe_margin_x + (i * (self.frame_width - 2 * self.safe_margin_x) / (count - 1))

            # Vehicles sit on ground
            y = self.ground_y

            # Get asset dimensions
            width, height = self._get_asset_dimensions(entity.asset, entity.default_scale)

            layout = LayoutResult(
                entity=entity,
                x=x,
                y=y,
                width=width,
                height=height,
                anchor="bottom",
                scale=entity.default_scale,
                z_index=2,
            )
            layouts.append(layout)

        return layouts

    def _handle_containment(self, layouts: list[LayoutResult], entities: list[Entity]) -> list[LayoutResult]:
        """Handle containment relationships (inside, on_top, etc.)."""
        # Find containers (entities that can contain others)
        containers = [e for e in entities if e.can_contain]

        for container in containers:
            # Find entities that should be inside this container
            contained_entities = [e for e in entities if e.relation == "inside" and e.relation_target == container.name]

            if not contained_entities:
                continue

            # Find container layout
            container_layout = next((l for l in layouts if l.entity.name == container.name), None)
            if not container_layout:
                continue

            # Place contained entities inside container
            for i, contained_entity in enumerate(contained_entities):
                # Find or create layout for contained entity
                contained_layout = next((l for l in layouts if l.entity.name == contained_entity.name), None)

                if contained_layout:
                    # Calculate position inside container
                    # For vehicles, use window slots
                    if container.container_type == "vehicle":
                        window_slots = self._get_vehicle_window_slots(container_layout, len(contained_entities))
                        if i < len(window_slots):
                            slot_x, slot_y = window_slots[i]
                            contained_layout.x = container_layout.x + slot_x
                            contained_layout.y = container_layout.y + slot_y
                            contained_layout.contained_in = container.name
                            contained_layout.window_slot = i
                            contained_layout.anchor = "center"
                    else:
                        # Generic containment - center inside container
                        contained_layout.x = container_layout.x
                        contained_layout.y = container_layout.y + container_layout.height * 0.3
                        contained_layout.contained_in = container.name
                        contained_layout.anchor = "center"

        return layouts

    def _get_vehicle_window_slots(self, container_layout: LayoutResult, count: int) -> list[tuple[float, float]]:
        """Get window slot positions for vehicle containment."""
        # Define window slots relative to vehicle center
        # These are approximate positions for windows in vehicles
        slots = [
            (-0.3, 0.1),  # Front left window
            (0.3, 0.1),   # Front right window
            (-0.3, -0.1), # Back left window
            (0.3, -0.1),  # Back right window
            (0.0, 0.15),  # Top center window
            (0.0, -0.15), # Bottom center window
        ]

        # Scale slots based on vehicle size
        scale_factor = container_layout.width / 2.0

        result = []
        for i in range(min(count, len(slots))):
            slot_x, slot_y = slots[i]
            result.append((slot_x * scale_factor, slot_y * scale_factor))

        return result

    def _resolve_collisions(self, layouts: list[LayoutResult]) -> list[LayoutResult]:
        """Resolve collisions between entities."""
        # Simple collision resolution - adjust positions if entities overlap
        for i, layout1 in enumerate(layouts):
            for j, layout2 in enumerate(layouts[i+1:], i+1):
                # Check if entities overlap
                if self._check_overlap(layout1, layout2):
                    # Adjust positions to resolve collision
                    self._resolve_pair_collision(layout1, layout2)

        return layouts

    def _check_overlap(self, layout1: LayoutResult, layout2: LayoutResult) -> bool:
        """Check if two layouts overlap."""
        # Calculate bounding boxes
        box1 = self._get_bounding_box(layout1)
        box2 = self._get_bounding_box(layout2)

        # Check for overlap
        return not (
            box1["right"] < box2["left"] or
            box1["left"] > box2["right"] or
            box1["top"] < box2["bottom"] or
            box1["bottom"] > box2["top"]
        )

    def _get_bounding_box(self, layout: LayoutResult) -> dict[str, float]:
        """Get bounding box for a layout."""
        # Calculate based on anchor
        if layout.anchor == "bottom":
            left = layout.x - layout.width / 2
            right = layout.x + layout.width / 2
            bottom = layout.y
            top = layout.y + layout.height
        elif layout.anchor == "top":
            left = layout.x - layout.width / 2
            right = layout.x + layout.width / 2
            bottom = layout.y - layout.height
            top = layout.y
        else:  # center
            left = layout.x - layout.width / 2
            right = layout.x + layout.width / 2
            bottom = layout.y - layout.height / 2
            top = layout.y + layout.height / 2

        return {
            "left": left,
            "right": right,
            "bottom": bottom,
            "top": top,
        }

    def _resolve_pair_collision(self, layout1: LayoutResult, layout2: LayoutResult):
        """Resolve collision between two layouts."""
        # Simple resolution: move second entity to the right
        box1 = self._get_bounding_box(layout1)
        box2 = self._get_bounding_box(layout2)

        # Calculate overlap
        overlap_x = min(box1["right"], box2["right"]) - max(box1["left"], box2["left"])
        overlap_y = min(box1["top"], box2["top"]) - max(box1["bottom"], box2["bottom"])

        # Move layout2 to the right
        if overlap_x > 0:
            layout2.x += overlap_x + 0.1

        # If still overlapping vertically, move up/down
        if overlap_y > 0:
            # Move to different y position
            if layout2.y > layout1.y:
                layout2.y += overlap_y + 0.1
            else:
                layout2.y -= overlap_y + 0.1

        # Clamp to frame bounds
        layout2.x = max(-self.frame_width / 2 + self.safe_margin_x, min(self.frame_width / 2 - self.safe_margin_x, layout2.x))
        layout2.y = max(self.ground_y_min, min(self.ground_y_max, layout2.y))

    def _assign_z_indices(self, layouts: list[LayoutResult]) -> list[LayoutResult]:
        """Assign z-indices based on entity types and positions."""
        # Sort by y position (higher y = lower z-index for background)
        layouts.sort(key=lambda l: l.y, reverse=True)

        # Assign z-indices
        for i, layout in enumerate(layouts):
            # Base z-index on category
            if layout.entity.category == "character":
                layout.z_index = 5
            elif layout.entity.category == "prop":
                layout.z_index = 3
            elif layout.entity.category == "vehicle":
                layout.z_index = 2
            elif layout.entity.category == "structure":
                layout.z_index = 1
            else:
                layout.z_index = 1

            # Adjust based on y position (higher = further back)
            if layout.y > 2.0:
                layout.z_index = max(1, layout.z_index - 1)
            elif layout.y < -1.0:
                layout.z_index = min(5, layout.z_index + 1)

        return layouts

    def _get_asset_dimensions(self, asset_path: str, scale: float) -> tuple[float, float]:
        """Get dimensions of an asset (simplified - would need actual SVG parsing)."""
        # For now, return estimated dimensions based on asset type
        # In production, this would parse the SVG to get actual dimensions

        # Estimate based on asset path
        if "plane" in asset_path:
            base_width = 2.0
            base_height = 1.0
        elif "cloud" in asset_path:
            base_width = 1.5
            base_height = 0.8
        elif "sun" in asset_path:
            base_width = 1.0
            base_height = 1.0
        elif "building" in asset_path:
            base_width = 1.5
            base_height = 3.0
        elif "tree" in asset_path:
            base_width = 1.0
            base_height = 2.0
        elif "person" in asset_path or "peep" in asset_path:
            base_width = 0.8
            base_height = 1.8
        elif "car" in asset_path:
            base_width = 2.0
            base_height = 1.0
        elif "bus" in asset_path:
            base_width = 2.5
            base_height = 1.2
        elif "train" in asset_path:
            base_width = 3.0
            base_height = 1.5
        elif "boat" in asset_path:
            base_width = 2.0
            base_height = 1.0
        else:
            base_width = 1.0
            base_height = 1.0

        # Apply scale
        width = base_width * scale * 10  # Scale factor
        height = base_height * scale * 10

        return width, height

    def validate_layout(self, layouts: list[LayoutResult]) -> list[str]:
        """Validate layout results."""
        errors = []

        for layout in layouts:
            # Check x bounds (same for all zones)
            if layout.x < -self.frame_width / 2 or layout.x > self.frame_width / 2:
                errors.append(f"Entity {layout.entity.name} x out of bounds: {layout.x}")

            # Check y bounds based on zone
            if layout.entity.zone == "sky":
                if layout.y < self.sky_y_min or layout.y > self.sky_y_max:
                    errors.append(f"Entity {layout.entity.name} y out of bounds (sky): {layout.y}")
            elif layout.entity.zone == "ground":
                if layout.y < self.ground_y_min or layout.y > self.ground_y_max:
                    errors.append(f"Entity {layout.entity.name} y out of bounds (ground): {layout.y}")

            # Check for NaN or infinite values
            if math.isnan(layout.x) or math.isinf(layout.x):
                errors.append(f"Entity {layout.entity.name} has invalid x: {layout.x}")

            if math.isnan(layout.y) or math.isinf(layout.y):
                errors.append(f"Entity {layout.entity.name} has invalid y: {layout.y}")

        return errors

    def to_json(self, layouts: list[LayoutResult]) -> list[dict[str, Any]]:
        """Convert layouts to JSON-serializable format."""
        result = []
        for layout in layouts:
            result.append({
                "entity": {
                    "name": layout.entity.name,
                    "asset": layout.entity.asset,
                    "role": layout.entity.role,
                    "zone": layout.entity.zone,
                    "scale_fraction": layout.entity.default_scale,
                    "action": layout.entity.action,
                    "motion_type": layout.entity.motion_type,
                    "motion_direction": layout.entity.motion_direction,
                    "motion_speed": layout.entity.motion_speed,
                    "relation": layout.entity.relation,
                    "relation_target": layout.entity.relation_target,
                    "relation_clip": layout.entity.relation_clip,
                    "relation_anchor": layout.entity.relation_anchor,
                },
                "x": layout.x,
                "y": layout.y,
                "width": layout.width,
                "height": layout.height,
                "anchor": layout.anchor,
                "scale": layout.scale,
                "z_index": layout.z_index,
                "contained_in": layout.contained_in,
                "window_slot": layout.window_slot,
            })
        return result
