"""Main scene generation orchestrator - ties parser and layout solver together."""

import json
import sys
import time
from pathlib import Path
from typing import Any

from scene_parser import SceneParser, SceneSpec
from layout_solver import LayoutSolver, LayoutResult, GROUND_Y
from ollama_client import OllamaClient
from chunked_spatial_reasoner import ChunkedSpatialReasoner


def show_loader(message: str, duration: float = 0.3):
    """Show a simple loading indicator."""
    for i in range(3):
        sys.stdout.write(f"\r{message}{'.' * (i + 1)}")
        sys.stdout.flush()
        time.sleep(duration / 3)
    sys.stdout.write(f"\r{message}... Done!\n")
    sys.stdout.flush()


class SceneGenerator:
    """Main scene generation orchestrator."""

    def __init__(self, asset_dir: Path | None = None, use_llm_spatial: bool = True):
        self.parser = SceneParser()
        self.layout_solver = LayoutSolver(asset_dir)
        self.asset_dir = asset_dir or Path("assets/svgs")
        self.use_llm_spatial = use_llm_spatial
        self.ollama_client = None
        self.spatial_reasoner = None

        if use_llm_spatial:
            try:
                ollama_path = r"C:\Users\USER\AppData\Local\Programs\Ollama\ollama.exe"
                self.ollama_client = OllamaClient(model="qwen2.5:0.5b", ollama_path=ollama_path, num_threads=16)
                self.spatial_reasoner = ChunkedSpatialReasoner(self.ollama_client)
            except Exception as e:
                print(f"  [WARNING] Could not initialize Ollama client: {e}")
                self.use_llm_spatial = False

    def generate(self, description: str, output_path: str | None = None) -> dict[str, Any]:
        """Generate a complete scene spec from a description."""
        print("\n" + "="*60)
        print("SCENE GENERATION")
        print("="*60)
        print(f"Description: '{description}'")
        print("="*60)

        # Step 1: Parse description with Python
        show_loader("Parsing description")
        spec = self.parser.parse(description)

        print(f"  Found {len(spec.entities)} entities")
        for entity in spec.entities:
            print(f"    - {entity.name} (count: {entity.count}, zone: {entity.zone})")

        # Step 2: Expand entities based on count
        expanded_entities = self.layout_solver._expand_entities(spec.entities)

        # Step 3: Use LLM spatial reasoning if available
        if self.use_llm_spatial and self.spatial_reasoner and len(expanded_entities) > 0:
            print("\n  Using LLM for spatial reasoning...")

            # Pre-warm Ollama to load model into RAM
            self.spatial_reasoner.pre_warm()

            # Convert entities to dict format for LLM (use original names without suffixes)
            entity_dicts = []
            name_mapping = {}  # Map original name to expanded names
            
            for e in expanded_entities:
                # Remove suffix for LLM (e.g., "cloud_1" -> "cloud")
                original_name = e.name.split('_')[0] if '_' in e.name else e.name
                
                entity_dicts.append({
                    "name": original_name,
                    "zone": e.zone,
                    "category": e.category,
                    "scale": e.default_scale,
                })
                
                # Track mapping
                if original_name not in name_mapping:
                    name_mapping[original_name] = []
                name_mapping[original_name].append(e.name)

            # Chunk 3: Spatial relationships (z-index)
            show_loader("Chunk 3: Determining z-index ordering")
            z_indices = self.spatial_reasoner.chunk3_spatial_relationships(entity_dicts)
            print(f"  Z-index: {len(z_indices)} entities ordered")

            # Chunk 4: Sky distribution
            show_loader("Chunk 4: Calculating sky coordinates")
            sky_coords = self.spatial_reasoner.chunk4_sky_distribution(entity_dicts)
            print(f"  Sky: {len(sky_coords)} entities positioned")

            # Chunk 5: Ground distribution
            show_loader("Chunk 5: Calculating ground coordinates")
            ground_coords = self.spatial_reasoner.chunk5_ground_distribution(entity_dicts)
            print(f"  Ground: {len(ground_coords)} entities positioned")

            # Chunk 6: Scaling adjustments
            show_loader("Chunk 6: Adjusting scales")
            all_coords = sky_coords + ground_coords
            scales = self.spatial_reasoner.chunk6_scaling_adjustments(entity_dicts, all_coords)
            print(f"  Scales: {len(scales)} entities adjusted")

            # Chunk 7: Collision resolution
            show_loader("Chunk 7: Resolving collisions")
            final_coords = self.spatial_reasoner.chunk7_collision_resolution(entity_dicts, all_coords, scales)
            print(f"  Collisions: {len(final_coords)} entities checked")

            # Apply LLM results to entities (map back from original names to expanded names)
            coord_map = {}
            for name, x, y in final_coords:
                if name in name_mapping:
                    for expanded_name in name_mapping[name]:
                        coord_map[expanded_name] = (x, y)
            
            z_map = {}
            for name, z in z_indices:
                if name in name_mapping:
                    for expanded_name in name_mapping[name]:
                        z_map[expanded_name] = z
            
            scale_map = {}
            for name, scale in scales:
                if name in name_mapping:
                    for expanded_name in name_mapping[name]:
                        scale_map[expanded_name] = scale

            for e in expanded_entities:
                if e.name in coord_map:
                    e.x_offset = coord_map[e.name][0]
                    e.y_offset = coord_map[e.name][1]
                if e.name in z_map:
                    e.z_index = z_map[e.name]
                if e.name in scale_map:
                    e.default_scale = scale_map[e.name]

            layouts = self._entities_to_layouts(expanded_entities)

        else:
            # Fallback to Python layout solver
            show_loader("Using Python layout solver")
            layouts = self.layout_solver.solve(spec)

        print(f"  Generated {len(layouts)} layouts")

        # Step 4: Validate layout
        show_loader("Validating layout")
        errors = self.layout_solver.validate_layout(layouts)
        if errors:
            print(f"  [WARNING] {len(errors)} validation errors:")
            for error in errors[:5]:
                print(f"    - {error}")
        else:
            print("  [OK] Layout validation passed")

        # Step 5: Convert to JSON
        show_loader("Converting to JSON")
        scene_json = self._layouts_to_scene_json(spec, layouts)

        # Step 6: Save to file
        if not output_path:
            output_path = "scenes/generated_scene.json"

        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)

        show_loader("Saving to file")
        with open(output_file, "w") as f:
            json.dump(scene_json, f, indent=2)

        print("\n" + "="*60)
        print("GENERATION COMPLETE")
        print("="*60)
        print(f"Scene spec saved to: {output_file}")
        print(f"Total entities: {len(scene_json['elements'])}")
        print(f"Scene name: {scene_json['scene_name']}")
        print("="*60 + "\n")

        return {
            "spec": scene_json,
            "output_path": str(output_file),
            "layouts": self.layout_solver.to_json(layouts),
        }

    def _entities_to_layouts(self, entities: list) -> list[LayoutResult]:
        """Convert entities to layout results."""
        layouts = []
        for e in entities:
            width, height = self.layout_solver._get_asset_dimensions(e.asset, e.default_scale)

            layout = LayoutResult(
                entity=e,
                x=e.x_offset,
                y=e.y_offset,
                width=width,
                height=height,
                anchor="bottom" if e.zone == "ground" else "center",
                scale=e.default_scale,
                z_index=e.z_index,
            )
            layouts.append(layout)
        return layouts

    def _layouts_to_scene_json(self, spec: SceneSpec, layouts: list[LayoutResult]) -> dict[str, Any]:
        """Convert layouts to scene JSON format compatible with render_video.py."""
        elements = []

        for layout in layouts:
            entity = layout.entity

            # Build element dict for render_video.py
            element_dict = {
                "asset": entity.asset,
                "role": entity.role,
                "name": entity.name,
                "zone": entity.zone,
                "anchor": layout.anchor,
                "width": layout.width,
                "x": layout.x,
                "y": layout.y,
                "z": layout.z_index,
                "scale_fraction": entity.default_scale,
                "animation": "draw_border",
                "run_time": 1.0,
                "wait": 0.15,
            }

            # Add motion parameters
            if entity.motion_type == "translate_y":
                element_dict["motion_group"] = f"{entity.name}_motion"
                element_dict["target_x"] = layout.x
                element_dict["target_y"] = layout.y + (1.5 * entity.motion_speed)
            elif entity.motion_type == "translate_x":
                element_dict["motion_group"] = f"{entity.name}_motion"
                element_dict["target_x"] = layout.x + (1.0 * entity.motion_speed)
                element_dict["target_y"] = layout.y
            elif entity.motion_type == "rotate":
                element_dict["motion_group"] = f"{entity.name}_motion"
                element_dict["target_x"] = layout.x
                element_dict["target_y"] = layout.y

            # Add containment info for composition system
            if layout.contained_in:
                element_dict["parent_asset"] = layout.contained_in
                element_dict["composition_context"] = f"inside {layout.contained_in}"

            elements.append(element_dict)

        return {
            "scene_name": spec.scene_name,
            "description": spec.description,
            "ground_y": GROUND_Y,
            "elements": elements,
        }

    def batch_generate(self, descriptions: list[str], output_dir: str = "scenes/batch") -> list[dict[str, Any]]:
        """Generate multiple scenes from a list of descriptions."""
        print("\n" + "="*60)
        print("BATCH SCENE GENERATION")
        print("="*60)
        print(f"Processing {len(descriptions)} descriptions")
        print("="*60)

        results = []
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        for i, description in enumerate(descriptions):
            print(f"\n[{i+1}/{len(descriptions)}] Processing: '{description}'")

            try:
                output_file = output_path / f"scene_{i+1}.json"
                result = self.generate(description, str(output_file))
                results.append(result)
                print(f"  [OK] Generated: {result['output_path']}")
            except Exception as e:
                print(f"  [ERROR] Failed: {e}")
                results.append({"error": str(e), "description": description})

        print("\n" + "="*60)
        print("BATCH GENERATION COMPLETE")
        print("="*60)
        print(f"Successful: {len([r for r in results if 'error' not in r])}")
        print(f"Failed: {len([r for r in results if 'error' in r])}")
        print("="*60 + "\n")

        return results


def main():
    """Main entry point."""
    # Test descriptions
    test_descriptions = [
        "plane flying up with people looking up, clouds and sun",
        "three passengers inside the plane looking out windows",
        "two buildings next to each other with a tree between them",
        "a car driving on the road with a person walking beside it",
        "sun setting over the ocean with a boat sailing",
    ]

    # Initialize generator
    generator = SceneGenerator()

    # Test single generation only
    print("\n" + "#"*60)
    print("TEST: Single Scene Generation")
    print("#"*60)
    result = generator.generate(test_descriptions[0])

    print("\n" + "="*60)
    print("TEST COMPLETE")
    print("="*60 + "\n")


if __name__ == "__main__":
    main()
