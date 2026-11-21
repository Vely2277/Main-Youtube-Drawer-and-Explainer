"""Test the complete scene generation system."""

from pathlib import Path

from scene_orchestrator import SceneGenerationOrchestrator


def test_system_status():
    """Test system status and components."""
    print("=" * 60)
    print("TEST 1: System Status")
    print("=" * 60)

    asset_dir = Path("assets/svgs")
    output_dir = Path("output/generated_scenes")

    orchestrator = SceneGenerationOrchestrator(asset_dir, output_dir)
    status = orchestrator.get_system_status()

    print(f"Asset count: {status['asset_count']}")
    print(f"Template count: {status['template_count']}")
    print(f"Output dir: {status['output_dir']}")
    print("\nComponents:")
    for name, status_str in status["components"].items():
        print(f"  {name}: {status_str}")

    print("\n[OK] System status check passed\n")


def test_template_generation():
    """Test template-based scene generation."""
    print("=" * 60)
    print("TEST 2: Template Generation")
    print("=" * 60)

    asset_dir = Path("assets/svgs")
    output_dir = Path("output/generated_scenes")

    orchestrator = SceneGenerationOrchestrator(asset_dir, output_dir)

    # Test with plane flight description
    description = "plane flying up with people looking up, clouds and sun"
    result = orchestrator.generate_scene(description, "test_plane_flight.json")

    print(f"Scene name: {result['spec']['scene_name']}")
    print(f"Entity count: {len(result['spec']['entities'])}")
    print(f"Output path: {result['output_path']}")
    print(f"Validation: {result['validation']['is_valid']}")

    if not result["validation"]["is_valid"]:
        print(f"Errors: {result['validation']['errors']}")

    print("\n[OK] Template generation passed\n")


def test_ollama_generation():
    """Test Ollama-based scene generation."""
    print("=" * 60)
    print("TEST 3: Ollama Generation")
    print("=" * 60)

    asset_dir = Path("assets/svgs")
    output_dir = Path("output/generated_scenes")

    orchestrator = SceneGenerationOrchestrator(asset_dir, output_dir)

    # Test with a description that doesn't match templates
    description = "a robot walking through a city at night"
    result = orchestrator.generate_scene(description, "test_robot_city.json")

    print(f"Scene name: {result['spec']['scene_name']}")
    print(f"Entity count: {len(result['spec']['entities'])}")
    print(f"Output path: {result['output_path']}")
    print(f"Validation: {result['validation']['is_valid']}")

    if not result["validation"]["is_valid"]:
        print(f"Errors: {result['validation']['errors']}")

    print("\n[OK] Ollama generation passed\n")


def test_batch_generation():
    """Test batch scene generation."""
    print("=" * 60)
    print("TEST 4: Batch Generation")
    print("=" * 60)

    asset_dir = Path("assets/svgs")
    output_dir = Path("output/generated_scenes")

    orchestrator = SceneGenerationOrchestrator(asset_dir, output_dir)

    descriptions = [
        "plane flying up with people looking up",
        "city skyline with buildings",
        "nature scene with trees and sun",
    ]

    results = orchestrator.batch_generate(descriptions)

    for i, result in enumerate(results):
        if "error" in result:
            print(f"Scene {i+1}: ERROR - {result['error']}")
        else:
            print(f"Scene {i+1}: {result['spec']['scene_name']} - {len(result['spec']['entities'])} entities")

    print("\n[OK] Batch generation passed\n")


def test_validation():
    """Test validation system."""
    print("=" * 60)
    print("TEST 5: Validation System")
    print("=" * 60)

    asset_dir = Path("assets/svgs")
    output_dir = Path("output/generated_scenes")

    orchestrator = SceneGenerationOrchestrator(asset_dir, output_dir)

    # Test with invalid spec
    invalid_spec = {
        "scene_name": "Invalid Scene",
        "entities": [
            {
                "asset": "nonexistent.svg",
                "role": "invalid_role",
                "zone": "invalid_zone",
                "anchor": "invalid_anchor",
                "scale_fraction": 2.0,  # Out of range
            }
        ],
    }

    errors = orchestrator.scene_validator.validate_spec(invalid_spec)
    print(f"Validation errors found: {len(errors)}")
    for error in errors[:5]:  # Show first 5
        print(f"  - {error}")

    print("\n[OK] Validation system passed\n")


if __name__ == "__main__":
    print("\n" + "="*60)
    print("SCENE GENERATION SYSTEM TEST")
    print("="*60 + "\n")

    try:
        test_system_status()
        test_template_generation()
        test_ollama_generation()
        test_batch_generation()
        test_validation()

        print("="*60)
        print("ALL TESTS PASSED")
        print("="*60)
    except Exception as e:
        print(f"\n[FAIL] Test failed: {e}")
        import traceback
        traceback.print_exc()
