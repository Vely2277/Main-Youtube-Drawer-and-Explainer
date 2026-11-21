"""Test script for SVG composition system with LLM."""

from pathlib import Path

from svg_composition_system import compose_svg_with_context


def test_passenger_composition():
    """Test composing a passenger SVG for the plane scene."""
    asset_dir = Path("assets/svgs")
    passenger_path = asset_dir / "open_peeps/templates_sitting/peep-sitting-sitting-crossed-legs-long-afro-smile-none.svg"

    if not passenger_path.exists():
        print(f"Passenger SVG not found: {passenger_path}")
        return

    # Compose with context
    context = "passenger sitting inside a plane, hide legs below the body"
    result = compose_svg_with_context(
        passenger_path,
        context,
        use_llm=True,
    )

    if result.success:
        print(f"[OK] Composition successful")
        print(f"  Modified SVG: {result.modified_svg_path}")
        print(f"  Instructions: {len(result.instructions)}")
        for instr in result.instructions:
            print(f"    - {instr.type}: {instr}")
    else:
        print(f"[FAIL] Composition failed: {result.error}")


if __name__ == "__main__":
    test_passenger_composition()
