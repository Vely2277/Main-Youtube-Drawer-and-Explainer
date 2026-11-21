"""Ollama integration for LLM-based SVG composition decisions."""

from __future__ import annotations

import json
import os
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from svg_compositor import ClipInstruction
from svg_parser import SVGStructure


@dataclass
class LLMDecision:
    """Decision from LLM about SVG composition."""
    instructions: list[ClipInstruction]
    reasoning: str
    confidence: float


class OllamaClient:
    """Client for interacting with Ollama API."""

    def __init__(self, model: str = "qwen2.5:3b", ollama_path: str = "ollama", num_threads: int = 16):
        self.model = model
        self.ollama_path = ollama_path
        self.num_threads = num_threads

    def generate(self, prompt: str, json_mode: bool = True, timeout: int = 120) -> str:
        """Generate a response from the LLM.

        Args:
            prompt: The prompt to send to the LLM
            json_mode: If True, request JSON output
            timeout: Timeout in seconds (default 120)

        Returns:
            The LLM's response as a string
        """
        cmd = [self.ollama_path, "run", self.model]

        if json_mode:
            cmd.extend(["--format", "json"])
        
        # Set OLLAMA_NUM_THREADS environment variable for CPU parallelism
        env = os.environ.copy()
        env["OLLAMA_NUM_THREADS"] = str(self.num_threads)

        try:
            result = subprocess.run(
                cmd,
                input=prompt,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="ignore",
                timeout=timeout,
                env=env,
            )

            if result.returncode != 0:
                raise RuntimeError(f"Ollama error: {result.stderr}")

            return result.stdout.strip()

        except subprocess.TimeoutExpired:
            raise RuntimeError("Ollama request timed out")
        except FileNotFoundError:
            raise RuntimeError("Ollama not found. Ensure it's installed and in PATH.")

    def generate_json(self, prompt: str) -> dict:
        """Generate a JSON response from the LLM.

        Args:
            prompt: The prompt to send to the LLM

        Returns:
            The LLM's response as a parsed JSON dict
        """
        response = self.generate(prompt, json_mode=True)
        try:
            return json.loads(response)
        except json.JSONDecodeError as e:
            raise RuntimeError(f"Failed to parse LLM JSON response: {e}")


class SVGCompositionLLM:
    """LLM-based SVG composition decision maker."""

    def __init__(self, model: str = "qwen2.5:3b", ollama_path: str = "ollama"):
        self.client = OllamaClient(model, ollama_path)

    def decide_composition(
        self,
        svg_structure: SVGStructure,
        context: str,
        parent_svg_structure: SVGStructure | None = None,
    ) -> LLMDecision:
        """Decide how to compose an SVG based on context.

        Args:
            svg_structure: Parsed structure of the SVG to modify
            context: Description of composition context (e.g., "passenger inside plane")
            parent_svg_structure: Optional structure of parent SVG for reference

        Returns:
            LLMDecision with composition instructions
        """
        # Build prompt
        prompt = self._build_prompt(svg_structure, context, parent_svg_structure)

        # Query LLM
        try:
            response = self.client.generate_json(prompt)
            return self._parse_llm_response(response)
        except Exception as e:
            # Fallback to rule-based decision on error
            return self._fallback_decision(context)

    def _build_prompt(
        self,
        svg_structure: SVGStructure,
        context: str,
        parent_svg_structure: SVGStructure | None = None,
    ) -> str:
        """Build the LLM prompt."""
        prompt = f"""You are an SVG composition expert. Given an SVG structure and a composition context, decide which parts of the SVG should be hidden or clipped.

SVG Structure:
{self._format_structure(svg_structure)}

"""

        if parent_svg_structure:
            prompt += f"""Parent SVG Structure (for reference):
{self._format_structure(parent_svg_structure)}

"""

        prompt += f"""Composition Context: {context}

Analyze the SVG and determine:
1. Which elements should be hidden (by ID)
2. Whether to apply a clip path (rectangular, below Y, or above Y)
3. The specific coordinates for any clipping

Return your decision as JSON in this exact format:
{{
  "instructions": [
    {{"type": "hide_element", "target_id": "element-id"}},
    {{"type": "clip_below_y", "y": 50.0}},
    {{"type": "clip_rect", "x": 0, "y": 0, "width": 100, "height": 50}}
  ],
  "reasoning": "Explanation of your decision",
  "confidence": 0.9
}}

Only return the JSON, nothing else. Ensure the JSON is valid and complete."""
        return prompt

    def _format_structure(self, structure: SVGStructure) -> str:
        """Format SVG structure for LLM prompt."""
        lines = []

        # Metadata
        lines.append("SVG Metadata:")
        if structure.viewbox:
            lines.append(f"  viewBox: {structure.viewbox}")
        if structure.width and structure.height:
            lines.append(f"  dimensions: {structure.width} x {structure.height}")
        lines.append("")

        # Element count
        lines.append(f"Total elements: {len(structure.all_elements)}")
        lines.append("")

        # Elements with IDs
        if structure.element_by_id:
            lines.append("Elements with IDs:")
            for element_id, element in list(structure.element_by_id.items())[:30]:
                lines.append(f"  ID '{element_id}': {element.tag}")
                if element.class_name:
                    lines.append(f"    class: {element.class_name}")
            lines.append("")

        return "\n".join(lines)

    def _parse_llm_response(self, response: dict) -> LLMDecision:
        """Parse LLM JSON response into LLMDecision."""
        instructions = []

        for instr in response.get("instructions", []):
            instr_type = instr.get("type")

            if instr_type == "hide_element":
                target_id = instr.get("target_id")
                if target_id:
                    instructions.append(ClipInstruction(
                        type="hide_element",
                        target_id=target_id,
                    ))

            elif instr_type == "clip_rect":
                x = instr.get("x")
                y = instr.get("y")
                width = instr.get("width")
                height = instr.get("height")
                if all(v is not None for v in [x, y, width, height]):
                    instructions.append(ClipInstruction(
                        type="clip_rect",
                        x=float(x),
                        y=float(y),
                        width=float(width),
                        height=float(height),
                    ))

            elif instr_type == "clip_below_y":
                y = instr.get("y")
                if y is not None:
                    instructions.append(ClipInstruction(
                        type="clip_below_y",
                        y=float(y),
                    ))

            elif instr_type == "clip_above_y":
                y = instr.get("y")
                if y is not None:
                    instructions.append(ClipInstruction(
                        type="clip_above_y",
                        y=float(y),
                    ))

        reasoning = response.get("reasoning", "")
        confidence = response.get("confidence", 0.5)

        return LLMDecision(
            instructions=instructions,
            reasoning=reasoning,
            confidence=confidence,
        )

    def _fallback_decision(self, context: str) -> LLMDecision:
        """Fallback rule-based decision when LLM fails."""
        instructions = []
        context_lower = context.lower()

        if "passenger" in context_lower and ("plane" in context_lower or "car" in context_lower or "bus" in context_lower):
            instructions.append(ClipInstruction(
                type="clip_below_y",
                y=15.0,  # Assuming 24px SVG, clip at ~60%
            ))

        return LLMDecision(
            instructions=instructions,
            reasoning=f"LLM failed, using rule-based fallback for context: {context}",
            confidence=0.5,
        )


def get_ollama_path() -> str:
    """Get the path to Ollama executable."""
    # Try common paths
    common_paths = [
        "ollama",
        r"C:\Users\USER\AppData\Local\Programs\Ollama\ollama.exe",
    ]

    for path in common_paths:
        try:
            result = subprocess.run(
                [path, "--version"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0:
                return path
        except (FileNotFoundError, subprocess.TimeoutExpired):
            continue

    return "ollama"  # Default, will fail if not in PATH
