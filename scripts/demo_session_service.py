#!/usr/bin/env python3
"""Demonstration script for session service capabilities.

This script provides runtime evidence for:
1. Services can create and finalize sessions safely
2. Repository methods preserve referential integrity
3. Duplicate session identifiers are rejected
"""

import asyncio
import sys
from datetime import UTC, datetime
from uuid import uuid4

# Add src to path
sys.path.insert(0, "src")

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from benchmark_core.db.models import Base
from benchmark_core.repositories.session_repository import SQLSessionRepository
from benchmark_core.services.benchmark_metadata_service import BenchmarkMetadataService
from benchmark_core.services.session_service import SessionService, SessionValidationError


def setup_database():
    """Set up an in-memory SQLite database with schema."""
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)


async def demo_create_and_finalize_session():
    """Demo: Services can create and finalize sessions safely."""
    print("=" * 60)
    print("DEMO 1: Create and Finalize Sessions Safely")
    print("=" * 60)

    session_local = setup_database()

    with session_local() as db_session:
        metadata_service = BenchmarkMetadataService(db_session)
        session_service = SessionService(SQLSessionRepository(db_session))

        # Step 1: Create prerequisite entities
        print("\n1. Creating prerequisite entities...")
        provider = await metadata_service.create_provider_with_models(
            name="openai",
            protocol_surface="openai_responses",
            upstream_base_url_env="OPENAI_BASE_URL",
            api_key_env="OPENAI_API_KEY",
            models=[{"alias": "gpt-4", "upstream_model": "gpt-4"}],
        )
        print(f"   ✓ Created provider: {provider.name} (ID: {provider.id})")

        harness = await metadata_service.create_harness_profile(
            name="aider",
            protocol_surface="openai_responses",
            base_url_env="OPENAI_API_BASE",
            api_key_env="OPENAI_API_KEY",
            model_env="OPENAI_MODEL",
        )
        print(f"   ✓ Created harness profile: {harness.name} (ID: {harness.id})")

        variant = await metadata_service.create_variant(
            name="gpt4-aider",
            provider="openai",
            model_alias="gpt-4",
            harness_profile="aider",
        )
        print(f"   ✓ Created variant: {variant.name} (ID: {variant.id})")

        task_card = await metadata_service.create_task_card(
            name="test-task",
            goal="Test the session service",
            starting_prompt="Create a simple Python function",
            stop_condition="Function is created and tested",
        )
        print(f"   ✓ Created task card: {task_card.name} (ID: {task_card.id})")

        experiment = await metadata_service.create_experiment(
            name="session-demo",
            description="Demo experiment for session service",
            variant_ids=[variant.id],
        )
        print(f"   ✓ Created experiment: {experiment.name} (ID: {experiment.id})")

        # Step 2: Create a session
        print("\n2. Creating a new session...")
        session = await session_service.create_session(
            experiment_id=experiment.id,
            variant_id=variant.id,
            task_card_id=task_card.id,
            harness_profile="aider",
            repo_path="/tmp/demo-repo",
            git_branch="main",
            git_commit="abc1234",
            git_dirty=False,
            operator_label="demo-session-001",
        )
        print(f"   ✓ Created session: {session.session_id}")
        print(f"   ✓ Status: {session.status}")
        print(f"   ✓ Started at: {session.started_at}")
        print(f"   ✓ Operator label: {session.operator_label}")

        # Step 3: Get session summary
        print("\n3. Retrieving session summary...")
        summary = await session_service.get_session_summary(session.session_id)
        print("   ✓ Session summary retrieved:")
        print(f"     - ID: {summary['id']}")
        print(f"     - Status: {summary['status']}")
        print(f"     - Experiment: {summary['experiment_id']}")
        print(f"     - Variant: {summary['variant_id']}")
        print(f"     - Task Card: {summary['task_card_id']}")
        print(f"     - Git branch: {summary['git_branch']}")
        print(f"     - Git commit: {summary['git_commit']}")

        # Step 4: Finalize the session
        print("\n4. Finalizing the session...")
        finalized = await session_service.finalize_session(session.session_id, status="completed")
        print("   ✓ Session finalized")
        print(f"   ✓ Ended at: {finalized.ended_at}")
        # Handle timezone-aware/naive datetime comparison for SQLite compatibility
        started = finalized.started_at
        ended = finalized.ended_at
        if started.tzinfo is not None and ended.tzinfo is None:
            ended = ended.replace(tzinfo=started.tzinfo)
        elif started.tzinfo is None and ended.tzinfo is not None:
            started = started.replace(tzinfo=ended.tzinfo)
        print(f"   ✓ Duration: {(ended - started).total_seconds():.2f} seconds")

    print("\n✅ DEMO 1 PASSED: Sessions can be created and finalized safely")
    return True


async def demo_referential_integrity():
    """Demo: Repository methods preserve referential integrity."""
    print("\n" + "=" * 60)
    print("DEMO 2: Referential Integrity Preservation")
    print("=" * 60)

    session_local = setup_database()

    with session_local() as db_session:
        metadata_service = BenchmarkMetadataService(db_session)
        session_service = SessionService(SQLSessionRepository(db_session))

        # Create valid entities
        await metadata_service.create_provider_with_models(
            name="anthropic",
            protocol_surface="anthropic_messages",
            upstream_base_url_env="ANTHROPIC_BASE_URL",
            api_key_env="ANTHROPIC_API_KEY",
            models=[{"alias": "claude", "upstream_model": "claude-3"}],
        )
        await metadata_service.create_harness_profile(
            name="default",
            protocol_surface="anthropic_messages",
            base_url_env="OPENAI_API_BASE",
            api_key_env="OPENAI_API_KEY",
            model_env="OPENAI_MODEL",
        )
        variant = await metadata_service.create_variant(
            name="claude-default",
            provider="anthropic",
            model_alias="claude",
            harness_profile="default",
        )
        task_card = await metadata_service.create_task_card(
            name="integrity-test",
            goal="Test referential integrity",
            starting_prompt="Test",
            stop_condition="Done",
        )

        fake_uuid = uuid4()
        print(f"\n1. Attempting to create session with non-existent experiment ({fake_uuid})...")
        try:
            await session_service.create_session(
                experiment_id=fake_uuid,
                variant_id=variant.id,
                task_card_id=task_card.id,
                harness_profile="default",
                repo_path="/tmp/test",
                git_branch="main",
                git_commit="abc1234",
            )
            print("   ✗ FAILED: Should have raised an error")
            return False
        except SessionValidationError as e:
            print(f"   ✓ Correctly rejected: {e}")

        fake_variant_uuid = uuid4()
        print(
            f"\n2. Attempting to create session with non-existent variant ({fake_variant_uuid})..."
        )
        experiment = await metadata_service.create_experiment(
            name="integrity-exp",
            variant_ids=[variant.id],
        )
        try:
            await session_service.create_session(
                experiment_id=experiment.id,
                variant_id=fake_variant_uuid,
                task_card_id=task_card.id,
                harness_profile="default",
                repo_path="/tmp/test",
                git_branch="main",
                git_commit="abc1234",
            )
            print("   ✗ FAILED: Should have raised an error")
            return False
        except SessionValidationError as e:
            print(f"   ✓ Correctly rejected: {e}")

        fake_task_uuid = uuid4()
        print(
            f"\n3. Attempting to create session with non-existent task card ({fake_task_uuid})..."
        )
        try:
            await session_service.create_session(
                experiment_id=experiment.id,
                variant_id=variant.id,
                task_card_id=fake_task_uuid,
                harness_profile="default",
                repo_path="/tmp/test",
                git_branch="main",
                git_commit="abc1234",
            )
            print("   ✗ FAILED: Should have raised an error")
            return False
        except SessionValidationError as e:
            print(f"   ✓ Correctly rejected: {e}")

    print("\n✅ DEMO 2 PASSED: Referential integrity is preserved")
    return True


async def demo_duplicate_rejection():
    """Demo: Duplicate session identifiers are rejected."""
    print("\n" + "=" * 60)
    print("DEMO 3: Duplicate Session Identifier Rejection")
    print("=" * 60)

    session_local = setup_database()

    with session_local() as db_session:
        metadata_service = BenchmarkMetadataService(db_session)
        session_service = SessionService(SQLSessionRepository(db_session))

        # Create prerequisite entities
        await metadata_service.create_provider_with_models(
            name="ollama",
            protocol_surface="openai_responses",
            upstream_base_url_env="OLLAMA_BASE_URL",
            api_key_env="OLLAMA_API_KEY",
            models=[{"alias": "llama3", "upstream_model": "llama3"}],
        )
        await metadata_service.create_harness_profile(
            name="local",
            protocol_surface="openai_responses",
            base_url_env="OPENAI_API_BASE",
            api_key_env="OPENAI_API_KEY",
            model_env="OPENAI_MODEL",
        )
        variant = await metadata_service.create_variant(
            name="llama3-local",
            provider="ollama",
            model_alias="llama3",
            harness_profile="local",
        )
        task_card = await metadata_service.create_task_card(
            name="duplicate-test",
            goal="Test duplicate rejection",
            starting_prompt="Test",
            stop_condition="Done",
        )
        experiment = await metadata_service.create_experiment(
            name="duplicate-exp",
            variant_ids=[variant.id],
        )

        operator_label = "unique-session-identifier-123"

        print(f"\n1. Creating first session with operator_label='{operator_label}'...")
        session1 = await session_service.create_session(
            experiment_id=experiment.id,
            variant_id=variant.id,
            task_card_id=task_card.id,
            harness_profile="local",
            repo_path="/tmp/test1",
            git_branch="main",
            git_commit="abc1234",
            operator_label=operator_label,
        )
        print(f"   ✓ First session created: {session1.session_id}")

        print(
            f"\n2. Attempting to create second session with same operator_label='{operator_label}'..."
        )
        try:
            await session_service.create_session(
                experiment_id=experiment.id,
                variant_id=variant.id,
                task_card_id=task_card.id,
                harness_profile="local",
                repo_path="/tmp/test2",
                git_branch="feature",
                git_commit="def5678",
                operator_label=operator_label,
            )
            print("   ✗ FAILED: Should have raised an error")
            return False
        except SessionValidationError as e:
            print(f"   ✓ Correctly rejected duplicate: {e}")

        print("\n3. Creating session with different operator_label...")
        session3 = await session_service.create_session(
            experiment_id=experiment.id,
            variant_id=variant.id,
            task_card_id=task_card.id,
            harness_profile="local",
            repo_path="/tmp/test3",
            git_branch="develop",
            git_commit="ghi9012",
            operator_label="different-identifier-456",
        )
        print(f"   ✓ Different label accepted: {session3.session_id}")

    print("\n✅ DEMO 3 PASSED: Duplicate session identifiers are rejected")
    return True


async def main():
    """Run all demonstrations."""
    print("\n" + "=" * 60)
    print("SESSION SERVICE DEMONSTRATION")
    print("Runtime Evidence for COE-305 Acceptance Criteria")
    print("=" * 60)

    start_time = datetime.now(UTC)
    print(f"\nStarted at: {start_time.isoformat()}")

    all_passed = True

    all_passed &= await demo_create_and_finalize_session()
    all_passed &= await demo_referential_integrity()
    all_passed &= await demo_duplicate_rejection()

    end_time = datetime.now(UTC)
    duration = (end_time - start_time).total_seconds()

    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)

    if all_passed:
        print("✅ ALL ACCEPTANCE CRITERIA VERIFIED")
        print("\n1. ✅ Services can create and finalize sessions safely")
        print("2. ✅ Repository methods preserve referential integrity")
        print("3. ✅ Duplicate session identifiers are rejected")
    else:
        print("❌ SOME ACCEPTANCE CRITERIA FAILED")

    print(f"\nCompleted at: {end_time.isoformat()}")
    print(f"Total duration: {duration:.2f} seconds")

    return 0 if all_passed else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
