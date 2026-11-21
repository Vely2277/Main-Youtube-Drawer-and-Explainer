"""Chunked Ollama workflow - Step 3: Generate coordinates."""

import json
from typing import Any

from ollama_client import OllamaClient, get_ollama_path


def step3_generate_coordinates(assignments: dict[str, str]) -> dict[str, Any]:
    """Step 3: Generate coordinates for each entity."""
    print("\n" + "="*60)
    print("[Step 3/5] Generating coordinates...")
    print("="*60)
    print(f"Assignments: {assignments}")
    print("Querying Ollama...")

    ollama_path = get_ollama_path()
    client = OllamaClient(model="qwen2.5:3b", ollama_path=ollama_path)

    assignments_str = json.dumps(assignments)

    prompt = f"""Assignments: {assignments_str}

Frame: x from -7 to 7, y from -4 to 4. Ground: y < 0, Sky: y > 0.
Assign x,y coordinates for each element.
Return JSON: {{"coordinates": {{"plane": [0, 2], "people": [-2, -2], "cloud": [3, 1], "sun": [-3, 2]}}}}"""

    try:
        print("Waiting for Ollama response (max 30s)...")
        response = client.generate(prompt, json_mode=False)
        print(f"Response received: {response}")

        data = json.loads(response)
        coordinates = data.get("coordinates", {})

        print(f"\n[OK] Generated coordinates:")
        for elem, coords in coordinates.items():
            print(f"  - {elem} -> ({coords[0]}, {coords[1]})")
        print("="*60 + "\n")

        return {"coordinates": coordinates}

    except Exception as e:
        print(f"\n[ERROR] {e}")
        print("[FALLBACK] Using default coordinates")
        fallback = {}
        for elem, role in assignments.items():
            if role == "sky_entity":
                fallback[elem] = [0, 2]
            else:
                fallback[elem] = [-2, -2]
        for elem, coords in fallback.items():
            print(f"  - {elem} -> ({coords[0]}, {coords[1]})")
        print("="*60 + "\n")
        return {"coordinates": fallback}


if __name__ == "__main__":
    assignments = {"plane": "sky_entity", "people": "character", "cloud": "sky_entity", "sun": "sky_entity"}
    result = step3_generate_coordinates(assignments)
    print(json.dumps(result, indent=2))
