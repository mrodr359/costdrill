"""
Report generation for exporting cost data.
"""

import csv
import json
from pathlib import Path
from typing import Any, Dict, List


class ReportGenerator:
    """Generate reports in various formats."""

    @staticmethod
    def to_json(data: Dict[str, Any], output_path: Path) -> None:
        """
        Export data to JSON format.

        Args:
            data: Data to export
            output_path: Path to output file
        """
        with open(output_path, "w") as f:
            json.dump(data, f, indent=2, default=str)

    @staticmethod
    def to_csv(data: List[Dict[str, Any]], output_path: Path) -> None:
        """
        Export data to CSV format.

        Args:
            data: List of dictionaries to export
            output_path: Path to output file
        """
        if not data:
            return

        with open(output_path, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=data[0].keys())
            writer.writeheader()
            writer.writerows(data)

    @staticmethod
    def to_markdown(data: Dict[str, Any], output_path: Path, title: str = "Cost Report") -> None:
        """
        Export data to Markdown format.

        Args:
            data: Data to export
            output_path: Path to output file
            title: Report title
        """
        with open(output_path, "w") as f:
            f.write(f"# {title}\n\n")
            f.write(f"Generated: {data.get('generated_at', 'N/A')}\n\n")

            # TODO: Format data into markdown tables
            f.write("## Cost Summary\n\n")
            f.write("```json\n")
            f.write(json.dumps(data, indent=2, default=str))
            f.write("\n```\n")
