# Prompt for Claude Design — Options Wall page redesign

Paste everything below the line into Claude Design. It is self-contained: the data
contract, the reading order the layout must follow, the house style, and the
constraints of the Flask template it will be ported back into.

---

## Brief

Redesign one screen of an internal trading terminal: the **Options Wall** page for
NIFTY and BANKNIFTY index options. It is a research instrument, not a signal service.
The page reads one persisted chain snapshot and shows what the dealer book looks like
right now: which way dealer hedging pushes, how big, how concentrated, where the
levels are, and what the book has done since the open. Below that it lists the
scanner's ranked "farm list" and a 30-session regime river.

Design a desktop-first canvas (1440 wide, responsive down to 1024) with **three
artboards**: (1) the full page in a normal Positive-gamma session, (2) the same page
in a **Neutral / dispersed** session where most panels should visibly demote
themselves, (3) the slide-over detail panel for one farm-list row. Use real-looking
numbers from the sample payload below; do not invent metrics that are not in it.

## The reading order is the layout

Every value on this page is read in a fixed order, and each answer changes what the
next number means. The page must make that order physical, top to bottom:

1. **Which way does hedging push?** Regime (Positive / Neutral / Negative) and net
   GEX in ₹ crore, with the dealer-side inference coverage and the theta-drift flag
   right next to it. If the side read is unreliable, everything below is provisional
   and should look it.
2. **How much room?** Spot-to-flip distance, shown in **sigma**, not points.
3. **Can the levels be trusted?** HHI concentration with its band
   (COMPRESSED / BALANCED / DISPERSED). This is a gate: a DISPERSED book should visibly
   soften every level panel below it (the copy says "use zones, not lines").
4. **Where are the edges?** Pin (with conviction, margin, runner-up, GEX at pin),
   gamma ceiling / floor, OI call / put wall, gamma flip — each with its distance
   from spot in sigma.
5. **Is the board fresh or leftover?** OI added / unwound since 09:15, vol/OI.
6. **What does the dealer have to do next?** The hedge ladder: forced futures flow at
   ±0.5 / 1.0 / 1.5 %.
7. Only then the **farm list** and the **regime river**.

Reference for the genre: hedgewall.in's landing page and "Read the terminal" guide
(dealer-positioning terminal, ₹ crore GEX, pin conviction, HHI gate, sigma yardstick).
Match the *discipline* — every number carries its unit, its band and its caveat — not
the visual style.

## Data contract (what the page has, nothing more)

`GET /options/wall/api/farm?index=NIFTY` returns `{ index, ts, regime, rows }`.

`regime` (one object, the current session's latest reading):

```json
{
  "trade_date": "2026-09-02", "underlying": "NSE_INDEX|Nifty 50",
  "ts": "2026-09-02 13:20:12", "regime": "Positive GEX (Stable)",
  "underlying_ltp": 23872.5,
  "net_gex_cr": 681814.0,            "// ₹ crore per 1 % move; Neutral inside ±100"
  "side_coverage": 0.96,             "// share of contracts whose dealer side was inferred"
  "side_reliable": true,             "// false = theta drift, price test is measuring the clock"
  "zero_gamma_level": 22503.2,       "// gamma flip"
  "hhi": 0.056, "hhi_call": 0.079, "hhi_put": 0.088,   "// bands: ≥0.25 COMPRESSED, ≥0.10 BALANCED, else DISPERSED"
  "pin_strike": 23900.0, "runner_up": 24000.0,
  "pin_conviction": 49.0,            "// 0–100: ≥70 LOCKED, ≥30 CONTESTED, else DRIFTING"
  "pin_margin": 2.8,                 "// score points, lead over runner-up"
  "gex_at_pin_cr": -135118.0,
  "gamma_ceiling": 24000.0, "gamma_floor": 23800.0,   "// call-side / put-side gamma peaks"
  "call_wall": 24000.0, "put_wall": 23800.0,           "// max-OI strikes"
  "sigma_pts": 347.0,                "// ATM IV × √time-to-expiry, index points — the yardstick"
  "atm_iv": 11.15, "realized_vol": 6.86,
  "net_gamma_total": 1534624.6,      "// raw units, legacy"
  "gamma_by_strike": {"23700.0": 12.1, "23800.0": 40.2, "...": 0},   "// signed dealer gamma per strike, for the ladder chart"
  "hedge_ladder": [
    {"move_pct": -1.5, "flow_cr": 1022721.0, "side": "BUY"},
    {"move_pct": -1.0, "flow_cr": 681814.0,  "side": "BUY"},
    {"move_pct": -0.5, "flow_cr": 340907.0,  "side": "BUY"},
    {"move_pct":  0.5, "flow_cr": -340907.0, "side": "SELL"},
    {"move_pct":  1.0, "flow_cr": -681814.0, "side": "SELL"},
    {"move_pct":  1.5, "flow_cr": -1022721.0,"side": "SELL"}
  ],
  "oi_rotation": {
    "added": 6602180, "unwound": 4743830, "total_oi": 288938455, "vol_oi": 6.59,
    "by_strike": {"23800.0": {"ce": 120000, "pe": -80000}, "...": {}}
  }
}
```

`rows` (the farm list; zero to ~20 items): each has `screen`
(`premium_farm` | `imperfection` | `laggard`), `structure` (`iron_fly` |
`iv_asymmetry` | `vol_outlier` | `flip_cross` | `charm_cascade`), `strike`,
`option_type`, `score`, `credit`, `iv_minus_rv`, `pin_conviction`, `reason`, `expiry`,
and for iron flies `legs` (4 × `{side, option_type, strike, best_bid, best_ask, mid}`).

`GET /options/wall/api/regime?index=NIFTY&days=30` returns `{ river: [regime, …] }`,
one object per session, ascending, same shape as `regime`.

Also on the page: an index switch (NIFTY / BANKNIFTY), the snapshot spot and
timestamp, a "Scan now" button that triggers a background rescan, and a live
premium-farm **gate strip** — five conditions the scanner tests (regime contains
"Positive"; spot within ±0.5 % of pin; ATM IV − RV ≥ 2.0 pt; widest leg spread ≤ 5 %;
ATM credit > 0), each shown as reading vs threshold with pass / fail / unknown.

## What exists today (the page you are replacing)

The current template already renders every panel listed below in a plain
form: a 12-cell regime band, the gamma ladder, hedge ladder (six rungs), OI since
open (five tiles + diverging per-strike bars), the five-check gate strip, farm-list
cards, and the river chart + table. It works but reads as a grid of equal cells;
it does not yet make the reading order or the gates physical. Treat it as the
content inventory, not the layout.

## Panels to design

- **Header**: index tabs, spot, expiry + DTE, last-scan time, poll cadence, Scan now.
- **Board read** (steps 1–4 above): not a flat grid of 12 identical cells. Group by
  question. Every cell = label, value with unit, band word, one-line caveat. Distances
  in σ everywhere a strike appears. The side-coverage / theta-drift status belongs on
  the regime cell.
- **Gamma by strike**: bar ladder (positive teal, negative rust), overlays for spot,
  pin ± band, flip, ceiling / floor, OI walls; strike ticks. Sigma rulers (±1σ from
  spot) would help.
- **Hedge ladder**: six rungs, BUY right / SELL left, ₹ Cr labels, "look for the
  jump" annotation.
- **OI since open**: added / unwound / net / total / vol-OI tiles, then a per-strike
  diverging bar chart (calls vs puts) for ~21 strikes around spot.
- **Premium farm gate**: the five checks, plus verdict chip.
- **Farm list**: cards or dense rows, filter by screen, sort by score / strike / screen,
  click → slide-over (artboard 3) with headline stats, 4-leg quote table for flies,
  "conditions this row passed", positioning context, provenance, caveats.
- **Regime river**: 30 sessions; a band from put wall to call wall, pin and flip as
  lines, negative-gamma sessions shaded; a table with date, regime, net GEX ₹Cr, pin,
  conviction, HHI, flip, walls, ATM IV, RV; "show all / show latest 8" toggle.
- **Empty and degraded states**: no persisted regime yet; a screen with zero rows
  ("check the gate strip for the condition that closed first"); Neutral regime;
  DISPERSED book; `side_reliable=false`; fewer than 2 river sessions.

## House style (must match the rest of the app)

Light, paper-like, editorial. Off-white ground (#FBFAF8 panels on #FFFFFF cards),
hairline borders (`--line #E6E2DC`, `--hairline #F0EDE7`), ink `#14181F`, body
`#4C525C`, muted `#6E7480`, faint `#8A8578`. Accents: green `#197A5A` (positive /
pass), rust `#B4472F` (negative / fail), amber `#C9821A` (flip, warnings), teal
`#0E6F63` (pin). Type: **Instrument Serif** for display headings (the page opens with a
serif headline that states the regime in a sentence), **Public Sans** for UI text,
**IBM Plex Mono** with tabular numerals for every number. 15 px card radius, 999 px
chips, restrained motion (cards rise in on load, slide-over from the right). No dark
mode. No gradients, no glassmorphism, no charting library look — the existing charts
are hand-drawn SVG.

## Constraints for the hand-back

- The design is ported into a single Jinja template (`flask_app/templates/options_wall/index.html`)
  that extends a base layout with a left sidebar; inline styles and a small `<style>`
  block, vanilla JS, no framework, no Tailwind classes beyond what the base already
  loads. Keep components simple enough to hand-code.
- Charts are inline SVG or plain divs. No external libraries.
- All numbers come from the payload above; the page never computes analytics itself.
- Keep the existing element ids where sensible (`regime-band`, `ladder-wrap`,
  `gate-strip`, `farm-rows`, `river-chart-wrap`, `river-body`, `ow-panel`) so the JS
  can be adapted rather than rewritten.
- Use ₹ crore formatting as `+6.82L Cr`, `−135K Cr`, `+72 Cr`; sigma as `+0.83σ`;
  percentages with one decimal; strikes with no decimals.
- Copy tone: plain, declarative, one caveat per panel. "Discovery only — the scanner
  does not size or route" stays somewhere visible.
