"""Render a small SVG drawing-animation test scene with Manim.

Run from the project directory:
    python render_video.py

The renderer looks for SVGs in assets and resolves filenames containing the
roles cloud, house, person, sun, and tree. Use --asset-dir to point at another
folder containing the real illustrations.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

from manim import (
    WHITE,
    AnimationGroup,
    Create,
    DrawBorderThenFill,
    Scene,
    SVGMobject,
    config,
)

from scene_contract import CONTRACT, Role, Zone
from scene_spec import AnchorType, EntitySpec, MotionType, SceneSpec
from scene_solver import BaselineSolver, solve_scene
from svg_composition_system import SVGCompositionSystem, compose_svg_with_context


ROOT = Path(__file__).resolve().parent
DEFAULT_ASSET_DIR = ROOT / "assets" / "svgs"
DEFAULT_OUTPUT_DIR = ROOT / "output"
ROLES = ("sun", "cloud", "house", "tree", "person")


def resolve_asset(asset_dir: Path, role: str) -> Path:
    """Find one SVG whose filename contains the requested role."""
    candidates = sorted(
        path
        for path in asset_dir.rglob("*.svg")
        if role in path.stem.lower()
    )
    if not candidates:
        raise FileNotFoundError(
            f"No SVG found for role '{role}' under '{asset_dir}'. "
            f"Add an SVG with '{role}' in its filename."
        )
    return candidates[0]


def load_svg(path: Path, scale: float, position: tuple[float, float, float]) -> SVGMobject:
    """Load and place an SVG while preserving its source colors."""
    svg = SVGMobject(str(path))
    svg.scale(scale)
    svg.move_to(position)
    return svg


class DrawingTest(Scene):
    """Draw five familiar objects in a simple outdoor composition."""

    def __init__(
        self,
        asset_dir: Path,
        animation: str,
        draw_time: float,
        **kwargs: object,
    ) -> None:
        self.asset_dir = asset_dir
        self.animation = animation
        self.draw_time = draw_time
        super().__init__(**kwargs)

    def construct(self) -> None:
        self.camera.background_color = WHITE
        placements = {
            "sun": (0.9, 2.4, 0.0, 0.9),
            "cloud": (-1.9, 2.1, 0.0, 0.75),
            "house": (-1.9, -0.5, 0.0, 1.65),
            "tree": (2.1, -0.3, 0.0, 1.35),
            "person": (0.5, -1.3, 0.0, 0.95),
        }

        for role in ROLES:
            path = resolve_asset(self.asset_dir, role)
            x, y, z, scale = placements[role]
            svg = load_svg(path, scale, (x, y, z))
            animation = (
                Create(svg, run_time=self.draw_time)
                if self.animation == "create"
                else DrawBorderThenFill(svg, run_time=self.draw_time)
            )
            self.play(animation)
            self.wait(0.15)

        self.wait(1)


class JsonSvgScene(Scene):
    """Render a validated, role-based SVG layout from JSON."""

    def __init__(self, asset_dir: Path, scene_json: Path, **kwargs: object) -> None:
        self.asset_dir = asset_dir
        self.scene_json = scene_json
        super().__init__(**kwargs)

    def construct(self) -> None:
        self.camera.background_color = WHITE
        layout = json.loads(self.scene_json.read_text(encoding="utf-8"))
        if "elements" not in layout or not isinstance(layout["elements"], list):
            raise ValueError("Scene JSON must contain an 'elements' list.")
        ground_y = float(layout.get("ground_y", -2.4))

        asset_root = self.asset_dir.resolve()
        moving_groups: dict[str, list[tuple[SVGMobject, float]]] = {}
        for element in layout["elements"]:
            relative_asset = Path(element["asset"])
            path = (asset_root / relative_asset).resolve()
            if asset_root not in path.parents:
                raise ValueError(f"Asset path escapes assets/svgs/: {relative_asset}")
            if not path.is_file():
                raise FileNotFoundError(f"Scene asset not found: {relative_asset}")

            svg = SVGMobject(str(path))
            svg.set(width=float(element["width"]))
            x = float(element["x"])
            if element.get("anchor", "center") == "bottom":
                svg.move_to((x, ground_y + svg.height / 2, 0))
            else:
                svg.move_to((x, float(element["y"]), 0))
            svg.set_z_index(int(element.get("z", 0)))
            run_time = float(element.get("run_time", 1.0))
            if element.get("animation") == "create":
                animation = Create(svg, run_time=run_time)
            else:
                animation = DrawBorderThenFill(svg, run_time=run_time)
            self.play(animation)
            if float(element.get("wait", 0)) > 0:
                self.wait(float(element["wait"]))

            group = element.get("motion_group")
            if group:
                moving_groups.setdefault(str(group), []).append(
                    (svg, float(element.get("target_x", x)))
                )

        for group in moving_groups.values():
            motions = [
                mob.animate(run_time=1.8).move_to(
                    (target_x, mob.get_center()[1], mob.get_center()[2])
                )
                for mob, target_x in group
            ]
            self.play(AnimationGroup(*motions, lag_ratio=0))

        self.wait(float(layout.get("final_wait", 1.0)))


class SpecSvgScene(Scene):
    """Render a scene from a SceneSpec using the coordinate contract solver."""

    def __init__(self, asset_dir: Path, scene_spec: SceneSpec, **kwargs: object) -> None:
        self.asset_dir = asset_dir
        self.scene_spec = scene_spec
        super().__init__(**kwargs)

    def construct(self) -> None:
        self.camera.background_color = WHITE

        # Initialize composition system
        composition_system = SVGCompositionSystem(use_llm=True)

        # Solve the scene spec into concrete layouts
        solver = BaselineSolver()
        layouts = solver.solve(self.scene_spec, self.asset_dir)

        # Apply composition to entities that need it
        composed_assets: dict[str, Path] = {}
        for entity in self.scene_spec.entities:
            if entity.composition_context and entity.parent_asset:
                try:
                    result = compose_svg_with_context(
                        self.asset_dir / entity.asset_path,
                        entity.composition_context,
                        use_llm=True,
                    )
                    if result.success:
                        composed_assets[entity.asset_path] = result.modified_svg_path
                except Exception as e:
                    print(f"Composition failed for {entity.asset_path}: {e}")

        # Group motion entities
        motion_groups: dict[str, list[tuple[SVGMobject, float, float]]] = {}

        asset_root = self.asset_dir.resolve()
        for layout in layouts:
            entity = layout.entity

            # Use composed asset if available
            if entity.asset_path in composed_assets:
                path = composed_assets[entity.asset_path]
            else:
                relative_asset = Path(entity.asset_path)
                path = (asset_root / relative_asset).resolve()
                if asset_root not in path.parents:
                    raise ValueError(f"Asset path escapes assets/svgs/: {relative_asset}")
                if not path.is_file():
                    raise FileNotFoundError(f"Scene asset not found: {relative_asset}")

            svg = SVGMobject(str(path))
            # Scale to computed width
            svg.set(width=layout.width)
            # Position based on anchor
            if layout.anchor == AnchorType.BOTTOM:
                svg.move_to((layout.x, layout.y - layout.height / 2, 0))
            elif layout.anchor == AnchorType.TOP:
                svg.move_to((layout.x, layout.y + layout.height / 2, 0))
            else:
                svg.move_to((layout.x, layout.y, 0))
            svg.set_z_index(layout.z_index)

            # Animate
            run_time = entity.run_time
            if entity.animation == "create":
                animation = Create(svg, run_time=run_time)
            else:
                animation = DrawBorderThenFill(svg, run_time=run_time)
            self.play(animation)
            if entity.wait_after > 0:
                self.wait(entity.wait_after)

            # Track motion groups
            if entity.motion_group and entity.motion_type == MotionType.TRANSLATE_X:
                target_x = layout.target_x if layout.target_x is not None else layout.x
                motion_groups.setdefault(entity.motion_group, []).append(
                    (svg, target_x, svg.get_center()[1])
                )

        # Execute motion groups
        for group_name, motions in motion_groups.items():
            # Get the first entity in this group for motion_run_time
            group_entities = [e for e in self.scene_spec.entities if e.motion_group == group_name]
            if not group_entities:
                continue
            run_time = group_entities[0].motion_run_time

            animations = [
                mob.animate(run_time=run_time).move_to(
                    (target_x, current_y, mob.get_center()[2])
                )
                for mob, target_x, current_y in motions
            ]
            if animations:
                self.play(AnimationGroup(*animations, lag_ratio=0))

        self.wait(self.scene_spec.final_wait)


def load_scene_spec_from_json(json_path: Path) -> SceneSpec:
    """Load a SceneSpec from a JSON file.

    Expected JSON format:
    {
        "name": "scene_name",
        "background": "#FFFFFF",
        "final_wait": 2.0,
        "ground_y": -2.35,
        "entities": [
            {
                "asset": "path/to.svg",
                "role": "character|prop|structure|sky_entity|background|foreground",
                "zone": "sky|ground|background|foreground",
                "anchor": "bottom|center|top",
                "scale_fraction": 0.3,
                "motion_group": "group_name",
                "motion_type": "static|translate_x|translate_y|scale|fade",
                "motion_target_x": 3.0,
                "motion_target_y": 1.0,
                "motion_run_time": 1.8,
                "animation": "create|draw_border",
                "run_time": 1.0,
                "wait_after": 0.1,
                "z_index": 5,
                "x_offset": 0.0,
                "y_offset": 0.0
            }
        ]
    }
    """
    data = json.loads(json_path.read_text(encoding="utf-8"))

    spec = SceneSpec(
        name=data.get("name", json_path.stem),
        background=data.get("background", "#FFFFFF"),
        final_wait=data.get("final_wait", 2.0),
        ground_y=data.get("ground_y"),
        layout_mode=data.get("layout_mode", "auto"),
    )

    role_map = {
        "character": Role.CHARACTER,
        "prop": Role.PROP,
        "structure": Role.STRUCTURE,
        "sky_entity": Role.SKY_ENTITY,
        "background": Role.BACKGROUND,
        "foreground": Role.FOREGROUND,
    }

    zone_map = {
        "sky": Zone.SKY,
        "ground": Zone.GROUND,
        "background": Zone.BACKGROUND,
        "foreground": Zone.FOREGROUND,
    }

    anchor_map = {
        "bottom": AnchorType.BOTTOM,
        "center": AnchorType.CENTER,
        "top": AnchorType.TOP,
    }

    motion_map = {
        "static": MotionType.STATIC,
        "translate_x": MotionType.TRANSLATE_X,
        "translate_y": MotionType.TRANSLATE_Y,
        "scale": MotionType.SCALE,
        "fade": MotionType.FADE,
    }

    for entity_data in data.get("entities", []):
        role_str = entity_data.get("role", "prop")
        role = role_map.get(role_str, Role.PROP)

        zone_str = entity_data.get("zone")
        zone = zone_map.get(zone_str) if zone_str else None

        anchor_str = entity_data.get("anchor", "bottom")
        anchor = anchor_map.get(anchor_str, AnchorType.BOTTOM)

        motion_str = entity_data.get("motion_type", "static")
        motion_type = motion_map.get(motion_str, MotionType.STATIC)

        entity = EntitySpec(
            asset_path=entity_data["asset"],
            role=role,
            name=entity_data.get("name", ""),
            parent_asset=entity_data.get("parent_asset"),
            relative_offset_x=entity_data.get("relative_offset_x", 0.0),
            relative_offset_y=entity_data.get("relative_offset_y", 0.0),
            relative_anchor=anchor_map.get(entity_data.get("relative_anchor", "center"), AnchorType.CENTER),
            composition_context=entity_data.get("composition_context"),
            zone=zone,
            anchor=anchor,
            scale_fraction=entity_data.get("scale_fraction"),
            motion_group=entity_data.get("motion_group"),
            motion_type=motion_type,
            motion_target_x=entity_data.get("motion_target_x"),
            motion_target_y=entity_data.get("motion_target_y"),
            motion_run_time=entity_data.get("motion_run_time", 1.8),
            animation=entity_data.get("animation", "draw_border"),
            run_time=entity_data.get("run_time", 1.0),
            wait_after=entity_data.get("wait_after", 0.1),
            z_index=entity_data.get("z_index"),
            x_offset=entity_data.get("x_offset", 0.0),
            y_offset=entity_data.get("y_offset", 0.0),
        )
        spec.add_entity(entity)

    return spec


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--asset-dir",
        type=Path,
        default=DEFAULT_ASSET_DIR,
        help="Folder containing the SVG assets (default: assets).",
    )
    parser.add_argument(
        "--animation",
        choices=("draw_border", "create"),
        default="draw_border",
        help="SVG animation style (default: draw_border).",
    )
    parser.add_argument(
        "--draw-time",
        type=float,
        default=0.8,
        help="Seconds used to draw each asset (default: 0.8).",
    )
    parser.add_argument(
        "--quality",
        choices=("low", "medium"),
        default="low",
        help="Render quality (default: low, 480p30).",
    )
    parser.add_argument("--scene-json", type=Path)
    parser.add_argument("--scene-spec", type=Path, help="Scene spec JSON file (new format)")
    parser.add_argument("--output", type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    asset_dir = args.asset_dir.resolve()
    if not asset_dir.is_dir():
        print(f"Asset directory does not exist: {asset_dir}", file=sys.stderr)
        return 2

    config.pixel_width, config.pixel_height = (
        (854, 480) if args.quality == "low" else (1280, 720)
    )
    config.media_dir = str(DEFAULT_OUTPUT_DIR)
    config.quality = "low_quality" if args.quality == "low" else "medium_quality"
    config.frame_rate = 30
    if args.scene_spec:
        scene_spec_path = args.scene_spec.resolve()
        if not scene_spec_path.is_file():
            print(f"Scene spec does not exist: {scene_spec_path}", file=sys.stderr)
            return 2
        # Generate timestamped output filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_name = f"{scene_spec_path.stem}_{timestamp}.mp4"
        output_path = args.output.resolve() if args.output else DEFAULT_OUTPUT_DIR / output_name
        config.output_file = str(output_path)
        scene_spec = load_scene_spec_from_json(scene_spec_path)
        scene = SpecSvgScene(asset_dir=asset_dir, scene_spec=scene_spec)
    elif args.scene_json:
        scene_json = args.scene_json.resolve()
        if not scene_json.is_file():
            print(f"Scene JSON does not exist: {scene_json}", file=sys.stderr)
            return 2
        output_path = args.output.resolve() if args.output else DEFAULT_OUTPUT_DIR / f"{scene_json.stem}.mp4"
        config.output_file = str(output_path)
        scene = JsonSvgScene(asset_dir=asset_dir, scene_json=scene_json)
    else:
        try:
            missing = [role for role in ROLES if not list(asset_dir.rglob(f"*{role}*.svg"))]
            if missing:
                raise FileNotFoundError(
                    f"Missing roles: {', '.join(missing)} under '{asset_dir}'."
                )
        except OSError as error:
            print(f"Could not inspect assets: {error}", file=sys.stderr)
            return 2
        output_path = args.output.resolve() if args.output else DEFAULT_OUTPUT_DIR / f"drawing_test_{args.animation}.mp4"
        config.output_file = str(output_path)
        scene = DrawingTest(
            asset_dir=asset_dir,
            animation=args.animation,
            draw_time=args.draw_time,
        )
    try:
        scene.render()
    except (KeyError, TypeError, ValueError, FileNotFoundError, json.JSONDecodeError) as error:
        print(f"Render failed: {error}", file=sys.stderr)
        return 1
    print(f"Rendered video: {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
