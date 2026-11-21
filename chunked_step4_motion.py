"""Chunked Ollama workflow - Step 4: Add motion parameters."""

import json
from typing import Any

from ollama_client import OllamaClient, get_ollama_path


def step4_add_motion(coordinates: dict[str, list]) -> dict[str, Any]:
    """Step 4: Add motion parameters for each entity."""
    print("\n" + "="*60)
    print("[Step 4/5] Adding motion parameters...")
    print("="*60)
    print(f"Coordinates: {coordinates}")
    print("Querying Ollama...")

    ollama_path = get_ollama_path()
    client = OllamaClient(model="qwen2.5:3b", ollama_path=ollama_path)

    coordinates_str = json.dumps(coordinates)

    prompt = f"""Coordinates: {coordinates_str}

For each element, assign motion: static, translate_x, translate_y, scale, fade.
Return JSON: {{"motion": {{"plane": "translate_y", "people": "static", "cloud": "static", "sun": "static"}}}}"""

    try:
        print("Waiting for Ollama response (max 30s)...")
        response = client.generate(prompt, json_mode=False)
        print(f"Response received: {response}")

        data = json.loads(response)
        motion = data.get("motion", {})

        print(f"\n[OK] Assigned motion:")
        for elem, motion_type in motion.items():
            print(f"  - {elem} -> {motion_type}")
        print("="*60 + "\n")

        return {"motion": motion}

    except Exception as e:
        print(f"\n[ERROR] {e}")
        print("[FALLBACK] Using default motion assignments")
        fallback = {}
        for elem in coordinates.keys():
            if elem == "plane":
                fallback[elem] = "translate_y"
            else:
                fallback[elem] = "static"
        for elem, motion_type in fallback.items():
            print(f"  - {elem} -> {motion_type}")
        print("="*60 + "\n")
        return {"motion": fallback}


if __name__ == "__main__":
    coordinates = {"plane": [0, 2], "people": [-2, -2], "cloud": [3, 1], "sun": [-3, 2]}
    result = step4_add_motion(coordinates)
    print(json.dumps(result, indent=2))
