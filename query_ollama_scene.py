"""Query Ollama to generate a scene spec."""

import json

from ollama_client import OllamaClient, get_ollama_path


def query_ollama_for_scene_spec():
    """Query Ollama to generate a scene spec for the plane scenario."""
    ollama_path = get_ollama_path()
    client = OllamaClient(model="qwen2.5:3b", ollama_path=ollama_path)

    prompt = """You are a scene specification generator for an SVG animation system.

Generate a scene spec JSON for this scenario:
"A plane flying up with a lot of people down looking up to it... and the cloud and sun showing"

The scene spec format is JSON with these fields:
{
  "scene_name": "name of the scene",
  "entities": [
    {
      "asset": "path/to/svg/file.svg",
      "role": "character|prop|structure|sky_entity|background|foreground",
      "zone": "sky|ground|background|foreground",
      "anchor": "bottom|center|top",
      "scale_fraction": 0.0-1.0,
      "parent_asset": "path/to/parent.svg (optional)",
      "relative_offset_x": 0.0,
      "relative_offset_y": 0.0,
      "relative_anchor": "center",
      "composition_context": "description for LLM composition (optional)",
      "motion_group": "group_name (optional)",
      "motion_type": "static|translate_x|translate_y|scale|fade",
      "motion_target_x": 0.0,
      "motion_target_y": 0.0,
      "motion_run_time": 1.8,
      "animation": "create|draw_border",
      "run_time": 1.0,
      "wait_after": 0.1,
      "z_index": 0
    }
  ]
}

Available assets:
- tabler/outline/plane-inflight.svg (plane)
- tabler/outline/cloud.svg (cloud)
- tabler/outline/sun.svg (sun)
- open_peeps/templates_standing/* (standing people)
- tabler/outline/building-skyscraper.svg (buildings)

Rules:
- Plane should be in sky zone, flying upward (translate_y)
- People should be in ground zone, looking up
- Clouds and sun in sky zone
- Use scale_fraction between 0.05 and 0.4
- Use motion_group for synchronized movement
- Add composition_context for people if they need clipping

Return ONLY the JSON, nothing else."""

    print("Querying Ollama...")
    try:
        response = client.generate(prompt, json_mode=False)
        print("Ollama response:")
        print(response)
        print("\n" + "="*50 + "\n")

        # Try to parse JSON
        try:
            # Find JSON in response (in case there's extra text)
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
                print("Parsed scene spec:")
                print(json.dumps(scene_spec, indent=2))
                return scene_spec
            else:
                # Try parsing the whole response
                scene_spec = json.loads(response)
                print("Parsed scene spec:")
                print(json.dumps(scene_spec, indent=2))
                return scene_spec
        except json.JSONDecodeError as e:
            print(f"Failed to parse JSON: {e}")
            return None
    except Exception as e:
        print(f"Error querying Ollama: {e}")
        return None


if __name__ == "__main__":
    scene_spec = query_ollama_for_scene_spec()
    if scene_spec:
        # Save to file
        output_path = "scenes/plane_people_looking_up_spec.json"
        with open(output_path, "w") as f:
            json.dump(scene_spec, f, indent=2)
        print(f"\nSaved to: {output_path}")
