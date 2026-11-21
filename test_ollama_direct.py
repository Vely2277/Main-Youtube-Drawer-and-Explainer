"""Test Ollama with no timeout and real-time output."""

import subprocess
import sys


def test_ollama_direct():
    """Test Ollama directly with no timeout."""
    print("\n" + "="*60)
    print("OLLAMA DIRECT TEST (No Timeout)")
    print("="*60)

    ollama_path = r"C:\Users\USER\AppData\Local\Programs\Ollama\ollama.exe"

    print(f"\n[1/3] Using: {ollama_path}")
    print("[2/3] Running: ollama run qwen2.5:3b")
    print("[3/3] Input: 'hi'")
    print("\nStarting Ollama (no timeout, real-time output)...")
    print("-"*60)

    try:
        # Run without timeout, show output in real-time
        process = subprocess.Popen(
            [ollama_path, "run", "qwen2.5:3b"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="ignore",
        )

        # Send input
        process.stdin.write("hi\n")
        process.stdin.flush()

        # Read output line by line
        output_lines = []
        for line in process.stdout:
            print(line, end="")
            output_lines.append(line)
            if len(output_lines) > 50:  # Limit output
                break

        process.stdin.close()
        process.terminate()

        print("-"*60)
        print("\n[OK] Ollama responded")
        print(f"Total lines: {len(output_lines)}")
        print("="*60 + "\n")

    except Exception as e:
        print(f"\n[ERROR] {e}")
        print("="*60 + "\n")


if __name__ == "__main__":
    test_ollama_direct()
