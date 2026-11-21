"""SVG compositor for clipping, masking, and merging SVGs.

Provides tools to modify SVGs for composition:
- Apply clip paths to hide parts of SVGs
- Hide specific elements by ID
- Crop SVGs to bounding boxes
- Merge multiple SVGs into one
"""

from __future__ import annotations

import copy
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path
from typing import Literal
from uuid import uuid4


@dataclass
class ClipInstruction:
    """Instruction for clipping an SVG."""
    type: Literal["hide_element", "clip_rect", "clip_below_y", "clip_above_y"]
    target_id: str | None = None  # For hide_element
    x: float | None = None  # For clip_rect
    y: float | None = None  # For clip_rect, clip_below_y, clip_above_y
    width: float | None = None  # For clip_rect
    height: float | None = None  # For clip_rect


class SVGCompositor:
    """Composes and modifies SVGs for scene rendering."""

    def __init__(self):
        self.namespaces = {
            "svg": "http://www.w3.org/2000/svg",
            "xlink": "http://www.w3.org/1999/xlink",
        }

    def load_svg(self, svg_path: Path) -> ET.Element:
        """Load an SVG file as an ElementTree."""
        tree = ET.parse(svg_path)
        root = tree.getroot()
        return root

    def save_svg(self, root: ET.Element, output_path: Path) -> None:
        """Save an SVG element to a file."""
        tree = ET.ElementTree(root)
        ET.register_namespace("", self.namespaces["svg"])
        ET.register_namespace("xlink", self.namespaces["xlink"])
        tree.write(output_path, encoding="utf-8", xml_declaration=True)

    def hide_element_by_id(self, root: ET.Element, element_id: str) -> ET.Element:
        """Hide an element by setting its display to none."""
        element = self._find_element_by_id(root, element_id)
        if element is not None:
            element.set("display", "none")
        return root

    def apply_clip_rect(
        self,
        root: ET.Element,
        x: float,
        y: float,
        width: float,
        height: float,
    ) -> ET.Element:
        """Apply a rectangular clip path to the SVG.

        Creates a clipPath element and applies it to the root's children.
        """
        # Create unique clip path ID
        clip_id = f"clip-{uuid4().hex[:8]}"

        # Find or create defs section
        defs = root.find("svg:defs", self.namespaces)
        if defs is None:
            defs = ET.Element(f"{{{self.namespaces['svg']}}}defs")
            root.insert(0, defs)

        # Create clip path
        clip_path = ET.Element(f"{{{self.namespaces['svg']}}}clipPath")
        clip_path.set("id", clip_id)

        # Create rectangle
        rect = ET.Element(f"{{{self.namespaces['svg']}}}rect")
        rect.set("x", str(x))
        rect.set("y", str(y))
        rect.set("width", str(width))
        rect.set("height", str(height))

        clip_path.append(rect)
        defs.append(clip_path)

        # Apply clip path to all direct children of root (except defs)
        for child in root:
            if child.tag != f"{{{self.namespaces['svg']}}}defs":
                child.set("clip-path", f"url(#{clip_id})")

        return root

    def clip_below_y(self, root: ET.Element, y_threshold: float) -> ET.Element:
        """Clip everything below a certain Y coordinate.

        Creates a clip path that shows only the region above y_threshold.
        """
        # Get SVG dimensions
        width = self._get_svg_dimension(root, "width", 100)
        height = self._get_svg_dimension(root, "height", 100)

        # Clip from y=0 to y=y_threshold
        return self.apply_clip_rect(root, 0, 0, width, y_threshold)

    def clip_above_y(self, root: ET.Element, y_threshold: float) -> ET.Element:
        """Clip everything above a certain Y coordinate.

        Creates a clip path that shows only the region below y_threshold.
        """
        # Get SVG dimensions
        width = self._get_svg_dimension(root, "width", 100)
        height = self._get_svg_dimension(root, "height", 100)

        # Clip from y=y_threshold to y=height
        clip_height = height - y_threshold
        return self.apply_clip_rect(root, 0, y_threshold, width, clip_height)

    def apply_instructions(
        self,
        root: ET.Element,
        instructions: list[ClipInstruction],
    ) -> ET.Element:
        """Apply a list of clip instructions to an SVG."""
        for instruction in instructions:
            if instruction.type == "hide_element" and instruction.target_id:
                root = self.hide_element_by_id(root, instruction.target_id)
            elif instruction.type == "clip_rect":
                if all(v is not None for v in [instruction.x, instruction.y, instruction.width, instruction.height]):
                    root = self.apply_clip_rect(
                        root,
                        instruction.x,
                        instruction.y,
                        instruction.width,
                        instruction.height,
                    )
            elif instruction.type == "clip_below_y" and instruction.y is not None:
                root = self.clip_below_y(root, instruction.y)
            elif instruction.type == "clip_above_y" and instruction.y is not None:
                root = self.clip_above_y(root, instruction.y)

        return root

    def merge_svgs(
        self,
        svg_roots: list[ET.Element],
        positions: list[tuple[float, float]],
        output_width: float = 100,
        output_height: float = 100,
    ) -> ET.Element:
        """Merge multiple SVGs into a single SVG.

        Args:
            svg_roots: List of SVG root elements to merge
            positions: List of (x, y) positions for each SVG
            output_width: Width of the merged output SVG
            output_height: Height of the merged output SVG

        Returns:
            Merged SVG root element
        """
        # Create new root
        merged_root = ET.Element(f"{{{self.namespaces['svg']}}}svg")
        merged_root.set("width", str(output_width))
        merged_root.set("height", str(output_height))
        merged_root.set("viewBox", f"0 0 {output_width} {output_height}")

        # Create defs section
        defs = ET.Element(f"{{{self.namespaces['svg']}}}defs")
        merged_root.append(defs)

        # Add each SVG as a group with transform
        for svg_root, (x, y) in zip(svg_roots, positions):
            group = ET.Element(f"{{{self.namespaces['svg']}}}g")
            group.set("transform", f"translate({x}, {y})")

            # Copy all children from source SVG (except defs)
            for child in svg_root:
                if child.tag != f"{{{self.namespaces['svg']}}}defs":
                    group.append(copy.deepcopy(child))

            merged_root.append(group)

        return merged_root

    def _find_element_by_id(self, root: ET.Element, element_id: str) -> ET.Element | None:
        """Find an element by its ID attribute."""
        # Search recursively
        for element in root.iter():
            if element.get("id") == element_id:
                return element
        return None

    def _get_svg_dimension(self, root: ET.Element, attr: str, default: float) -> float:
        """Get a dimension attribute from SVG root."""
        value = root.get(attr)
        if value is None:
            return default

        # Parse dimension (handle units)
        value = value.strip()
        for unit in ["px", "pt", "em", "rem", "%"]:
            if value.endswith(unit):
                value = value[:-len(unit)]

        try:
            return float(value)
        except ValueError:
            return default

    def compose_svg(
        self,
        svg_path: Path,
        instructions: list[ClipInstruction],
        output_path: Path | None = None,
    ) -> ET.Element:
        """Load, modify, and optionally save an SVG.

        Args:
            svg_path: Path to source SVG
            instructions: List of clip instructions to apply
            output_path: Optional path to save modified SVG

        Returns:
            Modified SVG root element
        """
        root = self.load_svg(svg_path)
        root = self.apply_instructions(root, instructions)

        if output_path:
            self.save_svg(root, output_path)

        return root


def compose_svg(
    svg_path: Path,
    instructions: list[ClipInstruction],
    output_path: Path | None = None,
) -> ET.Element:
    """Convenience function to compose an SVG."""
    compositor = SVGCompositor()
    return compositor.compose_svg(svg_path, instructions, output_path)
