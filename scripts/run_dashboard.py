#!/usr/bin/env python3
"""CLI entry point for launching the Streamlit dashboard."""

import subprocess
import sys


def main():
    subprocess.run(
        [sys.executable, "-m", "streamlit", "run", "stockbot/dashboard/app.py",
         "--server.port", "8501"],
        check=True,
    )


if __name__ == "__main__":
    main()
