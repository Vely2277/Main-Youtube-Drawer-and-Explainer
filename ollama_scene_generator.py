"""Ollama integration with retry logic for scene generation."""

import json
from typing import Any

from ollama_client import OllamaClient, get_ollama_path
from scene_schema import validate_schema
from scene_validator import SceneValidator


class OllamaSceneGenerator:
    """Generate scene specs using Ollama with validation and retry logic."""

    def __init__(self, asset_dir, model: str = "qwen2.5:3b", max_retries: int = 3):
        self.asset_dir = asset_dir
        self.model = model
        self.max_retries = max_retries
        self.client = OllamaClient(model=model, ollama_path=get_ollama_path())
        self.validator = SceneValidator(asset_dir)

    def generate_scene(self, description: str) -> dict[str, Any]:
        """Generate a scene spec from a natural language description."""
        # Try template first
        from scene_templates import SceneTemplateLibrary

        template_lib = SceneTemplateLibrary()
        template = template_lib.get_best_template(description)

        if template:
            spec = template.to_spec()
            # Validate template
            errors = self.validator.validate_spec(spec)
            if not errors:
                return spec

        # Generate with Ollama
        for attempt in range(self.max_retries):
            try:
                spec = self._generate_with_ollama(description, attempt)
                if spec:
                    # Validate spec
                    errors = self.validator.validate_spec(spec)
                    if not errors:
                        return spec
                    else:
                        # Retry with error feedback
                        description = self._add_error_feedback(description, errors)
                else:
                    # Ollama failed, try again
                    continue
            except Exception as e:
                print(f"Attempt {attempt + 1} failed: {e}")
                continue

        # All retries failed, return None
        return None

    def _generate_with_ollama(self, description: str, attempt: int) -> dict[str, Any] | None:
        """Generate scene spec using Ollama."""
        prompt = self._build_prompt(description, attempt)

        try:
            response = self.client.generate(prompt, json_mode=False)
            return self._parse_response(response)
        except Exception as e:
            print(f"Ollama generation failed: {e}")
            return None

    def _build_prompt(self, description: str, attempt: int) -> str:
        """Build prompt for Ollama."""
        base_prompt = f"""You are a scene specification generator for an SVG animation system.

SCENARIO: "{description}"

FRAME SPECS:
- Aspect ratio: 16:9
- Frame width: ~14.22 units
- Frame height: 8 units
- Ground baseline: y = -2.35
- Safe margins: 8% horizontal, 10% vertical
- Sky zone: y > 0
- Ground zone: y < 0

ZONES:
- SKY: y > 0 (sky entities, plane)
- GROUND: y < 0 (characters, structures)
- BACKGROUND: z_index 0-2
- FOREGROUND: z_index 5+

SCALE FRACTIONS (relative to frame height):
- Characters: 0.20-0.40
- Props: 0.05-0.20
- Structures: 0.25-0.60
- Sky entities: 0.08-0.30
- Background: 0.30-0.80
- Foreground: 0.15-0.50

AVAILABLE ASSETS:
- tabler/outline/plane-inflight.svg (plane)
- tabler/outline/cloud.svg (cloud)
- tabler/outline/sun.svg (sun)
- tabler/outline/building-skyscraper.svg (buildings)
- open_peeps/templates_standing/*.svg (standing people)

SCENE SPEC JSON FORMAT:
{{
  "scene_name": "name",
  "entities": [
    {{
      "asset": "path/to/svg",
      "role": "character|prop|structure|sky_entity|background|foreground",
      "zone": "sky|ground|background|foreground",
      "anchor": "bottom|center|top",
      "scale_fraction": 0.0-1.0,
      "parent_asset": "path (optional)",
      "relative_offset_x": 0.0,
      "relative_offset_y": 0.0,
      "relative_anchor": "center",
      "composition_context": "description (optional)",
      "motion_group": "group_name (optional)",
      "motion_type": "static|translate_x|translate_y|scale|fade",
      "motion_target_x": 0.0,
      "motion_target_y": 0.0,
      "motion_run_time": 1.8,
      "animation": "create|draw_border",
      "run_time": 1.0,
      "wait_after": 0.1,
      "z_index": 0
    }}
  ]
}}

RULES:
- Plane should be in sky zone, flying upward (translate_y)
- People should be in ground zone
- Clouds and sun in sky zone
- Use scale_fraction between 0.05 and 0.4 for most entities
- Use motion_group for synchronized movement
- Add composition_context for people if they need clipping
- Ensure no overlapping entities
- Use proper z-index for depth (background=0-2, foreground=5+)

Return ONLY the JSON, nothing else."""

        if attempt > 0:
            base_prompt += f"\n\nThis is attempt {attempt + 1}. Please ensure the JSON is valid and complete."

        return base_prompt

    def _parse_response(self, response: str) -> dict[str, Any] | None:
        """Parse Ollama response into scene spec."""
        try:
            # Try to find JSON in response
            lines = response.strip().split("\n")
            json_start = -1
            json_end = -1
            brace_count = 0

            for i, line in enumerate(lines):
                if "{" in line and json_start == -1:
                    json_start = i
                if json_start != -1:
                    brace_count += line.count("{") - line.count("}")
                    if brace_count == 0:
                        json_end = i + 1
                        break

            if json_start != -1 and json_end != -1:
                json_text = "\n".join(lines[json_start:json_end])
                return json.loads(json_text)
            else:
                # Try parsing whole response
                return json.loads(response)
        except json.JSONDecodeError as e:
            print(f"Failed to parse JSON: {e}")
            return None

    def _add_error_feedback(self, description: str, errors: list[str]) -> str:
        """Add error feedback to description for retry."""
        error_text = "\n\nPrevious attempt had these errors:\n"
        for error in errors[:5]:  # Limit to first 5 errors
            error_text += f"- {error}\n"
        error_text += "\nPlease fix these issues and try again."

        return description + error_text

    def generate_scene_with_fallback(self, description: str) -> dict[str, Any]:
        """Generate scene with fallback to templates if Ollama fails."""
        # Try Ollama first
        spec = self.generate_scene(description)
        if spec:
            return spec

        # Fallback to template
        from scene_templates import SceneTemplateLibrary

        template_lib = SceneTemplateLibrary()
        template = template_lib.get_best_template(description)

        if template:
            return template.to_spec()

        # Last resort: return a minimal valid spec
        return {
            "scene_name": "Default Scene",
            "entities": [
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
                }
            ],
        }
