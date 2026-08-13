"""Module entry-point kept for learners who prefer ``python -m telemetry_report``."""

from src.pressure_report import *  # noqa: F401,F403

if __name__ == "__main__":
    from src.pressure_report import main

    raise SystemExit(main())
