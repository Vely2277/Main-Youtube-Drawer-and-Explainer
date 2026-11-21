"""Test Ollama with a simple query."""

from ollama_client import OllamaClient, get_ollama_path


def test_ollama():
    """Test Ollama with a simple 'hi' query."""
    ollama_path = get_ollama_path()
    client = OllamaClient(model="qwen2.5:3b", ollama_path=ollama_path)

    print("Testing Ollama with 'hi'...")
    try:
        response = client.generate("hi", json_mode=False)
        print("Response:")
        print(response)
        print("\n[OK] Ollama is working")
    except Exception as e:
        print(f"[FAIL] Error: {e}")


if __name__ == "__main__":
    test_ollama()
