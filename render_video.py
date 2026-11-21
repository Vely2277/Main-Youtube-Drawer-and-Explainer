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
    if args.scene_json:
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
