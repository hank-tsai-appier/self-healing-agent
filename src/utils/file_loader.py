"""
Helpers for reading text files (e.g., conversation logs, generated code blocks).
"""

from __future__ import annotations

from pathlib import Path


class TextFileLoader:
    """
    Ensures the target file exists before reading.
    """

    def __init__(self, file_path: Path, hint: str | None = None):
        self.file_path = file_path
        self.hint = hint or "Required file not found."

    def read(self) -> str:
        if not self.file_path.exists():
            raise FileNotFoundError(f"{self.file_path} not found.\n{self.hint}")
        return self.file_path.read_text(encoding="utf-8")
