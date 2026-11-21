"""Coordinate contract system for scene composition.

Defines zones, baselines, safe margins, and scale ratios that all scenes must follow.
This replaces hardcoded coordinates with a deterministic layout system.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Literal


class Zone(Enum):
    """Spatial zones in the scene."""
    SKY = "sky"
    GROUND = "ground"
    BACKGROUND = "background"
    FOREGROUND = "foreground"


class Role(Enum):
    """Entity roles that determine placement rules."""
    CHARACTER = "character"
    PROP = "prop"
    STRUCTURE = "structure"
    SKY_ENTITY = "sky_entity"
    BACKGROUND = "background"
    FOREGROUND = "foreground"


@dataclass(frozen=True)
class CoordinateContract:
    """Global coordinate contract for all scenes.

    All positions are in Manim's coordinate system (center origin, y-up).
    Frame is 16:9 aspect ratio.
    """
    # Frame dimensions (Manim units)
    FRAME_WIDTH: float = 14.22  # 16:9 at 720p
    FRAME_HEIGHT: float = 8.0    # 16:9 at 720p

    # Safe margins (percentage of frame)
    SAFE_MARGIN_LEFT: float = 0.08   # 8% from left edge
    SAFE_MARGIN_RIGHT: float = 0.08  # 8% from right edge
    SAFE_MARGIN_TOP: float = 0.10    # 10% from top
    SAFE_MARGIN_BOTTOM: float = 0.10 # 10% from bottom

    # Zone boundaries (y-coordinates)
    SKY_ZONE_TOP: float = 2.5        # Top of sky zone
    SKY_ZONE_BOTTOM: float = 0.5     # Bottom of sky zone (above ground)
    GROUND_ZONE_TOP: float = 0.5     # Top of ground zone
    GROUND_ZONE_BOTTOM: float = -3.5 # Bottom of ground zone

    # Baselines
    GROUND_Y: float = -2.35          # Master ground baseline
    HORIZON_Y: float = 0.0           # Horizon line (sky/ground boundary)

    # Scale ratios (as fraction of frame height)
    SCALE_RATIOS: dict[Role, tuple[float, float]] = None

    def __post_init__(self):
        if self.SCALE_RATIOS is None:
            object.__setattr__(self, 'SCALE_RATIOS', {
                Role.CHARACTER: (0.25, 0.32),      # 25-32% of frame height
                Role.PROP: (0.08, 0.14),           # 8-14% of frame height
                Role.STRUCTURE: (0.40, 0.50),      # 40-50% of frame height
                Role.SKY_ENTITY: (0.15, 0.25),     # 15-25% of frame height
                Role.BACKGROUND: (0.30, 0.45),     # 30-45% of frame height
                Role.FOREGROUND: (0.20, 0.35),     # 20-35% of frame height
            })

    @property
    def safe_left(self) -> float:
        """Left safe boundary in Manim coordinates."""
        return -self.FRAME_WIDTH / 2 + (self.FRAME_WIDTH * self.SAFE_MARGIN_LEFT)

    @property
    def safe_right(self) -> float:
        """Right safe boundary in Manim coordinates."""
        return self.FRAME_WIDTH / 2 - (self.FRAME_WIDTH * self.SAFE_MARGIN_RIGHT)

    @property
    def safe_top(self) -> float:
        """Top safe boundary in Manim coordinates."""
        return self.FRAME_HEIGHT / 2 - (self.FRAME_HEIGHT * self.SAFE_MARGIN_TOP)

    @property
    def safe_bottom(self) -> float:
        """Bottom safe boundary in Manim coordinates."""
        return -self.FRAME_HEIGHT / 2 + (self.FRAME_HEIGHT * self.SAFE_MARGIN_BOTTOM)

    @property
    def ground_span(self) -> tuple[float, float]:
        """Available horizontal span for ground entities."""
        return (self.safe_left, self.safe_right)

    @property
    def sky_span(self) -> tuple[float, float]:
        """Available horizontal span for sky entities."""
        return (self.safe_left, self.safe_right)

    def get_scale_range(self, role: Role) -> tuple[float, float]:
        """Get min/max scale as fraction of frame height for a role."""
        return self.SCALE_RATIOS.get(role, (0.1, 0.3))

    def scale_to_height(self, role: Role, target_fraction: float | None = None) -> float:
        """Convert role-based scale fraction to Manim height units.

        Args:
            role: Entity role
            target_fraction: Optional specific fraction (0.0-1.0). If None, uses midpoint.

        Returns:
            Height in Manim units
        """
        min_frac, max_frac = self.get_scale_range(role)
        if target_fraction is None:
            target_fraction = (min_frac + max_frac) / 2
        return self.FRAME_HEIGHT * target_fraction

    def zone_for_role(self, role: Role) -> Zone:
        """Determine which zone a role belongs to."""
        zone_map = {
            Role.CHARACTER: Zone.GROUND,
            Role.PROP: Zone.GROUND,
            Role.STRUCTURE: Zone.GROUND,
            Role.SKY_ENTITY: Zone.SKY,
            Role.BACKGROUND: Zone.BACKGROUND,
            Role.FOREGROUND: Zone.FOREGROUND,
        }
        return zone_map.get(role, Zone.GROUND)

    def y_range_for_zone(self, zone: Zone) -> tuple[float, float]:
        """Get y-coordinate range for a zone."""
        ranges = {
            Zone.SKY: (self.SKY_ZONE_BOTTOM, self.SKY_ZONE_TOP),
            Zone.GROUND: (self.GROUND_ZONE_BOTTOM, self.GROUND_ZONE_TOP),
            Zone.BACKGROUND: (self.GROUND_ZONE_BOTTOM, self.HORIZON_Y),
            Zone.FOREGROUND: (self.GROUND_ZONE_BOTTOM, self.GROUND_ZONE_TOP),
        }
        return ranges.get(zone, (self.GROUND_ZONE_BOTTOM, self.GROUND_ZONE_TOP))


# Global contract instance
CONTRACT = CoordinateContract()
