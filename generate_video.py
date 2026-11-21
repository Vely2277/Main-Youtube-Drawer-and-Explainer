"""Unified endpoint to generate scene from prompt and render video."""

import sys
from pathlib import Path

from scene_generator import SceneGenerator


def main():
    if len(sys.argv) < 2:
        print("Usage: python generate_video.py \"your prompt here\"")
        print("Example: python generate_video.py \"plane flying with people looking up\"")
        sys.exit(1)

    prompt = " ".join(sys.argv[1:])
    
    print("="*60)
    print("FULL PIPELINE: Scene Generation + Video Rendering")
    print("="*60)
    print(f"Prompt: '{prompt}'")
    print("="*60)

    # Step 1: Generate scene
    print("\n[Step 1/2] Generating scene from prompt...")
    generator = SceneGenerator()
    result = generator.generate(prompt)
    scene_json_path = result["output_path"]
    print(f"Scene saved to: {scene_json_path}")

    # Step 2: Render video
    print("\n[Step 2/2] Rendering video from scene...")
    import subprocess
    
    render_cmd = [
        ".venv\\Scripts\\python.exe",
        "render_video.py",
        "--scene-spec", scene_json_path,
        "--asset-dir", "assets\\svgs"
    ]
    
    try:
        result = subprocess.run(render_cmd, cwd=Path(__file__).parent, capture_output=True, text=True)
        print(result.stdout)
        if result.stderr:
            print(result.stderr)
        
        if result.returncode == 0:
            print("\n" + "="*60)
            print("PIPELINE COMPLETE")
            print("="*60)
        else:
            print(f"\n[ERROR] Render failed with exit code {result.returncode}")
            sys.exit(1)
    except Exception as e:
        print(f"[ERROR] Failed to run render: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
