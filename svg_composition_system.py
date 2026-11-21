"""SVG composition system with LLM-driven decisions.

Orchestrates SVG parsing, LLM decision-making, and SVG modification
to handle complex composition scenarios like passengers inside vehicles.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

from svg_compositor import ClipInstruction, SVGCompositor, compose_svg
from svg_parser import SVGParser, SVGStructure, svg_to_llm_context
from ollama_client import SVGCompositionLLM, get_ollama_path


@dataclass
class CompositionRequest:
    """Request for SVG composition."""
    svg_path: Path
    context: str  # Description of composition context (e.g., "passenger inside plane")
    parent_svg_path: Path | None = None  # Optional parent SVG for reference
    output_path: Path | None = None  # Optional output path


@dataclass
class CompositionResult:
    """Result of SVG composition."""
    modified_svg_path: Path
    instructions: list[ClipInstruction]
    llm_decision: str | None = None
    success: bool = True
    error: str | None = None


@dataclass
class LLMDecision:
    """Decision from LLM about SVG composition."""
    instructions: list[ClipInstruction]
    reasoning: str
    confidence: float


class SVGCompositionSystem:
    """System for composing SVGs with LLM assistance."""

    def __init__(self, use_llm: bool = True, model_name: str = "qwen2.5:3b"):
        self.use_llm = use_llm
        self.model_name = model_name
        self.parser = SVGParser()
        self.compositor = SVGCompositor()
        self.decision_cache: dict[str, LLMDecision] = {}

        # Initialize LLM if enabled
        if self.use_llm:
            ollama_path = get_ollama_path()
            self.llm = SVGCompositionLLM(model=model_name, ollama_path=ollama_path)
        else:
            self.llm = None

    def compose(self, request: CompositionRequest) -> CompositionResult:
        """Compose an SVG based on the request.

        Args:
            request: Composition request with SVG path and context

        Returns:
            CompositionResult with modified SVG and applied instructions
        """
        try:
            # Parse SVG structure
            structure = self.parser.parse(request.svg_path)

            # Get composition instructions
            instructions = self._get_instructions(request, structure)

            # Apply instructions
            output_path = request.output_path or self._get_output_path(request.svg_path)
            self.compositor.compose_svg(
                request.svg_path,
                instructions,
                output_path,
            )

            return CompositionResult(
                modified_svg_path=output_path,
                instructions=instructions,
                success=True,
            )

        except Exception as e:
            return CompositionResult(
                modified_svg_path=request.svg_path,
                instructions=[],
                success=False,
                error=str(e),
            )

    def _get_instructions(
        self,
        request: CompositionRequest,
        structure: SVGStructure,
    ) -> list[ClipInstruction]:
        """Get composition instructions (from LLM or rules)."""
        if self.use_llm:
            return self._get_llm_instructions(request, structure)
        else:
            return self._get_rule_based_instructions(request, structure)

    def _get_llm_instructions(
        self,
        request: CompositionRequest,
        structure: SVGStructure,
    ) -> list[ClipInstruction]:
        """Get instructions from LLM."""
        if self.llm is None:
            return self._get_rule_based_instructions(request, structure)

        # Check cache first
        cache_key = self._make_cache_key(request.svg_path, request.context)
        if cache_key in self.decision_cache:
            return self.decision_cache[cache_key].instructions

        # Parse parent SVG if provided
        parent_structure = None
        if request.parent_svg_path:
            try:
                parent_structure = self.parser.parse(request.parent_svg_path)
            except Exception:
                pass  # Continue without parent structure

        # Query LLM
        try:
            decision = self.llm.decide_composition(structure, request.context, parent_structure)

            # Cache decision
            self.decision_cache[cache_key] = decision

            return decision.instructions

        except Exception as e:
            # Fallback to rule-based on error
            print(f"LLM error, falling back to rules: {e}")
            return self._get_rule_based_instructions(request, structure)

    def _get_rule_based_instructions(
        self,
        request: CompositionRequest,
        structure: SVGStructure,
    ) -> list[ClipInstruction]:
        """Get instructions from rule-based system."""
        instructions = []

        context_lower = request.context.lower()

        # Rule: Passenger in vehicle - clip legs
        if "passenger" in context_lower and ("plane" in context_lower or "car" in context_lower or "bus" in context_lower):
            # Clip below 60% of height (hide legs)
            if structure.height:
                clip_y = structure.height * 0.6
                instructions.append(ClipInstruction(
                    type="clip_below_y",
                    y=clip_y,
                ))
            else:
                # Fallback if height unknown
                instructions.append(ClipInstruction(
                    type="clip_below_y",
                    y=400.0,  # Conservative clip for large SVGs
                ))

        # Rule: Character behind object - clip top
        elif "behind" in context_lower:
            if structure.height:
                clip_y = structure.height * 0.4
                instructions.append(ClipInstruction(
                    type="clip_above_y",
                    y=clip_y,
                ))

        # Rule: Hide specific elements by ID pattern
        for element in structure.all_elements:
            if element.id:
                # Hide legs
                if "leg" in element.id.lower():
                    instructions.append(ClipInstruction(
                        type="hide_element",
                        target_id=element.id,
                    ))

        return instructions

    def _make_cache_key(self, svg_path: Path, context: str) -> str:
        """Create cache key for LLM decisions."""
        return f"{svg_path}:{context}"

    def _get_output_path(self, input_path: Path) -> Path:
        """Generate output path for modified SVG."""
        # Create composed directory
        composed_dir = input_path.parent.parent / "composed"
        composed_dir.mkdir(exist_ok=True)

        # Create subdirectory based on original path
        relative_path = input_path.relative_to(input_path.parent.parent)
        output_path = composed_dir / relative_path
        output_path.parent.mkdir(parents=True, exist_ok=True)

        return output_path

    def clear_cache(self) -> None:
        """Clear the LLM decision cache."""
        self.decision_cache.clear()


def compose_svg_with_context(
    svg_path: Path,
    context: str,
    output_path: Path | None = None,
    use_llm: bool = False,
) -> CompositionResult:
    """Convenience function to compose an SVG with context."""
    system = SVGCompositionSystem(use_llm=use_llm)
    request = CompositionRequest(
        svg_path=svg_path,
        context=context,
        output_path=output_path,
    )
    return system.compose(request)
