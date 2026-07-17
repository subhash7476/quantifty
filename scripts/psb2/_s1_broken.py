"""S1 deliberate break: crashes with returncode=1 to trip S1's guard."""
import sys, json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from scripts.psb2.run_devproof import _build_signal
tmp = Path(sys.argv[1])
p = tmp / "s1_broken.duckdb"
_build_signal(p, "null", seed_offset=888)
raise SystemExit(1)
