"""Scene specification data structures.

Defines role-based entity descriptions without hardcoded coordinates.
The solver computes actual positions from these specs.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Literal

from scene_contract import Role, Zone, CONTRACT


class AnchorType(Enum):
    """How an entity is anchored to its position."""
    BOTTOM = "bottom"      # Bottom edge at baseline
    CENTER = "center"      # Center at position
    TOP = "top"           # Top edge at position


class MotionType(Enum):
    """Types of motion an entity can perform."""
    STATIC = "static"           # No movement
    TRANSLATE_X = "translate_x" # Move horizontally
    TRANSLATE_Y = "translate_y" # Move vertically
    SCALE = "scale"            # Scale up/down
    FADE = "fade"              # Fade in/out


@dataclass
class EntitySpec:
    """Specification for a single entity in a scene.

    Describes what the entity is and how it should behave,
    without specifying exact coordinates.
    """
    # Identity
    asset_path: str                    # Path to SVG file
    role: Role                         # Entity role (character, prop, etc.)
    name: str = ""                     # Optional name for reference

    # Parent-child relationship
    parent_asset: str | None = None    # Path to parent entity's asset (for relative positioning)
    relative_offset_x: float = 0.0     # X offset from parent's center
    relative_offset_y: float = 0.0     # Y offset from parent's center
    relative_anchor: AnchorType = AnchorType.CENTER  # How to anchor to parent

    # Composition context (for SVG modification)
    composition_context: str | None = None  # Description for LLM composition (e.g., "passenger inside plane")

    # Placement hints (not exact coordinates)
    zone: Zone | None = None           # Override zone (auto-detected from role if None)
    anchor: AnchorType = AnchorType.BOTTOM

    # Scale (as fraction of frame height, or None for auto)
    scale_fraction: float | None = None

    # Motion
    motion_group: str | None = None    # Group name for synchronized motion
    motion_type: MotionType = MotionType.STATIC
    motion_target_x: float | None = None  # Target x for translate_x
    motion_target_y: float | None = None  # Target y for translate_y
    motion_run_time: float = 1.8       # Duration of motion

    # Animation
    animation: Literal["create", "draw_border"] = "draw_border"
    run_time: float = 1.0              # Draw animation duration
    wait_after: float = 0.1            # Wait after drawing

    # Z-order (auto-assigned if None)
    z_index: int | None = None

    # Offsets within zone (relative positioning)
    x_offset: float = 0.0              # Horizontal offset from computed position
    y_offset: float = 0.0              # Vertical offset from computed position

    def __post_init__(self):
        if self.zone is None:
            self.zone = CONTRACT.zone_for_role(self.role)


@dataclass
class SceneSpec:
    """Complete scene specification.

    Describes all entities and their relationships without coordinates.
    The solver computes actual layout from this spec.
    """
    name: str
    entities: list[EntitySpec] = field(default_factory=list)

    # Scene-level settings
    background: str = "#FFFFFF"
    final_wait: float = 2.0

    # Layout hints
    ground_y: float | None = None      # Override ground baseline (None = use contract)
    layout_mode: Literal["auto", "left_to_right", "center_out", "custom"] = "auto"

    def add_entity(self, entity: EntitySpec) -> None:
        """Add an entity to the scene."""
        self.entities.append(entity)

    def get_entities_by_zone(self, zone: Zone) -> list[EntitySpec]:
        """Get all entities in a specific zone."""
        return [e for e in self.entities if e.zone == zone]

    def get_entities_by_role(self, role: Role) -> list[EntitySpec]:
        """Get all entities with a specific role."""
        return [e for e in self.entities if e.role == role]

    def get_motion_groups(self) -> dict[str, list[EntitySpec]]:
        """Group entities by motion_group name."""
        groups: dict[str, list[EntitySpec]] = {}
        for entity in self.entities:
            if entity.motion_group:
                groups.setdefault(entity.motion_group, []).append(entity)
        return groups


@dataclass
class ComputedLayout:
    """Result of solving a SceneSpec into concrete coordinates."""
    entity: EntitySpec
    x: float
    y: float
    width: float
    height: float
    z_index: int
    anchor: AnchorType

    # Motion targets (if applicable)
    target_x: float | None = None
    target_y: float | None = None
