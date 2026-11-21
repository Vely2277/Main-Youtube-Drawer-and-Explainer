"""Test Ollama with a very simple JSON request."""

import json

from ollama_client import OllamaClient, get_ollama_path


def test_simple_json():
    """Test Ollama with simple JSON generation."""
    ollama_path = get_ollama_path()
    client = OllamaClient(model="qwen2.5:3b", ollama_path=ollama_path)

    prompt = """Return JSON: {"test": "value"}"""

    print("Testing simple JSON...")
    try:
        response = client.generate(prompt, json_mode=False)
        print("Response:")
        print(response)
    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    test_simple_json()
