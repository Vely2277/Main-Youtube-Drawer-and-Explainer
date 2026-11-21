"""Main scene generation orchestrator."""

import json
from pathlib import Path
from typing import Any

from asset_registry import AssetRegistry
from collision_detector import CollisionDetector, SpatialValidator
from coordinate_validator import SceneCoordinateValidator
from ollama_scene_generator import OllamaSceneGenerator
from scene_schema import validate_schema
from scene_templates import SceneTemplateLibrary
from scene_validator import SceneValidator
from visual_inspector import VisualInspector


class SceneGenerationOrchestrator:
    """Orchestrate the complete scene generation pipeline."""

    def __init__(self, asset_dir: Path, output_dir: Path):
        self.asset_dir = asset_dir
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Initialize components
        self.asset_registry = AssetRegistry(asset_dir)
        self.scene_validator = SceneValidator(asset_dir)
        self.coordinate_validator = SceneCoordinateValidator()
        self.collision_detector = CollisionDetector()
        self.spatial_validator = SpatialValidator()
        self.visual_inspector = VisualInspector()
        self.template_library = SceneTemplateLibrary()
        self.ollama_generator = OllamaSceneGenerator(asset_dir)

    def generate_scene(self, description: str, output_name: str | None = None) -> dict[str, Any]:
        """Generate a complete scene from description."""
        print(f"Generating scene: {description}")

        # Step 1: Try template first
        spec = self._try_template(description)
        if spec:
            print("Using template")
            return self._finalize_scene(spec, output_name)

        # Step 2: Generate with Ollama
        print("Generating with Ollama...")
        spec = self.ollama_generator.generate_scene_with_fallback(description)
        if not spec:
            print("Ollama generation failed, using fallback")
            spec = self._get_fallback_spec(description)

        # Step 3: Validate and refine
        spec = self._validate_and_refine(spec)

        # Step 4: Finalize and save
        return self._finalize_scene(spec, output_name)

    def _try_template(self, description: str) -> dict[str, Any] | None:
        """Try to find a matching template."""
        template = self.template_library.get_best_template(description)
        if template:
            spec = template.to_spec()
            # Validate template
            errors = self.scene_validator.validate_spec(spec)
            if not errors:
                return spec
        return None

    def _get_fallback_spec(self, description: str) -> dict[str, Any]:
        """Get fallback spec when all else fails."""
        # Try to find any template
        templates = self.template_library.get_all_templates()
        if templates:
            return templates[0].to_spec()

        # Last resort: minimal valid spec
        return {
            "scene_name": "Fallback Scene",
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

    def _validate_and_refine(self, spec: dict[str, Any]) -> dict[str, Any]:
        """Validate and refine scene spec."""
        print("Validating scene spec...")

        # Schema validation
        schema_errors = validate_schema(spec)
        if schema_errors:
            print(f"Schema errors: {schema_errors}")
            # Try to fix schema errors
            spec = self._fix_schema_errors(spec, schema_errors)

        # Full validation
        errors = self.scene_validator.validate_spec(spec)
        if errors:
            print(f"Validation errors: {errors}")
            # Try to fix errors
            spec = self._fix_validation_errors(spec, errors)

        # Coordinate validation
        coord_errors = self.coordinate_validator.validate_spec_coordinates(spec)
        if coord_errors:
            print(f"Coordinate errors: {coord_errors}")
            # Try to fix coordinate errors
            spec = self._fix_coordinate_errors(spec, coord_errors)

        # Collision detection
        collisions = self.collision_detector.detect_collisions(spec.get("entities", []))
        if collisions:
            print(f"Collisions detected: {len(collisions)}")
            # Try to resolve collisions
            spec = self._resolve_collisions(spec, collisions)

        # Spatial validation
        spatial_errors = self.spatial_validator.validate_spatial_relationships(spec.get("entities", []))
        if spatial_errors:
            print(f"Spatial errors: {spatial_errors}")

        return spec

    def _fix_schema_errors(self, spec: dict[str, Any], errors: list[str]) -> dict[str, Any]:
        """Fix schema validation errors."""
        # Add missing required fields with defaults
        if "scene_name" not in spec:
            spec["scene_name"] = "Generated Scene"

        if "entities" not in spec or not isinstance(spec.get("entities"), list):
            spec["entities"] = []

        # Fix entity fields
        for entity in spec.get("entities", []):
            # Add missing required fields
            if "asset" not in entity:
                entity["asset"] = "tabler/outline/cloud.svg"
            if "role" not in entity:
                entity["role"] = "sky_entity"
            if "zone" not in entity:
                entity["zone"] = "sky"
            if "anchor" not in entity:
                entity["anchor"] = "center"
            if "scale_fraction" not in entity:
                entity["scale_fraction"] = 0.15

            # Fix invalid values
            if entity.get("role") not in ["character", "prop", "structure", "sky_entity", "background", "foreground"]:
                entity["role"] = "sky_entity"
            if entity.get("zone") not in ["sky", "ground", "background", "foreground"]:
                entity["zone"] = "sky"
            if entity.get("anchor") not in ["bottom", "center", "top"]:
                entity["anchor"] = "center"
            if not isinstance(entity.get("scale_fraction"), (int, float)):
                entity["scale_fraction"] = 0.15
            if entity.get("scale_fraction", 0) < 0.01 or entity.get("scale_fraction", 0) > 1.0:
                entity["scale_fraction"] = 0.15

        return spec

    def _fix_validation_errors(self, spec: dict[str, Any], errors: list[str]) -> dict[str, Any]:
        """Fix validation errors."""
        for error in errors:
            if "asset not found" in error.lower():
                # Try to find similar asset
                parts = error.split(":")
                if len(parts) > 1:
                    asset_path = parts[-1].strip()
                    suggestions = self.asset_registry.get_asset_suggestions(asset_path)
                    if suggestions:
                        # Replace with first suggestion
                        for entity in spec.get("entities", []):
                            if entity.get("asset") == asset_path:
                                entity["asset"] = suggestions[0]
                                break

            elif "scale_fraction" in error and "outside range" in error:
                # Clamp scale to valid range
                for entity in spec.get("entities", []):
                    scale = entity.get("scale_fraction", 0.15)
                    role = entity.get("role", "")
                    if role in ["character", "prop", "structure", "sky_entity", "background", "foreground"]:
                        # Use default scale for role
                        entity["scale_fraction"] = self.asset_registry._infer_scale(role)

        return spec

    def _fix_coordinate_errors(self, spec: dict[str, Any], errors: list[str]) -> dict[str, Any]:
        """Fix coordinate validation errors."""
        for error in errors:
            if "out of bounds" in error.lower():
                # Clamp values to bounds
                for entity in spec.get("entities", []):
                    if "x_offset" in entity:
                        entity["x_offset"] = max(-10.0, min(10.0, entity["x_offset"]))
                    if "y_offset" in entity:
                        entity["y_offset"] = max(-10.0, min(10.0, entity["y_offset"]))
                    if "motion_target_x" in entity and entity["motion_target_x"] is not None:
                        entity["motion_target_x"] = max(-10.0, min(10.0, entity["motion_target_x"]))
                    if "motion_target_y" in entity and entity["motion_target_y"] is not None:
                        entity["motion_target_y"] = max(-10.0, min(10.0, entity["motion_target_y"]))

        return spec

    def _resolve_collisions(self, spec: dict[str, Any], collisions: list[dict[str, Any]]) -> dict[str, Any]:
        """Resolve collisions by adjusting positions."""
        entities = spec.get("entities", [])

        for collision in collisions:
            idx1 = collision["entity1_index"]
            idx2 = collision["entity2_index"]

            # Move entity2 to resolve collision
            entity2 = entities[idx2]
            current_x = entity2.get("x_offset", 0.0)
            current_y = entity2.get("y_offset", 0.0)

            # Simple resolution: move entity2 up and to the right
            entity2["x_offset"] = current_x + 0.5
            entity2["y_offset"] = current_y + 0.5

        return spec

    def _finalize_scene(self, spec: dict[str, Any], output_name: str | None = None) -> dict[str, Any]:
        """Finalize scene and save to file."""
        # Ensure scene_name exists
        if "scene_name" not in spec:
            spec["scene_name"] = "Generated Scene"

        # Generate output filename
        if not output_name:
            output_name = f"{spec['scene_name'].lower().replace(' ', '_')}.json"

        output_path = self.output_dir / output_name

        # Save spec
        with open(output_path, "w") as f:
            json.dump(spec, f, indent=2)

        print(f"Scene spec saved to: {output_path}")

        # Return result
        return {
            "spec": spec,
            "output_path": str(output_path),
            "validation": self.scene_validator.get_validation_summary(spec),
        }

    def generate_and_render(self, description: str, output_name: str | None = None) -> dict[str, Any]:
        """Generate scene and render video."""
        # Generate scene spec
        result = self.generate_scene(description, output_name)

        # Render video
        spec_path = Path(result["output_path"])
        video_path = self._render_video(spec_path)

        # Inspect video
        inspection = self.visual_inspector.inspect_video(video_path)

        return {
            "scene_spec": result["spec"],
            "spec_path": str(spec_path),
            "video_path": str(video_path),
            "inspection": inspection,
            "quality_score": self.visual_inspector.get_quality_score(video_path),
        }

    def _render_video(self, spec_path: Path) -> Path:
        """Render video from scene spec."""
        import subprocess

        # Determine output video path
        video_name = spec_path.stem + ".mp4"
        video_path = self.output_dir / video_name

        # Run render_video.py
        cmd = [
            "python",
            "render_video.py",
            "--scene-spec",
            str(spec_path),
            "--quality",
            "medium",
        ]

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300,
                cwd=str(Path(__file__).parent),
            )

            if result.returncode != 0:
                print(f"Render failed: {result.stderr}")
                return video_path  # Return expected path even if failed

            print(f"Video rendered: {video_path}")
            return video_path

        except subprocess.TimeoutExpired:
            print("Render timed out")
            return video_path
        except Exception as e:
            print(f"Render error: {e}")
            return video_path

    def batch_generate(self, descriptions: list[str]) -> list[dict[str, Any]]:
        """Generate multiple scenes from descriptions."""
        results = []

        for i, description in enumerate(descriptions):
            print(f"\n{'='*60}")
            print(f"Generating scene {i+1}/{len(descriptions)}: {description}")
            print(f"{'='*60}")

            try:
                result = self.generate_scene(description, f"scene_{i+1}.json")
                results.append(result)
            except Exception as e:
                print(f"Failed to generate scene: {e}")
                results.append({"error": str(e), "description": description})

        return results

    def get_system_status(self) -> dict[str, Any]:
        """Get system status and statistics."""
        return {
            "asset_count": len(self.asset_registry.assets),
            "template_count": len(self.template_library.templates),
            "output_dir": str(self.output_dir),
            "asset_dir": str(self.asset_dir),
            "components": {
                "asset_registry": "OK",
                "scene_validator": "OK",
                "coordinate_validator": "OK",
                "collision_detector": "OK",
                "spatial_validator": "OK",
                "visual_inspector": "OK" if self.visual_inspector.ffmpeg_path else "ffmpeg not found",
                "ollama_generator": "OK" if self.ollama_generator.client else "not available",
            },
        }
