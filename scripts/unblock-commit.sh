#!/bin/bash
# Helper script for COE-227 commit workflow
# Run this after sandbox restrictions are lifted

set -e

echo "=== COE-227: Canonical Data Store and Collection Pipeline ==="
echo ""

# Check we're in the right directory
if [ ! -f "pyproject.toml" ]; then
    echo "ERROR: Run this from the COE-227 repository root"
    exit 1
fi

# Create feature branch
BRANCH="leonardogonzalez/coe-227-canonical-data-store-and-collection-pipeline"
echo "Creating branch: $BRANCH"
git checkout -b "$BRANCH" 2>/dev/null || git checkout "$BRANCH"

# Stage all changes
echo "Staging changes..."
git add -A

# Show what will be committed
echo ""
echo "Files to be committed:"
git status --short

# Commit
echo ""
echo "Committing..."
git commit -m "feat: implement canonical data store and collection pipeline

- Database schema with 9 tables (providers, harness_profiles, variants,
  experiments, task_cards, sessions, requests, metric_rollups, artifacts)
- Repository layer with FK integrity and SQLAlchemy models
- SessionService for create/finalize with duplicate rejection
- LiteLLM collector with correlation key extraction and diagnostics
- RequestNormalizer with session/variant joins and unmapped row surfacing
- MetricRollupService computing median/p95 using numpy.percentile
- PrometheusCollector for operational metrics
- Unit and integration tests

Refs: COE-227"

echo ""
echo "Pushing to origin..."
git push -u origin "$BRANCH"

echo ""
echo "=== Commit complete ==="
echo "Next steps:"
echo "1. pip install -e '.[dev]'"
echo "2. pytest tests/ -v"
echo "3. gh pr create --title 'COE-227: Canonical Data Store and Collection Pipeline' \\"
echo "     --body 'Implements database schema, repositories, collectors, normalization, and rollups.' \\"
echo "     --label symphony"
