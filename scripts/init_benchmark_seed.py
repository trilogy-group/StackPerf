#!/usr/bin/env python3
"""Initialize and seed benchmark tables for local Grafana verification."""

from datetime import UTC, datetime, timedelta

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from benchmark_core.db.models import Experiment, ExperimentVariant, Request, TaskCard, Variant
from benchmark_core.db.models import Session as BenchmarkSession
from benchmark_core.db.session import get_database_url, init_db


EXPERIMENT_NAME = "demo-grafana-validation"


def main() -> None:
    engine = create_engine(get_database_url(), pool_pre_ping=True)
    init_db(engine)

    with Session(engine) as session:
        existing = session.execute(
            select(Experiment).where(Experiment.name == EXPERIMENT_NAME)
        ).scalar_one_or_none()
        if existing is not None:
            print(f"Benchmark seed already present: {EXPERIMENT_NAME}")
            return

        now = datetime.now(UTC)
        task_card = TaskCard(
            name="grafana-demo-task",
            repo_path="/workspace",
            goal="Seed benchmark data for Grafana validation",
            starting_prompt="Validate dashboard wiring against seeded benchmark data.",
            stop_condition="Dashboards display seeded historical metrics.",
            session_timebox_minutes=30,
            notes=["seeded", "grafana", "validation"],
        )

        experiment = Experiment(
            name=EXPERIMENT_NAME,
            description="Seeded benchmark data for local Grafana dashboard verification.",
        )

        variants = [
            Variant(
                name="fireworks-kimi-k2-5-demo",
                provider="fireworks",
                provider_route="fireworks-main",
                model_alias="kimi-k2-5",
                harness_profile="claude-code",
                benchmark_tags={"provider": "fireworks", "model": "kimi-k2-5"},
            ),
            Variant(
                name="fireworks-glm-5-demo",
                provider="fireworks",
                provider_route="fireworks-main",
                model_alias="glm-5",
                harness_profile="claude-code",
                benchmark_tags={"provider": "fireworks", "model": "glm-5"},
            ),
        ]

        session.add_all([task_card, experiment, *variants])
        session.flush()

        session.add_all(
            [
                ExperimentVariant(experiment_id=experiment.id, variant_id=variant.id)
                for variant in variants
            ]
        )

        session_specs = [
            (
                variants[0],
                "completed",
                "success",
                18,
                [480, 520, 610],
                [130, 150, 170],
                [320, 340, 360],
            ),
            (
                variants[0],
                "completed",
                "success",
                12,
                [450, 470, 500],
                [120, 135, 145],
                [300, 315, 325],
            ),
            (
                variants[1],
                "completed",
                "failed",
                27,
                [720, 760, 910],
                [210, 240, None],
                [280, 290, 300],
            ),
            (
                variants[1],
                "completed",
                "success",
                22,
                [640, 680, 710],
                [180, 195, 205],
                [295, 305, 315],
            ),
        ]

        for index, (variant, status, outcome, minutes, latencies, ttfts, completions) in enumerate(
            session_specs
        ):
            started_at = now - timedelta(hours=index + 1)
            benchmark_session = BenchmarkSession(
                experiment_id=experiment.id,
                variant_id=variant.id,
                task_card_id=task_card.id,
                harness_profile=variant.harness_profile,
                repo_path="/workspace",
                git_branch="COE-316-grafana-dashboards",
                git_commit="seeded-demo",
                git_dirty=False,
                operator_label="grafana-seed",
                started_at=started_at,
                ended_at=started_at + timedelta(minutes=minutes),
                status=status,
                outcome_state=outcome,
            )
            session.add(benchmark_session)
            session.flush()

            for req_index, latency in enumerate(latencies):
                ttft = ttfts[req_index]
                completion_tokens = completions[req_index]
                error = outcome == "failed" and req_index == len(latencies) - 1
                request = Request(
                    request_id=f"seed-{index}-{req_index}",
                    session_id=benchmark_session.id,
                    provider=variant.provider,
                    model=variant.model_alias,
                    timestamp=started_at + timedelta(minutes=req_index * 2),
                    latency_ms=float(latency),
                    ttft_ms=None if ttft is None else float(ttft),
                    tokens_prompt=180 + req_index * 10,
                    tokens_completion=completion_tokens,
                    error=error,
                    error_message="Synthetic provider timeout" if error else None,
                    cache_hit=req_index == 0,
                    request_metadata={"seeded": True, "requested_model": variant.model_alias},
                )
                session.add(request)

        session.commit()
        print(f"Seeded benchmark data for experiment: {EXPERIMENT_NAME}")


if __name__ == "__main__":
    main()
