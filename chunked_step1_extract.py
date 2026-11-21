"""Chunked Ollama workflow - Step 1: Extract scene elements."""

import json
from typing import Any

from ollama_client import OllamaClient, get_ollama_path


def step1_extract_elements(description: str) -> dict[str, Any]:
    """Step 1: Extract scene elements from description."""
    print("\n" + "="*60)
    print("[Step 1/5] Extracting scene elements...")
    print("="*60)
    print(f"Description: '{description}'")
    print("Querying Ollama...")

    ollama_path = get_ollama_path()
    client = OllamaClient(model="qwen2.5:3b", ollama_path=ollama_path)

    prompt = f"""Description: "{description}"

List the main elements (objects, characters, background) needed.
Return JSON: {{"elements": ["plane", "people", "cloud", "sun"]}}"""

    try:
        print("Waiting for Ollama response (max 30s)...")
        response = client.generate(prompt, json_mode=False)
        print(f"Response received: {response}")

        # Parse JSON
        data = json.loads(response)
        elements = data.get("elements", [])

        print(f"\n[OK] Extracted {len(elements)} elements:")
        for elem in elements:
            print(f"  - {elem}")
        print("="*60 + "\n")

        return {"elements": elements}

    except Exception as e:
        print(f"\n[ERROR] {e}")
        print("[FALLBACK] Using default elements")
        fallback = ["plane", "people", "cloud", "sun"]
        print(f"  - {', '.join(fallback)}")
        print("="*60 + "\n")
        return {"elements": fallback}


if __name__ == "__main__":
    description = "plane flying up with people looking up, clouds and sun"
    result = step1_extract_elements(description)
    print(json.dumps(result, indent=2))
