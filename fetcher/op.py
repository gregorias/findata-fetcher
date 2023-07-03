"""A wrapper for the 1Password CLI."""

import subprocess


def read(vault: str, item: str, field: str) -> str:
    """Fetches a field from an item in a vault."""
    return subprocess.run(
        ["op", "read", f"op://{vault}/{item}/{field}", "--no-newline"],
        capture_output=True,
        check=True,
        text=True).stdout
