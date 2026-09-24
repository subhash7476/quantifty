"""Script-written screen report (freeze §13). No number is typed by hand.

The fixed text (A.0 title block, F-1 … F-9, the A.2 wording, X-1 … X-8) is read from the **frozen
document's committed bytes**, never retyped, so it cannot drift from the freeze. A.2's wording is chosen
by rule (`outcome_row`). A.5 is asserted: the script-generated text (everything that is not a fixed
statement) must not contain a forbidden phrase. Fixed statements are exempt because the template itself
quotes those phrases in order to forbid them.
"""

import re

from scripts.ptms.gann.constants import ALPHA, N_SURROGATES, SEED, SIZE_CHECK_MAX_REJECTION

FORBIDDEN = re.compile(r"\b(validated|validation|confirmed|works|edge)\b|Gann's rule is (false|true)", re.I)
N_A2_ROWS = 4


def _between(text, start, end):
    i = text.index(start)
    return text[i:text.index(end, i)]


def _cells(line):
    return [c.strip() for c in line.strip().strip("|").split("|")]


def fixed_text(freeze_text):
    """The template's fixed statements, taken from the frozen document (§13)."""
    s13 = _between(freeze_text, "## 13. Report template", "## 14. ")
    rows = {}
    for line in s13.splitlines():
        m = re.match(r"\| ((?:F|X)-\d) \|", line)
        if m:
            rows[m.group(1)] = _cells(line)[1]
    a2 = [_cells(l) for l in _between(s13, "##### A.2", "The specificity leg is:").splitlines()
          if l.startswith("| ") and not l.startswith("| Outcome")]
    title = [re.sub(r"^> ?", "", l) for l in _between(s13, "##### A.0", "##### A.1").splitlines() if l.startswith(">")]
    missing = [k for k in [f"F-{i}" for i in range(1, 10)] + [f"X-{i}" for i in range(1, 9)] if k not in rows]
    if missing or len(a2) != N_A2_ROWS or not title:
        raise SystemExit(f"frozen template incomplete: missing {missing}, {len(a2)} A.2 rows")
    return {"F": [rows[f"F-{i}"] for i in range(1, 10)], "X": {k: v for k, v in rows.items() if k[0] == "X"},
            "A2": [r[1] for r in a2], "title": title}


def outcome_row(size_passed, p_sur, spec_p):
    """A.2, by rule: 0 retired on the surrogate leg; 1 not shown Gann-specific (retired, G-1);
    2 survived both legs; 3 size check failed."""
    if not size_passed:
        return 3
    if p_sur > ALPHA:
        return 0
    return 1 if spec_p > ALPHA else 2


class _Doc:
    def __init__(self):
        self.parts = []

    def gen(self, text=""):
        self.parts.append((text, False))

    def fixed(self, text):
        self.parts.append((text, True))

    def text(self):
        bad = [t for t, is_fixed in self.parts if not is_fixed and FORBIDDEN.search(t)]
        if bad:
            raise AssertionError(f"A.5: forbidden phrasing in generated text: {bad[:3]}")
        return "\n".join(t for t, _ in self.parts) + "\n"


def _v(x, fmt="+.4f"):
    return "undefined" if x is None or x != x else format(x, fmt)


def _p(x):
    return "—" if x is None else _v(x, ".4f")


def _tc(tc):
    return f"{_v(tc['value'])} ({tc['n_dates']} dates)"


def render(res, fixed):
    """res: the results dict written by run_screen (every number script-generated)."""
    d = _Doc()
    pv = res["provenance"]
    title = "\n".join(fixed["title"])
    for key, val in (("{{freeze document path}}", pv["freeze_path"]), ("{{digest}}", pv["digest"]),
                     ("{{date}}", pv["g_s1_date"]), ("{{path}}", pv["script"]), ("{{sha}}", pv["head"])):
        title = title.replace(key, val)
    if "{{" in title:
        raise AssertionError("unfilled title placeholder")
    d.fixed(title)
    d.gen()

    d.gen("## 1. Protocol and provenance\n")
    d.gen("| Item | Value |\n|---|---|")
    for label, key in (("Frozen protocol", "freeze_path"), ("SHA-256", "digest"), ("Freeze commit", "freeze_commit"),
                       ("Script commit", "head"), ("Register row G-S1 appended", "g_s1_date"),
                       ("Size-check record", "size_record"), ("G-7 event list SHA-256", "g7_csv_sha256"),
                       ("P-2 CA enumeration commit", "p2_commit"), ("Panel content SHA-256", "panel_sha256")):
        d.gen(f"| {label} | `{pv[key]}` |")
    d.gen(f"| Seed | {SEED} |\n| B | {N_SURROGATES} |\n| α (one-sided) | 0.05/3 |\n")

    d.gen("## 2. Blind size check (recorded before unblinding)\n")
    d.gen(f"| Construct | Rejections / panels | Rate | Limit 2α | Action |\n|---|--:|--:|--:|---|")
    for c, s in res["size_check"].items():
        action = "screened" if s["passed"] else "stopped (G-9b)"
        d.gen(f"| {c} | {s['n_reject']} / {s['n_panels']} | {s['rate']:.4f} | {SIZE_CHECK_MAX_REJECTION:.4f} | {action} |")
    d.gen()

    d.gen("## 3. Panel and exclusions\n")
    for c, r in res["constructs"].items():
        d.gen(f"### {c}\n")
        if r["status"] != "screened":
            d.fixed(fixed["A2"][3])
            d.gen()
            continue
        pn = r["panel"]
        d.gen("| Item | Count |\n|---|--:|")
        d.gen(f"| Eligible stock-weeks kept after OPEN-M and G-7 | {pn['n_obs']} |")
        d.gen(f"| Formation dates entering T_c | {r['T_c']['n_dates']} |")
        d.gen(f"| Dates dropped by the 20-name floor (G-6b) | {r['T_c']['n_dropped_floor']} |")
        d.gen(f"| Observations excluded by OPEN-M | {pn['n_open_m']} |")
        d.gen(f"| Observations excluded by G-7 (from the 115 G-7 events) | {pn['n_g7']} |")
        if "n_open_n" in pn:
            d.gen(f"| Contrast weeks excluded by OPEN-N | {pn['n_open_n']} |")
        d.gen()
        d.gen("Dates dropped because the per-date IC was undefined (A.3-3a, OPEN-P):\n")
        d.gen("| Leg | Real panel | Surrogate median |\n|---|--:|--:|")
        for leg, u in pn["undefined_ic"].items():
            d.gen(f"| {leg} | {u['real']} | {u['surrogate_median']} |")
        d.gen()
        bh = pn["exclusion_loss"]
        d.gen(f"Exclusion-loss share (D-BH); base = {bh['base_label']}, {bh['base']} stock-weeks:\n")
        d.gen("| Limb | Count | Share |\n|---|--:|--:|")
        for limb, n in bh["limbs"].items():
            d.gen(f"| {limb} | {n} | {bh['shares'][limb]:.4f} |")
        d.gen()

    d.gen("## 4. Primary results\n")
    d.gen("| Construct | T_c | p_sur | Specificity p | Effect size | 2.5–97.5% surrogate interval |\n|---|--:|--:|--:|--:|---|")
    for c, r in res["constructs"].items():
        if r["status"] != "screened":
            d.gen(f"| {c} | — | — | — | — | — |")
            continue
        lo, hi = r["interval"]
        d.gen(f"| {c} | {_v(r['T_c']['value'])} | {_p(r['p_sur'])} | {_p(r['spec_p'])} | {_v(r['effect'])} | "
              f"[{_v(lo)}, {_v(hi)}] |")
    d.gen()
    for c, r in res["constructs"].items():
        d.gen(f"**{c}:**")
        d.fixed(fixed["A2"][r["outcome_row"]])
        d.gen()
    g10 = res["constructs"].get("GF-10", {})
    if g10.get("status") == "screened":
        ct = g10["contrast"]
        d.gen(f"GF-10 specificity leg (G-4): T(time) {_tc(ct['time'])}, T(price) {_tc(ct['price'])}, "
              f"Δ = {_v(ct['delta'])}, p = {_p(g10['spec_p'])} over {N_SURROGATES} joint surrogate panels.\n")

    d.gen("## 5. Robustness variants\n")
    d.fixed(fixed["F"][7])
    d.gen()
    d.gen("| Construct | Variant | T_c | Effect size | p_sur |\n|---|---|--:|--:|--:|")
    for c, vs in res["variants"].items():
        for name, v in vs.items():
            d.gen(f"| {c} | {name} | {_tc(v['T_c'])} | {_v(v['effect'])} | {_p(v.get('p_sur'))} |")
    d.gen("\nEffect sizes are against the primary's surrogate distribution (R-A); V-B5 and V-B60 use their own "
          "surrogate runs and report p_sur (R-A′).\n")

    d.gen("## 6. Diagnostics\n")
    d.gen("Price-level halves at the per-date median as-traded close on D_L (D-PL, floor 10 per half):\n")
    d.gen("| Construct | Low half T_c | High half T_c | Stock-weeks without an as-traded bar on D_L |\n|---|--:|--:|--:|")
    for c, x in res["diagnostics"]["D-PL"].items():
        d.gen(f"| {c} | {_tc(x['low'])} | {_tc(x['high'])} | {x['n_no_bar']} |")
    if "D-AA" in res["diagnostics"]:
        d.gen("\nGF-1 store-history depth at D_L, in weeks (D-AA):\n")
        d.gen("| Stratum | T_c |\n|---|--:|")
        for k, x in res["diagnostics"]["D-AA"].items():
            d.gen(f"| {k} | {_tc(x)} |")
    d.gen("\nPer-stock φ (D-PS; stocks with ≥ 5 score-1 and ≥ 5 score-0 weeks; descriptive):\n")
    d.gen("| Construct | Qualifying stocks | Outcome constant (left out) | Median φ | IQR | Share φ > 0 |\n|---|--:|--:|--:|---|--:|")
    for c, x in res["diagnostics"]["D-PS"].items():
        s = x["summary"]
        d.gen(f"| {c} | {s['n_stocks']} | {s['n_undefined']} | {_v(s.get('median'))} | "
              f"[{_v(s.get('q1'))}, {_v(s.get('q3'))}] | {_v(s.get('share_positive'), '.3f')} |")
    d.gen()

    d.gen("## 7. GF-10 disclosures\n")
    x1 = fixed["X"]["X-1"]
    for n in res.get("gf10_structural_zeros", {}).values():
        x1 = x1.replace("`{{n}}`", f"`{n}`", 1)
    d.gen("| # | Disclosure |\n|---|---|")
    for k in [f"X-{i}" for i in range(1, 9)]:
        d.fixed(f"| {k} | {x1 if k == 'X-1' else fixed['X'][k]} |")
    d.gen()

    d.gen("## 8. Limitations\n")
    for i, s in enumerate(fixed["F"], 1):
        d.fixed(f"- F-{i}: {s}")
    d.gen()

    d.gen("## Appendix — per-stock φ (D-PS)\n")
    for c, x in res["diagnostics"]["D-PS"].items():
        d.gen(f"### {c}\n\n| Stock | Score-1 weeks | Score-0 weeks | φ |\n|---|--:|--:|--:|")
        for ent, n1, n0, phi in x["stocks"]:
            d.gen(f"| {ent} | {n1} | {n0} | {_v(phi)} |")
        d.gen()
    return d.text()
