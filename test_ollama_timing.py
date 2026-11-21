"""Test Ollama with detailed progress and timing."""

import sys
import time
from ollama_client import OllamaClient, get_ollama_path


def test_ollama_with_timing():
    """Test Ollama with timing and progress."""
    print("\n" + "="*60)
    print("OLLAMA CONNECTION TEST")
    print("="*60)

    # Find Ollama
    print("\n[1/4] Finding Ollama executable...")
    ollama_path = get_ollama_path()
    if ollama_path:
        print(f"  Found: {ollama_path}")
    else:
        print("  [ERROR] Ollama not found!")
        return False

    # Initialize client with 16 threads for faster inference
    print("\n[2/4] Initializing Ollama client...")
    print("  Model: qwen2.5:0.5b")
    print("  Threads: 16 (for faster CPU inference)")
    client = OllamaClient(model="qwen2.5:0.5b", ollama_path=ollama_path, num_threads=16)
    print("  [OK] Client initialized")

    # Test with simple query
    print("\n[3/4] Sending test query: 'hi'")
    print("  Waiting for response (max 120s)...")

    start_time = time.time()

    # Show loading animation
    for i in range(120):
        sys.stdout.write(f"\r  Loading: [{'=' * (i % 20)}{' ' * (20 - (i % 20))}] {i}s")
        sys.stdout.flush()
        time.sleep(0.1)

    try:
        response = client.generate("hi", json_mode=False)
        elapsed = time.time() - start_time

        sys.stdout.write(f"\r  Loading: [{'=' * 10}] {elapsed:.1f}s\n")
        sys.stdout.flush()

        print(f"\n[4/4] Response received:")
        print(f"  Time: {elapsed:.2f} seconds")
        print(f"  Response: {response}")
        print("\n[OK] Ollama is working!")
        print("="*60 + "\n")
        return True

    except Exception as e:
        elapsed = time.time() - start_time
        sys.stdout.write(f"\r  Loading: [{'X' * 10}] {elapsed:.1f}s\n")
        sys.stdout.flush()
        print(f"\n[ERROR] Failed after {elapsed:.2f} seconds")
        print(f"  Error: {e}")
        print("="*60 + "\n")
        return False


if __name__ == "__main__":
    success = test_ollama_with_timing()
    sys.exit(0 if success else 1)
