"""Fast template-based scene generator (no Ollama required)."""

import json
import sys
import time
from pathlib import Path

from scene_templates import SceneTemplateLibrary


def show_loader(message: str, duration: float = 0.3):
    """Show a simple loading indicator."""
    for i in range(3):
        sys.stdout.write(f"\r{message}{'.' * (i + 1)}")
        sys.stdout.flush()
        time.sleep(duration / 3)
    sys.stdout.write(f"\r{message}... Done!\n")
    sys.stdout.flush()


def generate_scene_from_template(description: str, output_path: str | None = None) -> dict[str, any]:
    """Generate scene spec using template matching (fast, no Ollama)."""
    print("\n" + "="*60)
    print("TEMPLATE-BASED SCENE GENERATION")
    print("="*60)
    print(f"Description: '{description}'")
    print("="*60)

    # Load template library
    show_loader("Loading template library")
    template_lib = SceneTemplateLibrary()
    templates = template_lib.get_all_templates()
    print(f"  Loaded {len(templates)} templates")

    # Find matching template
    show_loader("Matching description to template")
    template = template_lib.get_best_template(description)

    if template:
        print(f"  Matched: {template.name}")
        print(f"  Tags: {', '.join(template.tags)}")
    else:
        print("  No match found, using default template")
        template = templates[0]

    # Generate spec
    show_loader("Generating scene spec")
    spec = template.to_spec()

    # Save spec
    if not output_path:
        output_path = "scenes/template_generated_spec.json"

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
    print(f"Generation time: <1 second")
    print("="*60 + "\n")

    return {
        "spec": spec,
        "output_path": str(output_file),
        "template_used": template.name,
    }


if __name__ == "__main__":
    description = "plane flying up with people looking up, clouds and sun"
    result = generate_scene_from_template(description)
    print("\nGenerated spec:")
    print(json.dumps(result["spec"], indent=2))
