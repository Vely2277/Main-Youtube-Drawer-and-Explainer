"""Chunked Ollama workflow - Step 2: Assign roles to elements."""

import json
from typing import Any

from ollama_client import OllamaClient, get_ollama_path


def step2_assign_roles(elements: list[str]) -> dict[str, Any]:
    """Step 2: Assign roles to each element."""
    print("\n" + "="*60)
    print("[Step 2/5] Assigning roles to elements...")
    print("="*60)
    print(f"Elements: {', '.join(elements)}")
    print("Querying Ollama...")

    ollama_path = get_ollama_path()
    client = OllamaClient(model="qwen2.5:3b", ollama_path=ollama_path)

    elements_str = ", ".join(elements)

    prompt = f"""Elements: {elements_str}

Assign each element a role: character, prop, structure, sky_entity, background, foreground.
Return JSON: {{"assignments": {{"plane": "sky_entity", "people": "character", "cloud": "sky_entity", "sun": "sky_entity"}}}}"""

    try:
        print("Waiting for Ollama response (max 30s)...")
        response = client.generate(prompt, json_mode=False)
        print(f"Response received: {response}")

        data = json.loads(response)
        assignments = data.get("assignments", {})

        print(f"\n[OK] Assigned roles:")
        for elem, role in assignments.items():
            print(f"  - {elem} -> {role}")
        print("="*60 + "\n")

        return {"assignments": assignments}

    except Exception as e:
        print(f"\n[ERROR] {e}")
        print("[FALLBACK] Using default role assignments")
        fallback = {}
        for elem in elements:
            if elem in ["plane", "cloud", "sun"]:
                fallback[elem] = "sky_entity"
            elif elem in ["people", "person", "character"]:
                fallback[elem] = "character"
            else:
                fallback[elem] = "prop"
        for elem, role in fallback.items():
            print(f"  - {elem} -> {role}")
        print("="*60 + "\n")
        return {"assignments": fallback}


if __name__ == "__main__":
    elements = ["plane", "people", "cloud", "sun"]
    result = step2_assign_roles(elements)
    print(json.dumps(result, indent=2))
