"""Compatibility script entry point used by PyInstaller build specs."""

from pathlib import Path
import sys


if __package__ in (None, ""):
    repository_root = str(Path(__file__).resolve().parents[2])
    if repository_root not in sys.path:
        sys.path.insert(0, repository_root)

from src.core.application import run


def main() -> int:
    return run()


if __name__ == "__main__":
    raise SystemExit(main())

