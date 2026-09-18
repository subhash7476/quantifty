"""JEV-NMS-1 §28 step 2 (draws) — the preregistered draws of Amendment 2 §A2-1.

Every draw uses its own fresh `random.Random(42)` over a population sorted
ascending (sessions by date; states by (date, slot)). Populations come only
from the accepted §28 step-1 eligibility artifact, whose SHA-256 is checked
first. D1 draws from OTHERWISE-eligible D-eval sessions; D3/D4/D5 from
ELIGIBLE ones - the predicates stay distinct even where the sets coincide.

Population-hash recipe (provenance only; cannot change a draw): SHA-256 of
the UTF-8 newline-joined keys in population order, session key `YYYY-MM-DD`,
state key `YYYY-MM-DD|HH:MM`.

The artifact is create-only; an existing draw artifact is never redrawn.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import random
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
OUT = REPO / "data" / "jev_market_state"
ELIGIBILITY = OUT / "eligibility_step1.json"
ELIGIBILITY_SHA256 = "b5d1cd48b11667c15a3d744ebea81db7d0a11c7aa03a7e4420e2e9dc98344c77"
ARTIFACT_NAME = "draws_step2.json"
SEED = 42
SLOTS = ["10:00", "10:30", "11:00", "11:30", "12:00", "12:30", "13:00", "13:30", "14:00", "14:30"]
S0_SLOTS = ["10:00", "14:30"]
L2_YEARS = (2023, 2024, 2025)


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def population_hash(keys: list[str]) -> str:
    return sha256_bytes("\n".join(keys).encode("utf-8"))


def state_key(state: tuple[str, str]) -> str:
    return f"{state[0]}|{state[1]}"


def load_eligibility() -> dict:
    raw = ELIGIBILITY.read_bytes()
    if sha256_bytes(raw) != ELIGIBILITY_SHA256:
        raise RuntimeError("eligibility_step1.json does not match the accepted step-1 SHA-256")
    return json.loads(raw.decode("utf-8"))


def _sample(population: list, k: int) -> list:
    return random.Random(SEED).sample(population, k)


def _manifest(population: list[str], k, output: list[str], procedure: str) -> dict:
    return {"population_size": len(population), "population_sha256": population_hash(population),
            "k": k, "procedure": procedure, "output": output}


def make_draws(elig: dict) -> dict:
    sessions = elig["sessions"]
    eligible = {name: sorted(r["date"] for r in recs if r["eligible"])
                for name, recs in sessions.items() if name in ("d_fit", "d_eval")}
    otherwise_eval = sorted(r["date"] for r in sessions["d_eval"] if r["otherwise_eligible"])

    d1 = _sample(otherwise_eval, 100)
    d2 = d1[:30]
    d3 = _sample(eligible["d_fit"], 5)
    d3_states = sorted((d, s) for d in d3 for s in S0_SLOTS)

    dev_pool = sorted(eligible["d_fit"] + eligible["d_eval"])
    d4 = {}
    for year in L2_YEARS:
        pop = [d for d in dev_pool if d.startswith(f"{year}-")]
        d4[year] = (pop, _sample(pop, 30))
    l2_sessions = sorted(d for _, out in d4.values() for d in out)
    rng_t = random.Random(SEED)
    d4t = [(d, rng_t.choice(SLOTS)) for d in l2_sessions]

    excluded = (set(d3_states) | set(d4t)
                | {(d, s) for d in d1 for s in SLOTS})
    all_states = sorted((d, s) for d in dev_pool for s in SLOTS)
    l3_pop = [st for st in all_states if st not in excluded]
    d5 = _sample(l3_pop, 50)
    d6 = d5[:20]

    return {
        "d1_dev": _manifest(otherwise_eval, 100, d1, "random.sample(pop, 100)"),
        "d2_dev_secondary": {"derived": "first 30 of d1 output", "output": d2},
        "d3_s0": {**_manifest(eligible["d_fit"], 5, d3, "random.sample(pop, 5)"),
                  "states": [state_key(s) for s in d3_states]},
        **{f"d4_l2_{y}": _manifest(pop, 30, out, "random.sample(pop_year, 30)")
           for y, (pop, out) in d4.items()},
        "d4t_l2_timestamps": {**_manifest(l2_sessions, "one choice per session",
                                          [state_key(s) for s in d4t],
                                          "for each session in date order: rng.choice(SLOTS)"),
                              "slots": SLOTS},
        "d5_l3": {**_manifest([state_key(s) for s in l3_pop], 50, [state_key(s) for s in d5],
                              "random.sample(pop, 50) after d1, d3, d4, d4t"),
                  "all_states_before_exclusion": len(all_states),
                  "excluded_states": len(excluded)},
        "d6_canaries": {"derived": "first 20 of d5 output", "output": [state_key(s) for s in d6]},
        "check_d1_otherwise_eligible_equals_eligible_d_eval": otherwise_eval == eligible["d_eval"],
    }


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    target = OUT / ARTIFACT_NAME
    if target.exists():
        raise SystemExit(f"{target} exists; an authoritative draw is never redrawn")
    elig = load_eligibility()
    artifact = {
        "protocol_id": "JEV-NMS-1", "step": "section 28 step 2 - draws (A2-1)",
        "eligibility_sha256": ELIGIBILITY_SHA256, "seed": SEED,
        "rng": "python stdlib random.Random(42), fresh instance per draw",
        "python": sys.version,
        "population_hash_recipe": "sha256(utf-8 '\\n'.join(keys)); session 'YYYY-MM-DD', state 'YYYY-MM-DD|HH:MM'",
        "built_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "draws": make_draws(elig),
    }
    summary = {k: (v.get("population_size"), len(v["output"])) if isinstance(v, dict) else v
               for k, v in artifact["draws"].items()}
    print(json.dumps(summary))
    if args.dry_run:
        return
    with open(target, "x", encoding="utf-8", newline="") as fh:
        fh.write(json.dumps(artifact, indent=1, sort_keys=True))
    digest = sha256_bytes(target.read_bytes())
    with open(OUT / "ledger.jsonl", "a", encoding="utf-8", newline="") as fh:
        fh.write(json.dumps({"event": "draws_made", "at": artifact["built_at"],
                             "artifact": ARTIFACT_NAME, "sha256": digest}) + "\n")
    print(f"{target}  sha256={digest}")


if __name__ == "__main__":
    main()
