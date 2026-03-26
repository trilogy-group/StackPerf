"""Serialization utilities for reports and exports."""

import csv
import json
from pathlib import Path
from typing import Any


class ReportSerializer:
    """Serializer for benchmark reports in various formats."""

    @staticmethod
    def to_json(data: dict[str, Any], output_path: Path) -> None:
        """Serialize report to JSON."""
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w") as f:
            json.dump(data, f, indent=2, default=str)

    @staticmethod
    def to_csv(
        data: list[dict[str, Any]],
        output_path: Path,
        fieldnames: list[str] | None = None,
    ) -> None:
        """Serialize tabular data to CSV."""
        if not data:
            return

        output_path.parent.mkdir(parents=True, exist_ok=True)

        if fieldnames is None:
            fieldnames = list(data[0].keys())

        with open(output_path, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(data)

    @staticmethod
    def to_markdown(data: dict[str, Any], output_path: Path) -> None:
        """Serialize report to Markdown."""
        output_path.parent.mkdir(parents=True, exist_ok=True)

        lines = ["# Benchmark Report\n"]

        if "summary" in data:
            lines.append("## Summary\n")
            for key, value in data["summary"].items():
                lines.append(f"- **{key}**: {value}")
            lines.append("")

        if "comparisons" in data:
            lines.append("## Comparisons\n")
            lines.append("```json")
            lines.append(json.dumps(data["comparisons"], indent=2, default=str))
            lines.append("```\n")

        output_path.write_text("\n".join(lines))
