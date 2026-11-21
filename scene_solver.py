"""Baseline solver: computes concrete coordinates from SceneSpec.

This is the core engine that transforms role-based entity descriptions
into actual x, y, width, height, z_index values following the coordinate contract.
Supports parent-child relationships and group-based layout.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Literal

from manim import SVGMobject

from scene_contract import CONTRACT, CoordinateContract, Role, Zone
from scene_spec import AnchorType, ComputedLayout, EntitySpec, SceneSpec


class EntityGroup:
    """A group of entities that move together (parent + children)."""
    def __init__(self, parent: EntitySpec | None = None):
        self.parent = parent
        self.children: list[EntitySpec] = []
        self.entities: list[EntitySpec] = []
        self.bounding_box: tuple[float, float, float, float] | None = None  # (left, right, top, bottom)

    def add_entity(self, entity: EntitySpec) -> None:
        self.entities.append(entity)
        if entity.parent_asset is None:
            self.parent = entity
        else:
            self.children.append(entity)

    def compute_bounds(self, layouts: dict[str, ComputedLayout]) -> None:
        """Compute bounding box of all entities in group."""
        if not self.entities:
            return

        lefts, rights, tops, bottoms = [], [], [], []
        for entity in self.entities:
            layout = layouts.get(entity.asset_path)
            if layout:
                lefts.append(layout.x - layout.width / 2)
                rights.append(layout.x + layout.width / 2)
                tops.append(layout.y + layout.height / 2)
                bottoms.append(layout.y - layout.height / 2)

        if lefts:
            self.bounding_box = (min(lefts), max(rights), max(tops), min(bottoms))


class BaselineSolver:
    """Solves SceneSpec into concrete ComputedLayout positions.

    Applies the coordinate contract to compute:
    - Horizontal positions (x) with collision avoidance
    - Vertical positions (y) based on zone and anchor
    - Scale (width/height) based on role ratios
    - Z-order based on zone and role
    - Parent-child relative positioning
    - Group-based layout for motion groups
    """

    def __init__(self, contract: CoordinateContract | None = None):
        self.contract = contract or CONTRACT
        self._svg_cache: dict[str, SVGMobject] = {}

    def solve(self, spec: SceneSpec, asset_dir: Path) -> list[ComputedLayout]:
        """Solve a SceneSpec into concrete layouts.

        Args:
            spec: Scene specification with entities
            asset_dir: Root directory containing SVG assets

        Returns:
            List of ComputedLayout with concrete coordinates
        """
        # Group entities by parent-child relationships and motion groups
        groups = self._build_entity_groups(spec)

        # Solve each zone separately
        zone_groups: dict[Zone, list[EntityGroup]] = {}
        for group in groups:
            zone = group.parent.zone if group.parent else Zone.GROUND
            zone_groups.setdefault(zone, []).append(group)

        layouts: list[ComputedLayout] = []
        layout_map: dict[str, ComputedLayout] = {}

        # Solve zones in order: background, sky, ground, foreground
        zone_order = [Zone.BACKGROUND, Zone.SKY, Zone.GROUND, Zone.FOREGROUND]
        for zone in zone_order:
            if zone in zone_groups:
                zone_layouts = self._solve_zone_groups(zone_groups[zone], spec, asset_dir)
                layouts.extend(zone_layouts)
                for layout in zone_layouts:
                    layout_map[layout.entity.asset_path] = layout

        # Position children relative to parents
        self._position_children(layout_map, spec)

        # Resolve collisions between entities in same zone
        layouts = self._resolve_collisions(layouts, spec)

        # Sort by z_index for rendering order
        layouts.sort(key=lambda l: l.z_index)
        return layouts

    def _build_entity_groups(self, spec: SceneSpec) -> list[EntityGroup]:
        """Build entity groups based on parent-child and motion_group relationships."""
        groups: list[EntityGroup] = []
        entity_to_group: dict[str, EntityGroup] = {}

        # First pass: create groups for parents and standalone entities
        for entity in spec.entities:
            if entity.parent_asset is None:
                # This is a parent or standalone entity
                group = EntityGroup(parent=entity)
                group.add_entity(entity)
                groups.append(group)
                entity_to_group[entity.asset_path] = group

        # Second pass: assign children to their parents' groups
        for entity in spec.entities:
            if entity.parent_asset is not None:
                # Find parent's group
                parent_group = entity_to_group.get(entity.parent_asset)
                if parent_group:
                    parent_group.add_entity(entity)
                    entity_to_group[entity.asset_path] = parent_group
                else:
                    # Parent not found, treat as standalone
                    group = EntityGroup(parent=entity)
                    group.add_entity(entity)
                    groups.append(group)
                    entity_to_group[entity.asset_path] = group

        # Third pass: merge groups with same motion_group
        motion_groups: dict[str, list[EntityGroup]] = {}
        for group in groups:
            if group.parent and group.parent.motion_group:
                motion_groups.setdefault(group.parent.motion_group, []).append(group)

        # Merge motion groups
        merged_groups: list[EntityGroup] = []
        merged_motion_groups: set[str] = set()

        for group in groups:
            if group.parent and group.parent.motion_group:
                mg_name = group.parent.motion_group
                if mg_name not in merged_motion_groups:
                    # Merge all groups with this motion_group
                    merged = EntityGroup()
                    for g in motion_groups[mg_name]:
                        for entity in g.entities:
                            merged.add_entity(entity)
                    merged_groups.append(merged)
                    merged_motion_groups.add(mg_name)
            else:
                merged_groups.append(group)

        return merged_groups

    def _solve_zone_groups(
        self,
        groups: list[EntityGroup],
        spec: SceneSpec,
        asset_dir: Path,
    ) -> list[ComputedLayout]:
        """Solve layout for entity groups in a zone."""
        if not groups:
            return []

        # Load SVGs and compute dimensions for ALL entities (including children)
        entity_data: dict[str, dict] = {}
        for group in groups:
            for entity in group.entities:
                # Use XML parsing for dimensions to avoid Manim file locking
                width, height = self._compute_dimensions(entity, asset_dir=asset_dir)
                entity_data[entity.asset_path] = {
                    "entity": entity,
                    "width": width,
                    "height": height,
                }

        # Distribute groups across zone
        layouts = self._distribute_groups(groups, entity_data, spec, asset_dir)
        return layouts

    def _distribute_groups(
        self,
        groups: list[EntityGroup],
        entity_data: dict[str, dict],
        spec: SceneSpec,
        asset_dir: Path,
    ) -> list[ComputedLayout]:
        """Distribute entity groups across the available span."""
        layouts = []

        # Get zone from first group's parent
        if not groups or not groups[0].parent:
            return layouts

        zone = groups[0].parent.zone or Zone.GROUND
        span_left, span_right = self.contract.ground_span if zone == Zone.GROUND else self.contract.sky_span
        available_width = span_right - span_left

        # Calculate total width needed (using group bounding boxes)
        total_width = 0
        for group in groups:
            if group.parent:
                # Use parent's width as group width for now
                # Children will be positioned relative to parent
                parent_data = entity_data.get(group.parent.asset_path)
                if parent_data:
                    total_width += parent_data["width"]

        min_gap = 0.3
        required_width = total_width + (min_gap * (len(groups) - 1))

        # Determine starting position
        if required_width <= available_width:
            # Groups fit comfortably - center them
            group_width = required_width
            start_x = span_left + (available_width - group_width) / 2
        else:
            # Groups don't fit - start from left edge
            start_x = span_left

        # Position each group
        current_x = start_x
        for group in groups:
            if not group.parent:
                continue

            parent_data = entity_data.get(group.parent.asset_path)
            if not parent_data:
                continue

            entity = group.parent
            width = parent_data["width"]
            height = parent_data["height"]

            # Calculate group center x
            group_center_x = current_x + width / 2

            # Position parent
            if entity.anchor == AnchorType.BOTTOM:
                ground_y = spec.ground_y or self.contract.GROUND_Y
                y = ground_y + height / 2 + entity.y_offset
            else:
                y_min, y_max = self.contract.y_range_for_zone(zone)
                y = (y_min + y_max) / 2 + entity.y_offset

            x = group_center_x + entity.x_offset

            layout = self._create_layout(entity, x, y, width, height)
            layouts.append(layout)

            # Position children relative to parent
            for child in group.children:
                child_layout = self._position_child_relative(child, layout, entity_data, asset_dir)
                if child_layout:
                    layouts.append(child_layout)

            current_x += width + min_gap

        return layouts

    def _position_child_relative(
        self,
        child: EntitySpec,
        parent_layout: ComputedLayout,
        entity_data: dict[str, dict],
        asset_dir: Path,
    ) -> ComputedLayout | None:
        """Position a child entity relative to its parent."""
        child_data = entity_data.get(child.asset_path)
        if not child_data:
            # Compute dimensions using XML parsing to avoid Manim file issues
            width, height = self._compute_dimensions(child, asset_dir=asset_dir)
            child_data = {
                "entity": child,
                "width": width,
                "height": height,
            }
            entity_data[child.asset_path] = child_data

        # Calculate child position relative to parent center
        child_x = parent_layout.x + child.relative_offset_x
        child_y = parent_layout.y + child.relative_offset_y

        # Adjust for child's anchor
        if child.relative_anchor == AnchorType.CENTER:
            pass  # Already centered
        elif child.relative_anchor == AnchorType.BOTTOM:
            child_y -= child_data["height"] / 2
        elif child.relative_anchor == AnchorType.TOP:
            child_y += child_data["height"] / 2

        return self._create_layout(child, child_x, child_y, child_data["width"], child_data["height"])

    def _solve_zone(
        self,
        zone: Zone,
        entities: list[EntitySpec],
        asset_dir: Path,
        spec: SceneSpec,
    ) -> list[ComputedLayout]:
        """Solve layout for entities in a single zone (legacy method)."""
        # This is kept for backward compatibility but should not be used
        # The new solve method uses _solve_zone_groups instead
        return []

    def _solve_sky_zone(
        self,
        svg_data: list[dict],
        spec: SceneSpec,
    ) -> list[ComputedLayout]:
        """Solve layout for sky entities (legacy)."""
        return []

    def _solve_ground_zone(
        self,
        svg_data: list[dict],
        spec: SceneSpec,
    ) -> list[ComputedLayout]:
        """Solve layout for ground entities (legacy)."""
        return []

    def _solve_bottom_anchored(
        self,
        svg_data: list[dict],
        ground_y: float,
        spec: SceneSpec,
    ) -> list[ComputedLayout]:
        """Solve layout for entities anchored to bottom (legacy)."""
        return []

    def _solve_compressed(
        self,
        svg_data: list[dict],
        ground_y: float,
        spec: SceneSpec,
        layouts: list[ComputedLayout],
    ) -> None:
        """Solve layout when entities don't fit (legacy)."""
        pass

    def _solve_center_anchored(
        self,
        svg_data: list[dict],
        spec: SceneSpec,
    ) -> list[ComputedLayout]:
        """Solve layout for center-anchored entities (legacy)."""
        return []

    def _solve_background_zone(
        self,
        svg_data: list[dict],
        spec: SceneSpec,
    ) -> list[ComputedLayout]:
        """Solve layout for background entities (legacy)."""
        return []

    def _solve_foreground_zone(
        self,
        svg_data: list[dict],
        spec: SceneSpec,
    ) -> list[ComputedLayout]:
        """Solve layout for foreground entities (legacy)."""
        return []

    def _compute_sky_y(
        self,
        entity: EntitySpec,
        y_min: float,
        y_max: float,
        index: int,
        total: int,
    ) -> float:
        """Compute y position for sky entity (legacy)."""
        return (y_min + y_max) / 2

    def _compute_dimensions(self, entity: EntitySpec, svg: SVGMobject | None = None, asset_dir: Path | None = None) -> tuple[float, float]:
        """Compute width and height for an entity based on role and scale.

        Uses SVG viewBox dimensions to avoid Manim file locking issues.
        """
        # Get target height from contract
        if entity.scale_fraction is not None:
            target_height = self.contract.FRAME_HEIGHT * entity.scale_fraction
        else:
            target_height = self.contract.scale_to_height(entity.role)

        # Try to get dimensions from SVG XML first (avoids Manim file issues)
        if asset_dir is not None:
            svg_path = asset_dir / entity.asset_path
            if svg_path.exists():
                try:
                    tree = ET.parse(svg_path)
                    root = tree.getroot()
                    viewbox = root.get("viewBox", "")
                    if viewbox:
                        parts = viewbox.split()
                        if len(parts) == 4:
                            vb_width = float(parts[2])
                            vb_height = float(parts[3])
                            if vb_height > 0:
                                aspect_ratio = vb_width / vb_height
                                width = target_height * aspect_ratio
                                return (width, target_height)
                except Exception:
                    pass  # Fall back to SVGMobject

        # Fallback to SVGMobject if XML parsing fails
        if svg is not None:
            current_height = svg.height
            if current_height == 0:
                return (1.0, 1.0)
            scale_factor = target_height / current_height
            width = svg.width * scale_factor
            return (width, target_height)

        # Last resort: assume square aspect ratio
        return (target_height, target_height)

    def _create_layout(
        self,
        entity: EntitySpec,
        x: float,
        y: float,
        width: float,
        height: float,
    ) -> ComputedLayout:
        """Create a ComputedLayout from solved data."""
        # Compute z_index if not specified
        z_index = entity.z_index
        if z_index is None:
            z_index = self._compute_z_index(entity)

        # Compute motion targets
        target_x = entity.motion_target_x
        target_y = entity.motion_target_y

        return ComputedLayout(
            entity=entity,
            x=x,
            y=y,
            width=width,
            height=height,
            z_index=z_index,
            anchor=entity.anchor,
            target_x=target_x,
            target_y=target_y,
        )

    def _compute_z_index(self, entity: EntitySpec) -> int:
        """Compute z_index based on zone and role."""
        zone = entity.zone or self.contract.zone_for_role(entity.role)

        # Base z_index by zone
        zone_z = {
            Zone.BACKGROUND: 0,
            Zone.SKY: 1,
            Zone.GROUND: 2,
            Zone.FOREGROUND: 3,
        }

        base_z = zone_z.get(zone, 2)

        # Adjust by role within zone
        role_offset = {
            Role.BACKGROUND: 0,
            Role.STRUCTURE: 1,
            Role.SKY_ENTITY: 0,
            Role.CHARACTER: 2,
            Role.PROP: 3,
            Role.FOREGROUND: 4,
        }

        return base_z * 10 + role_offset.get(entity.role, 5)

    def _load_svg(self, asset_path: str, asset_dir: Path) -> SVGMobject:
        """Load SVG with caching."""
        cache_key = str(asset_dir / asset_path)
        if cache_key not in self._svg_cache:
            svg = SVGMobject(cache_key)
            self._svg_cache[cache_key] = svg
        return self._svg_cache[cache_key]

    def _position_children(self, layout_map: dict[str, ComputedLayout], spec: SceneSpec) -> None:
        """Position child entities relative to their parents."""
        for entity in spec.entities:
            if entity.parent_asset and entity.parent_asset in layout_map:
                parent_layout = layout_map[entity.parent_asset]
                child_layout = layout_map.get(entity.asset_path)
                if child_layout:
                    # Recalculate child position relative to parent
                    child_layout.x = parent_layout.x + entity.relative_offset_x
                    child_layout.y = parent_layout.y + entity.relative_offset_y

    def _resolve_collisions(self, layouts: list[ComputedLayout], spec: SceneSpec) -> list[ComputedLayout]:
        """Resolve collisions between entities in the same zone.

        Uses bounding box overlap detection and pushes entities apart
        along the x-axis while respecting safe margins.
        """
        if not layouts:
            return layouts

        # Group layouts by zone
        zone_layouts: dict[Zone, list[ComputedLayout]] = {}
        for layout in layouts:
            zone = layout.entity.zone or self.contract.zone_for_role(layout.entity.role)
            zone_layouts.setdefault(zone, []).append(layout)

        # Resolve collisions for each zone
        for zone, zone_items in zone_layouts.items():
            if len(zone_items) <= 1:
                continue

            # Sort by x position for left-to-right processing
            zone_items.sort(key=lambda l: l.x)

            # Get safe bounds for this zone
            if zone == Zone.GROUND:
                safe_left, safe_right = self.contract.ground_span
            elif zone == Zone.SKY:
                safe_left, safe_right = self.contract.sky_span
            else:
                safe_left, safe_right = self.contract.ground_span

            # Iterative collision resolution
            max_iterations = 10
            for _ in range(max_iterations):
                collisions_found = False

                for i in range(len(zone_items)):
                    for j in range(i + 1, len(zone_items)):
                        layout1 = zone_items[i]
                        layout2 = zone_items[j]

                        # Check if bounding boxes overlap
                        if self._boxes_overlap(layout1, layout2):
                            collisions_found = True
                            # Push apart along x-axis
                            self._push_apart(layout1, layout2, safe_left, safe_right)

                if not collisions_found:
                    break

        return layouts

    def _boxes_overlap(self, layout1: ComputedLayout, layout2: ComputedLayout) -> bool:
        """Check if two entity bounding boxes overlap.

        Uses AABB (Axis-Aligned Bounding Box) collision detection.
        """
        # Calculate bounding boxes
        left1 = layout1.x - layout1.width / 2
        right1 = layout1.x + layout1.width / 2
        top1 = layout1.y + layout1.height / 2
        bottom1 = layout1.y - layout1.height / 2

        left2 = layout2.x - layout2.width / 2
        right2 = layout2.x + layout2.width / 2
        top2 = layout2.y + layout2.height / 2
        bottom2 = layout2.y - layout2.height / 2

        # Check for overlap on both axes
        # Two boxes overlap if they overlap on BOTH x and y axes
        overlap_x = left1 < right2 and right1 > left2
        overlap_y = top1 > bottom2 and bottom1 < top2

        return overlap_x and overlap_y

    def _push_apart(
        self,
        layout1: ComputedLayout,
        layout2: ComputedLayout,
        safe_left: float,
        safe_right: float,
    ) -> None:
        """Push two overlapping entities apart along x-axis.

        Calculates the minimum distance needed to separate them
        and moves them apart symmetrically while respecting safe bounds.
        """
        # Calculate current positions and widths
        left1 = layout1.x - layout1.width / 2
        right1 = layout1.x + layout1.width / 2
        left2 = layout2.x - layout2.width / 2
        right2 = layout2.x + layout2.width / 2

        # Determine which entity is on the left
        if layout1.x < layout2.x:
            left_entity, right_entity = layout1, layout2
            left_left, left_right = left1, right1
            right_left, right_right = left2, right2
        else:
            left_entity, right_entity = layout2, layout1
            left_left, left_right = left2, right2
            right_left, right_right = left1, right1

        # Calculate overlap amount
        overlap = left_right - right_left
        if overlap <= 0:
            return  # No overlap

        # Add minimum gap
        min_gap = 0.3
        total_push = overlap + min_gap

        # Calculate how much to push each entity
        # Push left entity left, right entity right
        push_each = total_push / 2

        # Check if we can push without violating safe bounds
        new_left_x = left_entity.x - push_each
        new_right_x = right_entity.x + push_each

        # Calculate new bounding boxes
        new_left_left = new_left_x - left_entity.width / 2
        new_right_right = new_right_x + right_entity.width / 2

        # If pushing would violate safe bounds, adjust
        if new_left_left < safe_left:
            # Can't push left entity further left
            # Push right entity more instead
            extra_push = safe_left - new_left_left
            new_left_x = left_entity.x - push_each + extra_push / 2
            new_right_x = right_entity.x + push_each + extra_push / 2
        elif new_right_right > safe_right:
            # Can't push right entity further right
            # Push left entity more instead
            extra_push = new_right_right - safe_right
            new_left_x = left_entity.x - push_each - extra_push / 2
            new_right_x = right_entity.x + push_each - extra_push / 2

        # Apply new positions
        if layout1.x < layout2.x:
            layout1.x = new_left_x
            layout2.x = new_right_x
        else:
            layout1.x = new_right_x
            layout2.x = new_left_x


def solve_scene(spec: SceneSpec, asset_dir: Path) -> list[ComputedLayout]:
    """Convenience function to solve a scene spec."""
    solver = BaselineSolver()
    return solver.solve(spec, asset_dir)
