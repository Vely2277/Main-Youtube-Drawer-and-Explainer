"""Main chunked workflow orchestrator."""

import json
import sys
import time
from pathlib import Path

from chunked_step1_extract import step1_extract_elements
from chunked_step2_roles import step2_assign_roles
from chunked_step3_coordinates import step3_generate_coordinates
from chunked_step4_motion import step4_add_motion
from chunked_step5_combine import step5_combine_spec


def show_loader(message: str, duration: float = 0.5):
    """Show a simple loading indicator."""
    for i in range(3):
        sys.stdout.write(f"\r{message}{'.' * (i + 1)}")
        sys.stdout.flush()
        time.sleep(duration / 3)
    sys.stdout.write(f"\r{message}... Done!\n")
    sys.stdout.flush()


def generate_scene_chunked(description: str, output_path: str | None = None) -> dict[str, any]:
    """Generate scene spec using chunked workflow."""
    print("\n" + "="*60)
    print("CHUNKED SCENE GENERATION")
    print("="*60)
    print(f"Description: '{description}'")
    print("="*60)

    # Step 1: Extract elements
    show_loader("Initializing")
    step1_result = step1_extract_elements(description)
    elements = step1_result["elements"]

    # Step 2: Assign roles
    show_loader("Processing elements")
    step2_result = step2_assign_roles(elements)
    assignments = step2_result["assignments"]

    # Step 3: Generate coordinates
    show_loader("Calculating positions")
    step3_result = step3_generate_coordinates(assignments)
    coordinates = step3_result["coordinates"]

    # Step 4: Add motion
    show_loader("Adding animations")
    step4_result = step4_add_motion(coordinates)
    motion = step4_result["motion"]

    # Step 5: Combine into spec
    show_loader("Building scene")
    spec = step5_combine_spec(elements, assignments, coordinates, motion)

    # Save spec
    if not output_path:
        output_path = "scenes/chunked_generated_spec.json"

    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)

    show_loader("Saving to file")
    with open(output_file, "w") as f:
        json.dump(spec, f, indent=2)

    print("\n" + "="*60)
    print("GENERATION COMPLETE")
    print("="*60)
    print(f"Scene spec saved to: {output_file}")
    print(f"Total entities: {len(spec['entities'])}")
    print(f"Scene name: {spec['scene_name']}")
    print("="*60 + "\n")

    return {
        "spec": spec,
        "output_path": str(output_file),
    }


if __name__ == "__main__":
    description = "plane flying up with people looking up, clouds and sun"
    result = generate_scene_chunked(description)
    print("\nFinal spec:")
    print(json.dumps(result["spec"], indent=2))
