#!/usr/bin/env python3
"""Demo script to verify ComparisonService works correctly.

Run with: python3 scripts/demo_comparison.py
"""

import sys
import os

# Add project src to path - use absolute path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(project_root, 'src'))

import asyncio
from uuid import uuid4
from unittest.mock import MagicMock

# Verify all imports work
from reporting.comparison import (
    ComparisonService,
    VariantComparison,
    ProviderComparison,
    ModelComparison,
    HarnessProfileComparison,
    ExperimentComparisonResult,
)
from reporting.queries import DashboardQueries


def verify_service():
    """Verify ComparisonService can be instantiated and used."""
    # Create mock database session
    mock_db = MagicMock()
    
    # Create service
    service = ComparisonService(db_session=mock_db)
    print(f"✓ ComparisonService created successfully")
    
    # Verify compare_sessions handles empty input
    result = asyncio.run(service.compare_sessions([]))
    assert result == {"sessions": [], "summary": {}}
    print(f"✓ compare_sessions([]) returns empty result")
    
    # Verify compare_variants returns empty for missing experiment
    mock_db.get.return_value = None
    result = asyncio.run(service.compare_variants(uuid4()))
    assert result == []
    print(f"✓ compare_variants returns [] for missing experiment")
    
    return service


def verify_models():
    """Verify Pydantic models work correctly."""
    variant_id = uuid4()
    vc = VariantComparison(
        variant_id=variant_id,
        variant_name="gpt-4-turbo",
        provider="openai",
        model="gpt-4-turbo",
        harness_profile="default",
        session_count=10,
        total_requests=150,
        avg_latency_ms=245.5,
        avg_ttft_ms=120.3,
        total_errors=3,
        error_rate=0.02
    )
    print(f"✓ VariantComparison model works: {vc.variant_name}")
    
    # Verify JSON serialization
    json_str = vc.model_dump_json()
    assert "gpt-4-turbo" in json_str
    assert str(variant_id) in json_str
    print(f"✓ JSON serialization works: {len(json_str)} chars")
    
    # Verify ExperimentComparisonResult
    exp_id = uuid4()
    ecr = ExperimentComparisonResult(
        experiment_id=exp_id,
        experiment_name="test-experiment",
        variants=[vc],
        providers=[],
        models=[],
        harness_profiles=[]
    )
    assert ecr.experiment_name == "test-experiment"
    assert len(ecr.variants) == 1
    print(f"✓ ExperimentComparisonResult model works")
    
    return vc, ecr


def verify_queries():
    """Verify DashboardQueries generate correct SQL."""
    # Verify variant summary query
    sql, params = DashboardQueries.variant_summary_valid_only()
    assert "SELECT" in sql
    assert ":experiment_id" in sql
    assert "outcome_state != 'invalid'" in sql
    assert "ORDER BY v.name ASC" in sql
    assert params == {"experiment_id": None}
    print(f"✓ variant_summary_valid_only() generates correct SQL")
    
    # Verify provider summary query
    sql, params = DashboardQueries.provider_summary_valid_only()
    assert "v.provider" in sql
    assert "ORDER BY v.provider ASC" in sql
    print(f"✓ provider_summary_valid_only() generates correct SQL")
    
    # Verify model summary query
    sql, params = DashboardQueries.model_summary_valid_only()
    assert "v.model_alias" in sql
    assert "ORDER BY v.provider ASC, v.model_alias ASC" in sql
    print(f"✓ model_summary_valid_only() generates correct SQL")
    
    # Verify harness profile summary query
    sql, params = DashboardQueries.harness_profile_summary_valid_only()
    assert "v.harness_profile" in sql
    assert "ORDER BY v.harness_profile ASC" in sql
    print(f"✓ harness_profile_summary_valid_only() generates correct SQL")


def main():
    """Run all verification checks."""
    print("=== COE-314 Comparison Service Verification ===\n")
    
    print("1. Verifying ComparisonService...")
    verify_service()
    
    print("\n2. Verifying Pydantic models...")
    verify_models()
    
    print("\n3. Verifying DashboardQueries...")
    verify_queries()
    
    print("\n=== All verification checks passed! ===")


if __name__ == "__main__":
    main()