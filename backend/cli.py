"""Dev CLI for the ALARMI backend.

Entry points are wired in pyproject.toml under [project.scripts], so these run
via uv:

    uv run dev                  run the server (--reload, :8000)
    uv run dev --seed           seed demo data first, then run
    uv run dev --reset          delete the local DB first (fresh), then run
    uv run dev --reset --seed   wipe, re-seed, then run (clean slate + demo data)
    uv run dev --port 8001      run on a different port

    uv run seed                 just (re)seed demo data, don't start the server
"""

import argparse
import os
import subprocess
import sys

DB = "alarmi.db"


def _run(cmd: list[str]) -> int:
    """Run a subprocess with the venv's Python, inheriting stdio + signals."""
    return subprocess.run(cmd).returncode


def dev() -> None:
    parser = argparse.ArgumentParser(
        prog="dev", description="Run the ALARMI backend for local development."
    )
    parser.add_argument("--seed", action="store_true", help="Seed demo data before starting.")
    parser.add_argument("--reset", action="store_true", help="Delete the local DB first (fresh, empty).")
    parser.add_argument("--port", type=int, default=8000, help="Port to serve on (default: 8000).")
    args = parser.parse_args()

    if args.reset and os.path.exists(DB):
        print(f"dev: removing {DB} (fresh start)", flush=True)
        os.remove(DB)

    if args.seed:
        print("dev: seeding demo data", flush=True)
        _run([sys.executable, "-m", "app.seed"])

    print(f"dev: starting server on :{args.port}", flush=True)
    _run(
        [sys.executable, "-m", "uvicorn", "app.main:app", "--reload", "--port", str(args.port)]
    )


def seed() -> None:
    """Populate demo data without starting the server."""
    sys.exit(_run([sys.executable, "-m", "app.seed"]))
