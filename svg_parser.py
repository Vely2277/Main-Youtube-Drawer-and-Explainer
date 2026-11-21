"""SVG structure parser for LLM context generation.

Extracts SVG structure (groups, paths, IDs) to provide
semantic information to the LLM for composition decisions.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class SVGElement:
    """Represents a single element in an SVG."""
    tag: str
    id: str | None
    class_name: str | None
    attributes: dict[str, str]
    children: list[SVGElement]
    path_data: str | None = None  # For <path> elements
    text_content: str = ""


@dataclass
class SVGStructure:
    """Parsed structure of an SVG file."""
    root: SVGElement
    viewbox: tuple[float, float, float, float] | None
    width: float | None
    height: float | None
    all_elements: list[SVGElement]
    element_by_id: dict[str, SVGElement]


class SVGParser:
    """Parses SVG files to extract structure for LLM context."""

    def parse(self, svg_path: Path) -> SVGStructure:
        """Parse an SVG file and extract its structure.

        Args:
            svg_path: Path to the SVG file

        Returns:
            SVGStructure with parsed elements
        """
        tree = ET.parse(svg_path)
        root = tree.getroot()

        # Extract metadata
        viewbox = self._parse_viewbox(root)
        width = self._parse_dimension(root.get("width"))
        height = self._parse_dimension(root.get("height"))

        # Parse element tree
        root_element = self._parse_element(root)
        all_elements = self._collect_elements(root_element)
        element_by_id = {e.id: e for e in all_elements if e.id}

        return SVGStructure(
            root=root_element,
            viewbox=viewbox,
            width=width,
            height=height,
            all_elements=all_elements,
            element_by_id=element_by_id,
        )

    def _parse_viewbox(self, root: ET.Element) -> tuple[float, float, float, float] | None:
        """Parse viewBox attribute."""
        viewbox_str = root.get("viewBox", "")
        if not viewbox_str:
            return None

        parts = viewbox_str.split()
        if len(parts) != 4:
            return None

        try:
            return (float(parts[0]), float(parts[1]), float(parts[2]), float(parts[3]))
        except ValueError:
            return None

    def _parse_dimension(self, dim_str: str | None) -> float | None:
        """Parse width/height dimension (handles units)."""
        if not dim_str:
            return None

        # Remove units (px, pt, em, etc.)
        dim_str = dim_str.strip()
        for unit in ["px", "pt", "em", "rem", "%"]:
            if dim_str.endswith(unit):
                dim_str = dim_str[:-len(unit)]

        try:
            return float(dim_str)
        except ValueError:
            return None

    def _parse_element(self, element: ET.Element) -> SVGElement:
        """Recursively parse an SVG element."""
        tag = self._local_name(element.tag)
        element_id = element.get("id")
        class_name = element.get("class")

        # Collect attributes
        attributes = dict(element.attrib)

        # Extract path data if applicable
        path_data = element.get("d") if tag == "path" else None

        # Get text content
        text_content = "".join(element.itertext()).strip()

        # Parse children
        children = []
        for child in element:
            children.append(self._parse_element(child))

        return SVGElement(
            tag=tag,
            id=element_id,
            class_name=class_name,
            attributes=attributes,
            children=children,
            path_data=path_data,
            text_content=text_content,
        )

    def _collect_elements(self, element: SVGElement) -> list[SVGElement]:
        """Recursively collect all elements in the tree."""
        elements = [element]
        for child in element.children:
            elements.extend(self._collect_elements(child))
        return elements

    def _local_name(self, tag: str) -> str:
        """Extract local name from namespaced tag."""
        if "}" in tag:
            return tag.split("}")[1]
        return tag

    def to_llm_context(self, structure: SVGStructure, max_elements: int = 50) -> str:
        """Generate a text description of SVG structure for LLM context.

        Args:
            structure: Parsed SVG structure
            max_elements: Maximum number of elements to include (to avoid context overflow)

        Returns:
            Text description suitable for LLM prompt
        """
        lines = []

        # Metadata
        lines.append("SVG Metadata:")
        if structure.viewbox:
            lines.append(f"  viewBox: {structure.viewbox}")
        if structure.width and structure.height:
            lines.append(f"  dimensions: {structure.width} x {structure.height}")
        lines.append("")

        # Element count
        total_elements = len(structure.all_elements)
        lines.append(f"Total elements: {total_elements}")
        lines.append("")

        # Element hierarchy
        lines.append("Element Structure:")
        self._format_element_tree(structure.root, lines, indent=2, max_elements=max_elements)
        lines.append("")

        # Elements by ID (for easy reference)
        if structure.element_by_id:
            lines.append("Elements with IDs:")
            for element_id, element in list(structure.element_by_id.items())[:max_elements]:
                lines.append(f"  ID '{element_id}': {element.tag}")
                if element.class_name:
                    lines.append(f"    class: {element.class_name}")
                if element.path_data:
                    lines.append(f"    path: {element.path_data[:50]}...")
            lines.append("")

        return "\n".join(lines)

    def _format_element_tree(
        self,
        element: SVGElement,
        lines: list[str],
        indent: int,
        max_elements: int,
        count: list[int] = [0],
    ) -> None:
        """Format element tree for LLM context."""
        if count[0] >= max_elements:
            return

        prefix = " " * indent
        tag_line = f"{prefix}{element.tag}"

        if element.id:
            tag_line += f" id='{element.id}'"
        if element.class_name:
            tag_line += f" class='{element.class_name}'"

        lines.append(tag_line)
        count[0] += 1

        for child in element.children:
            self._format_element_tree(child, lines, indent + 2, max_elements, count)


def parse_svg(svg_path: Path) -> SVGStructure:
    """Convenience function to parse an SVG file."""
    parser = SVGParser()
    return parser.parse(svg_path)


def svg_to_llm_context(svg_path: Path, max_elements: int = 50) -> str:
    """Convenience function to get LLM context from SVG."""
    parser = SVGParser()
    structure = parser.parse(svg_path)
    return parser.to_llm_context(structure, max_elements)
