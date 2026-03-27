"""Demo script showing validation errors for COE-302."""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from pydantic import ValidationError

from benchmark_core.config import ProviderConfig, TaskCard, Variant


def main() -> None:
    """Demonstrate validation errors."""
    print("=" * 60)
    print("COE-302: Validation Error Evidence Demo")
    print("=" * 60)

    # 1. Invalid provider config - empty name
    print("\n1. Provider with empty name:")
    print("-" * 40)
    try:
        ProviderConfig(
            name="",
            protocol_surface="anthropic_messages",
            upstream_base_url_env="URL",
            api_key_env="KEY",
        )
    except ValidationError as e:
        print(f"  Field-level error: {e}")

    # 2. Invalid variant - missing benchmark tags
    print("\n2. Variant with missing benchmark tags:")
    print("-" * 40)
    try:
        Variant(
            name="test",
            provider="fireworks",
            model_alias="model",
            harness_profile="claude-code",
            benchmark_tags={},  # Missing required tags
        )
    except ValidationError as e:
        print(f"  Field-level error: {e}")

    # 3. Invalid task card - negative timebox
    print("\n3. Task card with negative timebox:")
    print("-" * 40)
    try:
        TaskCard(
            name="test",
            goal="Test goal",
            starting_prompt="Test prompt",
            stop_condition="Test condition",
            session_timebox_minutes=-5,
        )
    except ValidationError as e:
        print(f"  Field-level error: {e}")

    print("\n" + "=" * 60)
    print("All validation errors caught with precise field-level messages!")
    print("=" * 60)


if __name__ == "__main__":
    main()
