"""Two-step Ollama workflow: plan then generate scene spec."""

import json

from ollama_client import OllamaClient, get_ollama_path


def plan_scene():
    """Step 1: Ask Ollama to plan the scene in detail."""
    ollama_path = get_ollama_path()
    client = OllamaClient(model="qwen2.5:3b", ollama_path=ollama_path)

    prompt = """You are a scene planner for an SVG animation system.

SCENARIO: "A plane flying up with a lot of people down looking up to it... and the cloud and sun showing"

FRAME SPECS:
- Aspect ratio: 16:9
- Frame width: ~14.22 units
- Frame height: 8 units
- Ground baseline: y = -2.35
- Safe margins: 8% horizontal, 10% vertical
- Sky zone: y > 0
- Ground zone: y < 0

ZONES:
- SKY: y > 0 (sky entities, plane)
- GROUND: y < 0 (characters, structures)
- BACKGROUND: z_index 0-2
- FOREGROUND: z_index 5+

SCALE FRACTIONS (relative to frame height):
- Characters: 0.25-0.32
- Props: 0.08-0.15
- Structures: 0.3-0.5
- Sky entities: 0.1-0.25

AVAILABLE ASSETS:
- tabler/outline/plane-inflight.svg (plane)
- tabler/outline/cloud.svg (cloud)
- tabler/outline/sun.svg (sun)
- open_peeps/templates_standing/*.svg (standing people)
- tabler/outline/building-skyscraper.svg (buildings)

PLAN THE SCENE:
1. Describe the composition layout
2. Specify exact positions (x, y coordinates)
3. Specify scale fractions for each entity
4. Specify z-index ordering
5. Specify motion types and targets
6. Specify how many people and their arrangement
7. Specify cloud and sun positions
8. Explain the visual hierarchy

Return a detailed textual plan. Be specific about coordinates and scales."""

    print("Step 1: Planning scene...")
    try:
        plan = client.generate(prompt, json_mode=False)
        print("PLAN:")
        print(plan)
        print("\n" + "="*70 + "\n")
        return plan
    except Exception as e:
        print(f"Error: {e}")
        return None


def generate_spec_from_plan(plan: str):
    """Step 2: Ask Ollama to generate JSON from the plan."""
    ollama_path = get_ollama_path()
    client = OllamaClient(model="qwen2.5:3b", ollama_path=ollama_path)

    prompt = f"""You are a scene spec generator for an SVG animation system.

Based on this plan, generate a scene spec JSON:

PLAN:
{plan}

SCENE SPEC JSON FORMAT:
{{
  "scene_name": "name",
  "entities": [
    {{
      "asset": "path/to/svg",
      "role": "character|prop|structure|sky_entity|background|foreground",
      "zone": "sky|ground|background|foreground",
      "anchor": "bottom|center|top",
      "scale_fraction": 0.0-1.0,
      "parent_asset": "path (optional)",
      "relative_offset_x": 0.0,
      "relative_offset_y": 0.0,
      "relative_anchor": "center",
      "composition_context": "description (optional)",
      "motion_group": "group_name (optional)",
      "motion_type": "static|translate_x|translate_y|scale|fade",
      "motion_target_x": 0.0,
      "motion_target_y": 0.0,
      "motion_run_time": 1.8,
      "animation": "create|draw_border",
      "run_time": 1.0,
      "wait_after": 0.1,
      "z_index": 0
    }}
  ]
}}

AVAILABLE ASSETS:
- tabler/outline/plane-inflight.svg
- tabler/outline/cloud.svg
- tabler/outline/sun.svg
- open_peeps/templates_standing/peep-standing-standing-blazer-1-buns-smile-teeth-gap-none.svg
- open_peeps/templates_standing/peep-standing-standing-crossed-arms-1-bun-smile-big-none.svg
- open_peeps/templates_standing/peep-standing-standing-pointing-finger-1-bun-2-calm-none.svg

Return ONLY the JSON, nothing else."""

    print("Step 2: Generating JSON from plan...")
    try:
        response = client.generate(prompt, json_mode=False)
        print("RAW RESPONSE:")
        print(response)
        print("\n" + "="*70 + "\n")

        # Parse JSON
        lines = response.strip().split("\n")
        json_start = -1
        json_end = -1
        brace_count = 0

        for i, line in enumerate(lines):
            if "{" in line and json_start == -1:
                json_start = i
            if json_start != -1:
                brace_count += line.count("{") - line.count("}")
                if brace_count == 0:
                    json_end = i + 1
                    break

        if json_start != -1 and json_end != -1:
            json_text = "\n".join(lines[json_start:json_end])
            scene_spec = json.loads(json_text)
            print("PARSED SCENE SPEC:")
            print(json.dumps(scene_spec, indent=2))
            return scene_spec
        else:
            scene_spec = json.loads(response)
            print("PARSED SCENE SPEC:")
            print(json.dumps(scene_spec, indent=2))
            return scene_spec
    except Exception as e:
        print(f"Error: {e}")
        return None


if __name__ == "__main__":
    plan = plan_scene()
    if plan:
        scene_spec = generate_spec_from_plan(plan)
        if scene_spec:
            output_path = "scenes/plane_people_looking_up_spec_v2.json"
            with open(output_path, "w") as f:
                json.dump(scene_spec, f, indent=2)
            print(f"\nSaved to: {output_path}")
