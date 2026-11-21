"""Fallback template system for scene generation."""

from typing import Any


class SceneTemplate:
    """Pre-defined scene template."""

    def __init__(
        self,
        name: str,
        description: str,
        entities: list[dict[str, Any]],
        tags: list[str] | None = None,
    ):
        self.name = name
        self.description = description
        self.entities = entities
        self.tags = tags or []

    def to_spec(self) -> dict[str, Any]:
        """Convert template to scene spec."""
        return {
            "scene_name": self.name,
            "entities": self.entities.copy(),
        }


class SceneTemplateLibrary:
    """Library of pre-defined scene templates."""

    def __init__(self):
        self.templates: dict[str, SceneTemplate] = {}
        self._load_templates()

    def _load_templates(self) -> None:
        """Load all scene templates."""
        # Plane flight scene
        self.templates["plane_flight"] = SceneTemplate(
            name="Plane Flight",
            description="Plane flying up with people looking up, clouds and sun",
            tags=["plane", "flight", "people", "sky", "clouds", "sun"],
            entities=[
                {
                    "asset": "tabler/outline/plane-inflight.svg",
                    "role": "sky_entity",
                    "zone": "sky",
                    "anchor": "center",
                    "scale_fraction": 0.25,
                    "motion_group": "flight",
                    "motion_type": "translate_y",
                    "motion_target_y": 1.5,
                    "motion_run_time": 2.0,
                    "animation": "draw_border",
                    "run_time": 1.5,
                    "z_index": 10,
                },
                {
                    "asset": "open_peeps/templates_standing/peep-standing-standing-blazer-1-buns-smile-teeth-gap-none.svg",
                    "role": "character",
                    "zone": "ground",
                    "anchor": "bottom",
                    "scale_fraction": 0.12,
                    "motion_group": "people",
                    "motion_type": "static",
                    "animation": "draw_border",
                    "run_time": 1.0,
                    "z_index": 5,
                },
                {
                    "asset": "open_peeps/templates_standing/peep-standing-standing-crossed-arms-1-bun-smile-big-none.svg",
                    "role": "character",
                    "zone": "ground",
                    "anchor": "bottom",
                    "scale_fraction": 0.12,
                    "motion_group": "people",
                    "motion_type": "static",
                    "animation": "draw_border",
                    "run_time": 1.0,
                    "z_index": 5,
                },
                {
                    "asset": "open_peeps/templates_standing/peep-standing-standing-pointing-finger-1-bun-2-calm-none.svg",
                    "role": "character",
                    "zone": "ground",
                    "anchor": "bottom",
                    "scale_fraction": 0.12,
                    "motion_group": "people",
                    "motion_type": "static",
                    "animation": "draw_border",
                    "run_time": 1.0,
                    "z_index": 5,
                },
                {
                    "asset": "tabler/outline/cloud.svg",
                    "role": "sky_entity",
                    "zone": "sky",
                    "anchor": "center",
                    "scale_fraction": 0.15,
                    "motion_type": "static",
                    "animation": "draw_border",
                    "run_time": 1.0,
                    "z_index": 1,
                },
                {
                    "asset": "tabler/outline/sun.svg",
                    "role": "sky_entity",
                    "zone": "sky",
                    "anchor": "center",
                    "scale_fraction": 0.20,
                    "motion_type": "static",
                    "animation": "draw_border",
                    "run_time": 1.0,
                    "z_index": 0,
                },
            ],
        )

        # City scene
        self.templates["city_scene"] = SceneTemplate(
            name="City Scene",
            description="City skyline with buildings and people",
            tags=["city", "buildings", "people", "urban"],
            entities=[
                {
                    "asset": "tabler/outline/building-skyscraper.svg",
                    "role": "structure",
                    "zone": "ground",
                    "anchor": "bottom",
                    "scale_fraction": 0.40,
                    "motion_type": "static",
                    "animation": "draw_border",
                    "run_time": 1.5,
                    "z_index": 3,
                },
                {
                    "asset": "tabler/outline/building-skyscraper.svg",
                    "role": "structure",
                    "zone": "ground",
                    "anchor": "bottom",
                    "scale_fraction": 0.35,
                    "motion_type": "static",
                    "animation": "draw_border",
                    "run_time": 1.5,
                    "z_index": 3,
                },
                {
                    "asset": "open_peeps/templates_standing/peep-standing-standing-blazer-1-buns-smile-teeth-gap-none.svg",
                    "role": "character",
                    "zone": "ground",
                    "anchor": "bottom",
                    "scale_fraction": 0.12,
                    "motion_type": "static",
                    "animation": "draw_border",
                    "run_time": 1.0,
                    "z_index": 5,
                },
                {
                    "asset": "tabler/outline/cloud.svg",
                    "role": "sky_entity",
                    "zone": "sky",
                    "anchor": "center",
                    "scale_fraction": 0.15,
                    "motion_type": "static",
                    "animation": "draw_border",
                    "run_time": 1.0,
                    "z_index": 1,
                },
                {
                    "asset": "tabler/outline/sun.svg",
                    "role": "sky_entity",
                    "zone": "sky",
                    "anchor": "center",
                    "scale_fraction": 0.20,
                    "motion_type": "static",
                    "animation": "draw_border",
                    "run_time": 1.0,
                    "z_index": 0,
                },
            ],
        )

        # Nature scene
        self.templates["nature_scene"] = SceneTemplate(
            name="Nature Scene",
            description="Nature scene with trees, sun, and clouds",
            tags=["nature", "trees", "sun", "clouds", "outdoor"],
            entities=[
                {
                    "asset": "tabler/outline/tree.svg",
                    "role": "structure",
                    "zone": "ground",
                    "anchor": "bottom",
                    "scale_fraction": 0.35,
                    "motion_type": "static",
                    "animation": "draw_border",
                    "run_time": 1.5,
                    "z_index": 3,
                },
                {
                    "asset": "tabler/outline/cloud.svg",
                    "role": "sky_entity",
                    "zone": "sky",
                    "anchor": "center",
                    "scale_fraction": 0.15,
                    "motion_type": "static",
                    "animation": "draw_border",
                    "run_time": 1.0,
                    "z_index": 1,
                },
                {
                    "asset": "tabler/outline/sun.svg",
                    "role": "sky_entity",
                    "zone": "sky",
                    "anchor": "center",
                    "scale_fraction": 0.20,
                    "motion_type": "static",
                    "animation": "draw_border",
                    "run_time": 1.0,
                    "z_index": 0,
                },
            ],
        )

    def get_template(self, name: str) -> SceneTemplate | None:
        """Get template by name."""
        return self.templates.get(name)

    def find_templates_by_tags(self, tags: list[str]) -> list[SceneTemplate]:
        """Find templates matching any of the given tags."""
        matching = []
        tags_lower = [tag.lower() for tag in tags]

        for template in self.templates.values():
            template_tags_lower = [tag.lower() for tag in template.tags]
            if any(tag in template_tags_lower for tag in tags_lower):
                matching.append(template)

        return matching

    def get_best_template(self, description: str) -> SceneTemplate | None:
        """Get best matching template for a description."""
        # Extract keywords from description
        keywords = description.lower().split()

        # Find templates with matching tags
        matching_templates = self.find_templates_by_tags(keywords)

        if not matching_templates:
            return None

        # Return first match (could be improved with scoring)
        return matching_templates[0]

    def get_all_templates(self) -> list[SceneTemplate]:
        """Get all templates."""
        return list(self.templates.values())

    def get_template_names(self) -> list[str]:
        """Get all template names."""
        return list(self.templates.keys())
