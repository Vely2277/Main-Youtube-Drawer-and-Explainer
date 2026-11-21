"""Simple Ollama test with detailed progress."""

import subprocess
import sys
import time


def test_ollama_simple():
    """Test Ollama with detailed progress output."""
    print("\n" + "="*60)
    print("OLLAMA DETAILED TEST")
    print("="*60)

    ollama_path = r"C:\Users\USER\AppData\Local\Programs\Ollama\ollama.exe"

    # Step 1: Check if Ollama exists
    print("\n[Step 1/5] Checking Ollama executable...")
    print(f"  Path: {ollama_path}")
    time.sleep(0.5)

    try:
        result = subprocess.run(
            [ollama_path, "--version"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        print(f"  [OK] Ollama found: {result.stdout.strip()}")
    except Exception as e:
        print(f"  [ERROR] {e}")
        return

    # Step 2: Check if model exists
    print("\n[Step 2/5] Checking qwen2.5:3b model...")
    time.sleep(0.5)

    try:
        result = subprocess.run(
            [ollama_path, "list"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if "qwen2.5:3b" in result.stdout:
            print("  [OK] Model qwen2.5:3b found")
        else:
            print("  [WARNING] Model not found in list")
    except Exception as e:
        print(f"  [ERROR] {e}")
        return

    # Step 3: Start Ollama process
    print("\n[Step 3/5] Starting Ollama process...")
    print("  Command: ollama run qwen2.5:3b")
    print("  This may take a moment to load the model...")
    time.sleep(1)

    try:
        process = subprocess.Popen(
            [ollama_path, "run", "qwen2.5:3b"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="ignore",
        )
        print("  [OK] Ollama process started")
    except Exception as e:
        print(f"  [ERROR] {e}")
        return

    # Step 4: Send input
    print("\n[Step 4/5] Sending input: 'hi'")
    time.sleep(0.5)

    try:
        process.stdin.write("hi\n")
        process.stdin.flush()
        print("  [OK] Input sent")
    except Exception as e:
        print(f"  [ERROR] {e}")
        process.terminate()
        return

    # Step 5: Read response
    print("\n[Step 5/5] Reading response...")
    print("  Waiting for Ollama to respond...")
    print("-"*60)

    try:
        output = []
        start = time.time()

        for line in process.stdout:
            elapsed = time.time() - start
            print(f"[{elapsed:.1f}s] {line}", end="")
            output.append(line)

            # Stop after reasonable output
            if len(output) > 20 or elapsed > 60:
                break

        print("-"*60)
        print(f"\n[OK] Response received")
        print(f"  Time: {elapsed:.1f} seconds")
        print(f"  Lines: {len(output)}")

    except Exception as e:
        print(f"\n[ERROR] {e}")
    finally:
        process.stdin.close()
        process.terminate()

    print("\n" + "="*60)
    print("TEST COMPLETE")
    print("="*60 + "\n")


if __name__ == "__main__":
    test_ollama_simple()
