"""Module entry-point for ``python -m pressure_report`` in the starter repo."""

from src.pressure_report import *  # noqa: F401,F403

if __name__ == "__main__":
    from src.pressure_report import main

    raise SystemExit(main())
