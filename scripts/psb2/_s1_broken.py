import sys
sys.path.insert(0, 'F:\\Nifty')
import json
from pathlib import Path
from scripts.psb2.run_devproof import _build_signal
tmp = Path(sys.argv[1])
p = tmp / "s1_broken.duckdb"
_build_signal(p, "null", seed_offset=888)
# deliberately wrong: compute wrong result
res = {"C2": None, "C3": None, "C4": None}
sys.stdout.write(json.dumps(res))
