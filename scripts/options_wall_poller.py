"""Options-Wall chain poller entry point.

Usage:
    python scripts/options_wall_poller.py [--max-cycles N]
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.options_wall.poller import main

if __name__ == "__main__":
    raise SystemExit(main())
