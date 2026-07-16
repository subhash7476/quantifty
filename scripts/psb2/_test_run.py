"""Quick test: build null and signal panels, run harness."""
import sys, time
sys.path.insert(0, '.')
from pathlib import Path
from scripts.psb2.run_devproof import run_signal_test

out = Path("data/psb2_synthetic")
out.mkdir(parents=True, exist_ok=True)
t0 = time.time()

print("Building null...")
null = run_signal_test(out / "null.duckdb", "null")
for c in ["C2", "C3", "C4"]:
    r = null[c]
    ic = round(r.mean_ic, 4) if r.mean_ic is not None else None
    print(f"  Null {c}: n={len(r.ic) if r.ic is not None else 0} IC={ic}")

print("Building signal (c2)...")
sig = run_signal_test(out / "signal.duckdb", "c2")
for c in ["C2", "C3", "C4"]:
    r = sig[c]
    ic = round(r.mean_ic, 4) if r.mean_ic is not None else None
    print(f"  Sig {c}: n={len(r.ic) if r.ic is not None else 0} IC={ic}")

print(f"Time: {time.time()-t0:.1f}s")
