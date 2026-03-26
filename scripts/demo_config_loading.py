"""Demo script showing config loading working end-to-end for COE-302."""

from pathlib import Path
import sys

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from benchmark_core.config_loader import load_all_configs


def main() -> None:
    """Load and display all configs."""
    print("=" * 60)
    print("COE-302: Config Loading Evidence Demo")
    print("=" * 60)

    # Load all configs
    configs_dir = Path(__file__).parent.parent / "configs"
    registry = load_all_configs(configs_dir)

    print("\n1. Providers Loaded:")
    print("-" * 40)
    for name, provider in registry.providers.items():
        print(f"  • {name}")
        print(f"    - protocol_surface: {provider.protocol_surface}")
        print(f"    - models: {[m.alias for m in provider.models]}")

    print("\n2. Harness Profiles Loaded:")
    print("-" * 40)
    for name, harness in registry.harness_profiles.items():
        print(f"  • {name}")
        print(f"    - protocol_surface: {harness.protocol_surface}")
        print(f"    - base_url_env: {harness.base_url_env}")

    print("\n3. Variants Loaded:")
    print("-" * 40)
    for name, variant in registry.variants.items():
        print(f"  • {name}")
        print(f"    - provider: {variant.provider}")
        print(f"    - harness_profile: {variant.harness_profile}")
        print(f"    - model_alias: {variant.model_alias}")

    print("\n4. Experiments Loaded:")
    print("-" * 40)
    for name, exp in registry.experiments.items():
        print(f"  • {name}")
        print(f"    - variants: {exp.variants}")

    print("\n5. Task Cards Loaded:")
    print("-" * 40)
    for name, task in registry.task_cards.items():
        print(f"  • {name}")
        print(f"    - goal: {task.goal[:50]}...")

    print("\n6. Protocol Surface Coverage:")
    print("-" * 40)
    anthropic_providers = [
        n
        for n, p in registry.providers.items()
        if p.protocol_surface == "anthropic_messages"
    ]
    anthropic_harnesses = [
        n
        for n, h in registry.harness_profiles.items()
        if h.protocol_surface == "anthropic_messages"
    ]
    openai_providers = [
        n for n, p in registry.providers.items() if p.protocol_surface == "openai_responses"
    ]
    openai_harnesses = [
        n
        for n, h in registry.harness_profiles.items()
        if h.protocol_surface == "openai_responses"
    ]

    print("  Anthropic surfaces:")
    print(f"    - Providers: {anthropic_providers}")
    print(f"    - Harnesses: {anthropic_harnesses}")
    print("  OpenAI surfaces:")
    print(f"    - Providers: {openai_providers}")
    print(f"    - Harnesses: {openai_harnesses}")

    print("\n" + "=" * 60)
    print("All configs loaded successfully!")
    print("=" * 60)


if __name__ == "__main__":
    main()
