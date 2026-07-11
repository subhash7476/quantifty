# MSRP Phase 6 — Pre-Flight Record

**Date:** 2026-07-07

**Status:** Pre-flight complete — all checks green, Stage 2 authorized pending operator GO

---

## 1. Block length L derivation (dossier §1.1 / design §2)

**Rule applied:** L = smallest lag k ≥ 1 with |ACF(k)| < 1.96/√n (standard white-noise band). Fallback: L = floor(n/20) if no lag satisfies the condition. Computed on dev-window RV (2023-01-02 → 2025-12-31, raw RV, not log) using `compute_daily_rv` from the certified `forward_vol.py`. Dev-dated files only — zero 2026 files opened.

**Derivation script:** `scripts/msrp/derive_block_length.py`

**Full ACF table:**
```
n_dev=722  band=1.96/sqrt(n)=0.072944  nlags=40
lag,acf,|acf|>=band
1,0.458094,True
2,0.276088,True
3,0.203097,True
4,0.188846,True
5,0.179169,True
6,0.143017,True
7,0.098493,True
8,0.147746,True
9,0.179316,True
10,0.203190,True
11,0.177885,True
12,0.161414,True
13,0.130191,True
14,0.129105,True
15,0.171771,True
16,0.176922,True
17,0.135446,True
18,0.100977,True
19,0.135432,True
20,0.145253,True
21,0.124744,True
22,0.130943,True
23,0.114485,True
24,0.106052,True
25,0.111142,True
26,0.108038,True
27,0.106522,True
28,0.062400,False
29,0.052872,False
30,0.130652,True
31,0.159558,True
32,0.245197,True
33,0.207824,True
34,0.105731,True
35,0.110358,True
36,0.086340,True
37,0.097832,True
38,0.052047,False
39,0.029670,False
40,0.073814,True
PINNED L=28  override=False
```

**Result:** Pinned `L = 28`, `override = False`. First lag below band is k=28 (|ACF|=0.062400 < 0.072944). `B = 10000`, `seed = 42` administratively pinned.

---

## 2. Seal-integrity & provenance

| Check | Result |
|-------|--------|
| No prior Phase-6 record for held-out window | CLEAN — no record with `evaluation_window == ["2026-01-01","2026-07-03"]` found in `core/msi/validations/` |
| Artifact checksum integrity | OK — `combined_hash` matches all per-file SHA-256 hashes |
| Data snapshot present | `data/market_data/nse/candles/1m/2026-07-03.duckdb` and `data/market_data/nse/candles/1d/2026-07-03.duckdb` both present |
| Code commit | `13156a3` (runner byte-identical to Phase-5B-certified `6e10142`) |

---

## 3. Dev-window rehearsal

**Command:** `python scripts/msrp/run_forward_vol_validation.py --phase 5B --window-start 2025-06-01 --window-end 2025-12-31 --block-length 28 --replicates 10000 --seed 42`

**Output:**
```
Validation 0efdc198be6fbdfe1c1e540c4844811c59c3e436819b18f0ae8fe30267ba87ed (Rejected) -> F:\Nifty\core\msi\validations\0efdc...
  delta_auc_gate=-0.000094 CI=(-0.123446, 0.132361) base_rate=0.442177 n=147
```

**Assessment:** Wiring OK — all numbers finite and sane (n=147 trading days, base_rate=0.44, CI properly bracketed). This is a dev-window smoke test; the numbers are not a decision input and are never cited as a result. The throwaway `--phase 5B` record was deleted. No held-out file was read. Rehearsal confirms the certified harness runs end-to-end against real candle data.

---

## 4. GO / NO-GO Packet

**Pinned substrate:**
- `L = 28` (derived from dev-window RV ACF, first lag below 1.96/√722 ≈ 0.073)
- `B = 10000` replicates
- `seed = 42`

**Exact Stage 2 command:**
```
python scripts/msrp/run_forward_vol_validation.py \
    --phase 6 \
    --window-start 2026-01-01 --window-end 2026-07-03 \
    --block-length 28 --replicates 10000 --seed 42
```

**Pre-flight evidence:**
- No prior Phase-6 record for the held-out window (clean)
- Artifact checksum verified: `e6185683...` (OK)
- Data snapshot present: `2026-07-03.duckdb` for both 1m and 1d
- Dev-window rehearsal: wiring confirmed, all numbers finite and sane
- Code commit: `38a3386`

**WARNING: The next step reads the sealed held-out window (2026-01-01 → 2026-07-03) exactly once, irreversibly. The Phase-6 duplicate guard prevents any second run on this window.**
