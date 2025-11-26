"""
Cypress test execution utilities, including ARIA snapshot extraction.
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Optional, Tuple


class SubprocessExecutor:
    """
    Execute Cypress specs via yarn and enhance failure output with ARIA snapshots.
    """

    def __init__(self, workspace_path: str):
        self.workspace_path = workspace_path

    def run(self, test_file_path: str) -> Tuple[bool, str]:
        """
        Run the Cypress spec and return (success, combined stdout/stderr).
        """
        cmd = [
            "yarn",
            "run",
            "cy-run",
            "-b",
            "electron",
            "--headed",
            "--spec",
            test_file_path,
        ]

        result = subprocess.run(
            cmd,
            cwd=self.workspace_path,
            capture_output=True,
            text=True,
            timeout=600,
        )

        success = result.returncode == 0
        output = result.stdout + result.stderr

        if not success:
            aria_snapshot = self._extract_aria_snapshot(output)
            if aria_snapshot:
                output += "\n\n" + "=" * 80 + "\n"
                output += "CYPRESS ARIA SNAPSHOT (Extracted from Test Output)\n"
                output += "=" * 80 + "\n"
                snapshot_display = (
                    aria_snapshot[-30000:]
                    if len(aria_snapshot) > 30000
                    else aria_snapshot
                )
                output += snapshot_display
                if len(aria_snapshot) > 30000:
                    output += "\n... (truncated, showing last 30000 characters)"
                output += "\n" + "=" * 80 + "\n"

        return success, output

    @staticmethod
    def _extract_aria_snapshot(output: str) -> Optional[str]:
        marker_start = "ARIA SNAPSHOT (Accessibility Tree)"
        separator = "=" * 80

        start_idx = output.find(marker_start)
        if start_idx == -1:
            return None

        marker_line_end = output.find("\n", start_idx)
        if marker_line_end == -1:
            return None

        content_start = marker_line_end + 1
        while (
            content_start < len(output)
            and output[content_start : content_start + 80] == separator
        ):
            next_line = output.find("\n", content_start)
            if next_line == -1:
                return None
            content_start = next_line + 1

        end_idx = output.find(separator, content_start)
        if end_idx == -1:
            snapshot = output[content_start:].strip()
        else:
            snapshot = output[content_start:end_idx].strip()

        return snapshot or None

