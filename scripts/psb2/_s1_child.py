"""S1 child: compute candidate results for determinism proof."""
import sys, json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from scripts.psb2.run_devproof import _build_signal, run_scenario
tmp = Path(sys.argv[1])
p = tmp / "s1.duckdb"
_build_signal(p, "null", seed_offset=999)
res = run_scenario(p, "null", seed_offset=999)
out = {c: {"n": len(res[c].ic) if res[c].ic is not None else 0,
           "mic": float(res[c].mean_ic) if res[c].mean_ic is not None else None}
       for c in ["C2", "C3", "C4"]}
sys.stdout.write(json.dumps(out, default=str))
