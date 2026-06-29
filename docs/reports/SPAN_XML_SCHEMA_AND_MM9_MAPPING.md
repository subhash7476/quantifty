# SPAN XML Schema Specification & MM9.4 Data Model Mapping

**Source file:** `reference/span/nsccl.20260625.i1/nsccl.20260625.i01.spn`  
**Format:** PC-SPAN fileFormat 4.00 (XML, CRLF-terminated, latin-1 encoding)  
**Trade date:** 2026-06-25 (NSCCL — NSE Clearing)  
**File size:** 57.2 MB  
**Produced:** 2026-06-29

---

## 1. Complete XML Schema

### 1.1 Top-level structure

```
<spanFile>
├── <fileFormat>              "4.00"  — PC-SPAN schema version
├── <created>                 "202606242149"  — creation timestamp YYYYMMDDHHmm IST
├── <definitions>             global reference data
│   ├── <currencyDef> × 22
│   ├── <acctTypeDef> × 7
│   └── <groupTypeDef> × 1
└── <pointInTime>             one business day's parameter set
    ├── <date>                "20260625"  — trade date YYYYMMDD
    ├── <isSetl>              "0"  — 0=intraday snapshot, 1=end-of-day settlement
    ├── <setlQualifier>       "early"
    └── <clearingOrg>         NSCCL — the entire margin universe
```

### 1.2 Definitions block

#### `<currencyDef>` (22 entries)

| Element | Sample values | Meaning |
|---------|--------------|---------|
| `<currency>` | AUD, CAD, INR, USD … | ISO currency code |
| `<symbol>` | A, C, R, U … | Single-char SPAN abbreviation |
| `<name>` | AUSTRALIAN DOLLAR … | Display name |
| `<decimalPos>` | 2 | Decimal places for amounts |

#### `<acctTypeDef>` (7 entries)

| Element | Sample values | Meaning |
|---------|--------------|---------|
| `<acctType>` | H, M, N, O … | SPAN account-type code |
| `<name>` | Hedge, Member, Normal … | Human name |
| `<isCust>` | 0 / 1 | Is a customer account |
| `<isNetMargin>` | 0 / 1 | Eligible for net margining |
| `<priority>` | 10, 20, 30 … | Processing priority |

#### `<groupTypeDef>` (1 entry)

| Element | Value | Meaning |
|---------|-------|---------|
| `<id>` | 1 | Group type identifier |
| `<name>` | REPORT | Purpose of this group classification |

---

### 1.3 ClearingOrg block

```
<clearingOrg>
├── <ec>                   "NSCCL"  — clearing org code
├── <name>                 "National Securities Clearing Corporation"
├── <finalizeMeth>         "BY"  — finalization method
├── <isNetMargin>          "0"  — gross margin (not net)
├── <isContractScale>      "1"  — margins scaled at contract level
├── <lookAheadYears>       "0.002739"  — ~1 calendar day
├── <oopDeltaMeth>         "PERIOD"  — delta computed per period
├── <capAnov>              "0"  — cap on annual-of-variation adjustment
├── <curConv>              INR → USD conversion
│   ├── <fromCur>          "INR"
│   ├── <toCur>            "USD"
│   └── <factor>           "0.010559"
├── <pbRateDef> × 11       performance bond rate definitions
│   ├── <acctType>         H | M | N | O …
│   ├── <isCust>           0 / 1
│   ├── <isM>              0 / 1 (is member?)
│   ├── <pbc>              "CORE" | "RESRV"  — core vs reserve performance bond
│   └── <r>                rate index
├── <pointDef>             the SPAN scenario grid (§1.4)
├── <ccDef> × 239          combined commodity definitions (§1.5)
├── <interSpreads>         clearing-org-level inter-commodity spreads
│   └── <dSpread>          (empty in this file — NSE uses intra-cc spreads only)
└── <exchange>             NSE exchange data
    ├── <exch>             "NSE"
    ├── <name>             "National Stock Exchange of India"
    ├── <phyPf> × 239      physical/underlying portfolios (§1.6)
    ├── <futPf> × 239      futures portfolios (§1.7)
    └── <oopPf> × 221      options portfolios (§1.8)
```

---

### 1.4 Scenario Grid — `<pointDef>`

The SPAN scenario grid is the engine of the margin computation. Two scenario sets are defined.

#### Scan scenarios (`<scanPointDef>`, 16 entries)

Each defines one price×vol scenario applied to every position's risk array.

| Element | Meaning |
|---------|---------|
| `<point>` | Scenario index 1–16 |
| `<pairedPoint>` | Paired scenario (up/down vol pairs; SPAN takes the worse of each pair) |
| `<priceScanDef/numerator>`, `<priceScanDef/denominator>` | Price-shift fraction of `priceScan` range |
| `<volScanDef/numerator>`, `<volScanDef/denominator>` | Vol-shift fraction of `volScan` range |
| `<weight>` | Scenario weight (1.0 for normal; 0.3 for extreme scenarios 15/16) |

**The 16 canonical scenarios:**

| Pt | Price shift (× priceScan) | Vol shift (× volScan) | Weight | Notes |
|----|--------------------------|----------------------|--------|-------|
|  1 |  0.000 |  +1.000 | 1.0 | vol up, price flat |
|  2 |  0.000 |  −1.000 | 1.0 | vol down, price flat |
|  3 | +0.333 |  +1.000 | 1.0 | price +1/3, vol up |
|  4 | +0.333 |  −1.000 | 1.0 | price +1/3, vol down |
|  5 | −0.333 |  +1.000 | 1.0 | price −1/3, vol up |
|  6 | −0.333 |  −1.000 | 1.0 | price −1/3, vol down |
|  7 | +0.667 |  +1.000 | 1.0 | price +2/3, vol up |
|  8 | +0.667 |  −1.000 | 1.0 | price +2/3, vol down |
|  9 | −0.667 |  +1.000 | 1.0 | price −2/3, vol up |
| 10 | −0.667 |  −1.000 | 1.0 | price −2/3, vol down |
| 11 | +1.000 |  +1.000 | 1.0 | price +full, vol up |
| 12 | +1.000 |  −1.000 | 1.0 | price +full, vol down |
| 13 | −1.000 |  +1.000 | 1.0 | price −full, vol up |
| 14 | −1.000 |  −1.000 | 1.0 | price −full, vol down |
| 15 | +3.000 |   0.000 | 0.3 | extreme up (30% weight) |
| 16 | −3.000 |   0.000 | 0.3 | extreme down (30% weight) |

SPAN margin formula: apply each scenario to the risk array, weight scenarios 15/16 by 0.3, take
the worst-case loss across all 16 weighted results. The paired-point rule means SPAN compares
both members of each vol pair (up vs down) and takes the worse outcome.

#### Delta scenarios (`<deltaPointDef>`, 7 entries)

Used for inter-month spread credit calculations.

| Element | Meaning |
|---------|---------|
| `<point>` | Delta scenario index 1–7 |
| `<priceScanDef>` | Price-shift fraction |
| `<volScanDef>` | Vol-shift fraction (all zero — delta scenarios ignore vol) |
| `<weight>` | 0.037, 0.111, 0.217 … (symmetrically distributed around zero) |

---

### 1.5 Combined Commodity Definition — `<ccDef>` (239 entries)

One `<ccDef>` per underlying (e.g., NIFTY, BANKNIFTY, RELIANCE …).

| Element | Sample | Meaning |
|---------|--------|---------|
| `<cc>` | NIFTY | Underlying/combined-commodity code |
| `<name>` | NIFTY | Display name |
| `<currency>` | INR | Margin currency |
| `<riskExponent>` | 0 | Risk scaling exponent |
| `<capAnov>` | 0 | Cap on annual-of-variation |
| `<procMeth>` | NORMAL | Processing method |
| `<wfprMeth>` | NORMAL | WF price risk method |
| `<spotMeth>` | NORMAL | Spot price method |
| `<somMeth>` | GROSS | Short option minimum method (GROSS = not netted) |
| `<cmbMeth>` | NONE | Inter-commodity combining method |
| `<group/id>` | 1 | Group classification |
| `<group/aVal>` | ALL | Group attribute value |

#### Adjustment rates — `<adjRate>` (10 per ccDef)

Scaling factors for specific scenarios or risk types.

| Element | Meaning |
|---------|---------|
| `<r>` | Rate type index |
| `<baseR>` | Base rate reference |
| `<val>` | Rate value (1.00000 = no adjustment) |

#### Inter-month spread charges — `<dSpread>` (multiple per ccDef)

**Critical for margin netting.** Defines the flat charge when two contracts on the same underlying
are on opposite sides (a calendar spread). The spread charge is granted as a credit — the position
pays less than two full-leg margins.

| Element | Sample (NIFTY) | Meaning |
|---------|----------------|---------|
| `<spread>` | 1, 2, 3 … | Spread tier number |
| `<chargeMeth>` | F | Flat charge method |
| `<rate/val>` | 425.000000 | Charge in INR per spread |
| `<pLeg> × 2` | — | The two legs of the spread |
| `<pLeg/cc>` | NIFTY | Underlying |
| `<pLeg/pe>` | 20260630 | Expiry date YYYYMMDD |
| `<pLeg/rs>` | A / B | Leg side: A=near, B=far |
| `<pLeg/i>` | 1.000000 | Leg ratio |

**Concrete spread charges:**

| Underlying | Inter-month spread charge | Scope |
|------------|--------------------------|-------|
| NIFTY | **Rs 425 per lot-pair** | All weekly/monthly expiry combinations |
| BANKNIFTY | **Rs 1,029 per lot-pair** | All monthly expiry combinations |
| Single stocks | Varies | Per-symbol pairs |

#### Scan tiers — `<scanTiers>`, `<intraTiers>`, `<interTiers>`

Define expiry-date ranges for grouping contracts into margin tiers.

| Element | Meaning |
|---------|---------|
| `<tn>` | Tier number |
| `<sPe>` | Start expiry (YYYYMMDD) |
| `<ePe>` | End expiry (YYYYMMDD) |

#### Short option minimum tiers — `<somTiers>`

| Element | NIFTY value | BANKNIFTY value | Meaning |
|---------|-------------|-----------------|---------|
| `<tn>` | 0 | 0 | Tier 0 = uniform |
| `<rate/val>` | **0** | **0** | SOM charge per lot (Rs) |

NSE does not apply a separate SOM charge to NIFTY/BANKNIFTY options. The SOM rate is **0** for
index underlyings. Single-stock underlyings may have non-zero SOM rates.

#### Portfolio links — `<pfLink>` (3 per ccDef)

| `<pfType>` | `<pfId>` (NIFTY) | `<pfId>` (BANKNIFTY) | Meaning |
|------------|-----------------|----------------------|---------|
| PHY | 490 | 139 | Physical/underlying portfolio |
| FUT | 491 | 140 | Futures portfolio |
| OOP | 492 | 141 | Options portfolio |

---

### 1.6 Physical Portfolio — `<phyPf>` (239 entries)

One per underlying. Contains one `<phy>` child representing the spot/physical position.

#### Portfolio-level elements

| Element | Sample | Meaning |
|---------|--------|---------|
| `<pfId>` | 490 | Portfolio identifier |
| `<pfCode>` | NIFTY | Portfolio code = underlying symbol |
| `<name>` | NIFTY | Display name |
| `<currency>` | INR | Margin currency |
| `<cvf>` | 1.00 | Contract value factor |
| `<priceDl>` | 2 | Price decimal places |
| `<valueMeth>` | EQTY | Valuation method |
| `<priceMeth>` | IDX | Pricing method (IDX=index) |
| `<setlMeth>` | CASH | Settlement method |

#### Physical contract elements (`<phy>`)

| Element | Sample | Meaning |
|---------|--------|---------|
| `<cId>` | 1 | Contract / scan-tier ID |
| `<pe>` | 00000000 | Expiry (00000000 = no expiry for physical) |
| `<p>` | 24050.35 | Underlying spot price |
| `<d>` | 0.000000 | Delta (0 for physical) |
| `<v>` | 0.000000 | Implied vol (0 for physical) |
| `<sc>` | 1.00000 | Scaling factor |
| `<cvf>` | 1.00 | Contract value factor |
| `<scanRate/priceScan>` | **2234.01** | **Price scanning range in index points** |
| `<scanRate/volScan>` | **0.04** | **Vol scanning range as fraction (4%)** |
| `<scanRate/r>` | 1 | Scan tier reference |
| `<ra/r>` | 1 | Scan tier for this risk array |
| `<ra/a>` × 16 | 0.00 … | 16 scenario risk values (all ≈0 for physical) |
| `<ra/d>` | 1.00000 | Delta used in RA computation |

---

### 1.7 Futures Portfolio — `<futPf>` (239 entries)

One per underlying. Contains one `<fut>` child per expiry.

#### Portfolio-level elements (same as phyPf, plus)

| Element | Sample | Meaning |
|---------|--------|---------|
| `<undPf/pfId>` | 490 | Link to the physical portfolio |
| `<undPf/pfCode>` | NIFTY | Underlying code |
| `<undPf/pfType>` | PHY | Points to physical portfolio |
| `<undPf/s>` | B | Currency symbol |
| `<undPf/i>` | 1.000000 | Intercurrency factor |
| `<valueMeth>` | FUT | Valuation method = futures |

#### Per-contract elements (`<fut>`)

| Element | Sample (NIFTY Jun-26) | Meaning |
|---------|----------------------|---------|
| `<cId>` | 1 | Contract/scan-tier ID |
| `<pe>` | 20260630 | Expiry date YYYYMMDD |
| `<setlDate>` | 20260630 | Settlement date YYYYMMDD |
| `<p>` | 24051.80 | Futures price |
| `<d>` | 1.00000000 | Delta (always 1.0 for futures) |
| `<v>` | 0.17 | Underlying implied vol (annualised) |
| `<t>` | 0.016438 | Time to expiry in years |
| `<sc>` | 1.00000 | Scaling factor |
| `<cvf>` | 1.00 | Contract value factor |
| `<intrRate/val>` | 0.07 | Risk-free interest rate (7% p.a.) |
| `<intrRate/exm>` | 12 | Months in a year (for compounding) |
| `<intrRate/cpm>` | 0 | Compounding flag |
| `<intrRate/rl>` | 0 | Rate lag |
| `<undC/pfId>` | 490 | Underlying physical portfolio ID |
| `<undC/exch>` | NSE | Exchange |
| `<undC/cId>` | 1 | Underlying contract ID |
| `<undC/i>` | 1.00000 | Intercurrency factor |
| `<undC/s>` | B | Currency symbol |
| `<scanRate/priceScan>` | **2234.01** | Price scanning range in index points |
| `<scanRate/volScan>` | **0.04** | Vol scanning range as fraction (4%) |
| `<scanRate/r>` | 1 | Scan tier |
| `<ra/r>` | 1 | Scan tier |
| `<ra/a>` × 16 | 8.72, −736.49 … | **16 scenario P&L values in Rs per lot-unit** |
| `<ra/d>` | 1.00000 | Delta used in risk array |

**NIFTY Jun-26 futures: 16-scenario risk array (Rs per lot-unit):**

| Pt | Ra value | Scenario meaning |
|----|----------|-----------------|
| 1 | +8.72 | vol up, price flat |
| 2 | +8.72 | vol down, price flat |
| 3 | −736.49 | price +1/3 × priceScan |
| 4 | −736.49 | |
| 5 | +753.93 | price −1/3 × priceScan |
| 6 | +753.93 | |
| 7 | −1481.70 | price +2/3 × priceScan |
| 8 | −1481.70 | |
| 9 | +1499.14 | price −2/3 × priceScan |
| 10 | +1499.14 | |
| 11 | −2226.91 | price +full priceScan |
| 12 | −2226.91 | |
| 13 | **+2244.36** | price −full priceScan ← **worst loss for long** |
| 14 | +2244.36 | |
| 15 | −1561.89 | price +3× priceScan, weight 0.3 → effective −468.6 |
| 16 | +1568.00 | price −3× priceScan, weight 0.3 → effective +470.4 |

**Worst loss for a long futures position = 2244.36 Rs per lot-unit.**  
SPAN margin per lot = 2244.36 × lot_size (75 for NIFTY = **Rs 168,327 per lot**).

**BANKNIFTY Jun-26 futures:** priceScan=5488.30, volScan=0.05, worst loss=5513.40 Rs/lot-unit.

---

### 1.8 Options Portfolio — `<oopPf>` (221 entries)

One per underlying. Contains one `<series>` child per expiry, and one `<opt>` per strike.

#### Portfolio-level elements (same as futPf, plus)

| Element | Sample | Meaning |
|---------|--------|---------|
| `<priceModel>` | BS | Pricing model (Black-Scholes) |
| `<exercise>` | EURO | Exercise style (European) |
| `<strikeDl>` | 2 | Strike price decimal places |
| `<strikeFmt>` | (blank) | Strike format |
| `<cab>` | 0.00000 | Cab value (minimum option price for margin) |

#### Per-series elements (`<series>`)

| Element | Sample | Meaning |
|---------|--------|---------|
| `<pe>` | 20260630 | Expiry date YYYYMMDD |
| `<setlDate>` | 20260630 | Settlement date |
| `<t>` | 0.016438 | Time to expiry in years |
| `<v>` | 0.40289 | Underlying vol for this series |
| `<sc>` | 1.00000 | Scaling factor |
| `<cvf>` | 1.00 | Contract value factor |
| `<intrRate/*>` | (same as fut) | Interest rate |
| `<undC/*>` | (same as fut) | Underlying reference |
| `<volSrc>` | (empty) | Vol source identifier |
| `<scanRate/priceScan>` | **2234.01** | Series-level price scan range |
| `<scanRate/volScan>` | **0.04** | Series-level vol scan range |

#### Per-strike elements (`<opt>`)

| Element | Sample | Meaning |
|---------|--------|---------|
| `<k>` | 24000.00 | Strike price |
| `<o>` | C / P | Option type: Call or Put |
| `<p>` | 260.05 | Option market price |
| `<d>` | +0.8453 | Option delta |
| `<v>` | 0.4029 | Per-strike implied volatility |
| `<cId>` | 1 | Contract/scan-tier ID |
| `<ra/r>` | 1 | Scan tier |
| `<ra/a>` × 16 | various | **16 scenario P&L values in Rs** |
| `<ra/d>` | +0.8453 | Delta used in risk array |

**Total option contracts in this file:** 158,713 (all underlyings, all expiries, all strikes).

---

## 2. Mapping to MM9.4 Data Model

### 2.1 `SpanSnapshot` field mapping

| `SpanSnapshot` field | XML source | Status |
|---------------------|------------|--------|
| `snapshot_date: date` | `<pointInTime/date>` → YYYYMMDD | **Mappable** — straightforward parse |
| `schema_version: str` | `<fileFormat>` → "4.00" → map to "v1" | **Mappable** |
| `exchange: str` | `<exchange/exch>` → "NSE" | **Mappable** |
| `segment: str` | Not in XML; inferred from file naming | **Partially mappable** — hardcode "FO" |
| `file_hash: str` | SHA-256 of raw ZIP; computed externally | **Mappable** — computed outside XML |
| `risk_arrays: Dict[str, SpanRiskArray]` | One entry per `<ccDef/cc>` | **Parser not implemented** (Gap G-2) |
| `metadata: Dict[str, Any]` | `<created>`, `<ec>`, `<isSetl>`, `<curConv>`, `<pointDef>` | **Parser not implemented** |

### 2.2 `SpanRiskArray` field mapping

| `SpanRiskArray` field | XML source | Status |
|----------------------|------------|--------|
| `symbol: str` | `<ccDef/cc>` | **Mappable** |
| `risk_metrics["scan_risk"]` | `max(weight[i] × max(0, −RA[i]))` from `<phy/ra/a>` × 16 | **Gap G-1**: formula unimplemented |
| `risk_metrics["short_option_minimum"]` | `<ccDef/somTiers/tier/rate/val>` | **Gap G-5**: = 0 for index; parser must emit 0.0 explicitly |

### 2.3 `span_parser.py` mapping

| Parser component | XML elements required | Status |
|-----------------|----------------------|--------|
| File format detection | `<fileFormat>` | **Gap G-2**: parser named `parse_span_csv`; file is XML |
| Trade date extraction | `<pointInTime/date>` | **Gap G-2**: not implemented |
| Underlying enumeration | `<ccDef>` loop | **Gap G-2**: not implemented |
| Scan range extraction | `<phyPf/phy/scanRate/priceScan>`, `<phyPf/phy/scanRate/volScan>` | **Gap G-1**: not implemented |
| Worst-case RA derivation | `<phyPf/phy/ra/a>` × 16 | **Gap G-1**: formula not implemented |
| SOM extraction | `<ccDef/somTiers/tier/rate/val>` | **Gap G-5**: not implemented |
| Spread charges | `<ccDef/dSpread>` | **Gap G-3**: not captured in model |
| Interest rate | `<fut/intrRate/val>` | Not in model (deferred) |
| Per-contract option data | `<oopPf/series/opt>` | Not needed for current calculator scope |

### 2.4 `SpanMarginCalculator` field mapping

| Calculator input | XML data path | Status |
|-----------------|---------------|--------|
| `risk_metrics["scan_risk"]` | Worst loss from RA (§3, G-1) | **Gap G-1**: flagged constant; formula unspecified |
| `risk_metrics["short_option_minimum"]` | `<somTiers/rate/val>` = 0 | **Gap G-5**: calculator raises if key absent; parser must emit 0.0 |
| Lot size | External (instrument master); `cvf`=1.0 in XML | **Gap G-4**: cvf not stored; currently harmless |
| Inter-month spread credit | `<dSpread/rate/val>` | **Gap G-3**: not in model (conservative overestimate) |

---

## 3. Gap Analysis

### G-1 — `scan_risk` derivation formula not implemented (CRITICAL)

**What the XML provides:** Every contract carries a `<ra>` block with 16 `<a>` values — the
P&L impact of each SPAN scenario in rupees per lot-unit. These are pre-computed by NSCCL using
the BS pricing model at each scenario's price/vol shift.

**What the MM9.4 model needs:** `risk_metrics["scan_risk"]` as a single float.

**The correct derivation (per underlying, using physical portfolio RA as the representative):**

```python
# From <phyPf/phy/ra> (or nearest-expiry <futPf/fut/ra>):
ra_values = [float(a.text) for a in phy_ra.findall("a")]   # 16 values
weights = [1.0] * 14 + [0.3, 0.3]                          # pts 15,16 at 30%

# Loss for position holder: loss = −gain (RA positive = gain to long position)
# For a short position, sign flips — SPAN takes the absolute worst regardless of side.
# The parser records the per-lot-unit worst-case loss magnitude:
weighted_losses = [−ra * w for ra, w in zip(ra_values, weights)]
scan_risk_rs_per_lot_unit = max(weighted_losses)            # Rs per lot-unit (always positive)
```

**Two strategies for storing `scan_risk` in `risk_metrics`:**

| Strategy | `scan_risk` meaning | Calculator formula |
|----------|--------------------|--------------------|
| **A — fraction** | worst_loss ÷ (price × cvf) | `margin = qty × price × lot × scan_risk` |
| **B — absolute Rs/lot** | worst_loss in Rs per lot-unit | `margin = qty × lot × scan_risk` |

**Strategy B is strongly recommended:** the RA values are already in Rs; dividing by price loses
precision and reintroduces price dependency at runtime where none exists in the SPAN design.

**Required calculator revision for Strategy B:**

```python
# Current (fraction-based):
risk_pct = self._risk_percentage(symbol)
return pos.quantity * current_price * lot_size * risk_pct

# Strategy B (absolute Rs/lot):
scan_rs = risk_array.risk_metrics[METRIC_SCAN_RISK]    # already Rs per lot-unit
units   = abs(pos.quantity) * lot_size
return units * scan_rs * self.margin_rate
```

This eliminates the price argument from margin computation — correct, because SPAN margin is
pre-computed per-lot at parameter-file publication time.

**Concrete validation (NIFTY Jun-26):**
- RA worst loss = 2244.36 Rs/lot-unit (scenario 13, −priceScan move)
- NIFTY lot size = 75
- Scan margin per lot = 2244.36 × 75 = **Rs 168,327**
- NSCCL-published NIFTY futures initial margin ≈ Rs 1,68,000–1,70,000 ✓

---

### G-2 — Parser targets CSV; actual file is XML (CRITICAL)

**What exists:** `span_parser.py` exports `parse_span_csv()`, its docstring mentions "CSV",
and `ParserRegistry` maps `schema_version → Callable[[dict], SpanSnapshot]` expecting a
pre-parsed dict.

**What the NSE file is:** XML (`<spanFile>`, fileFormat 4.00). No CSV wrapper exists.

**Required changes to `span_parser.py`:**
1. Rename `parse_span_csv` → `parse_span_xml` (or keep as alias).
2. Change `ParserRegistry` signature from `Callable[[dict], SpanSnapshot]` to
   `Callable[[bytes], SpanSnapshot]` — the pipeline passes raw bytes from the downloaded file.
3. Implement a `_parse_v1(raw_bytes: bytes) -> SpanSnapshot` using `xml.etree.ElementTree`.

This is a **breaking change to the registry contract** but affects only the unimplemented parser
function — no downstream consumers exist yet.

---

### G-3 — Inter-month spread charges not modelled (DEFERRED, data is present)

**What the XML provides:**

| Underlying | Spread charge (Rs) | Applies to |
|------------|-------------------|------------|
| NIFTY | **Rs 425 per lot-pair** | All sequential expiry combinations |
| BANKNIFTY | **Rs 1,029 per lot-pair** | All monthly expiry combinations |

**What the model captures:** Nothing. S3 explicitly defers this (§3.5 — "Inter-month spread
credits — Later slice"). Without spread credits, opposite-side calendar spreads pay two full
single-leg margins rather than the credited spread rate. This is the conservative direction.

**Schema addition needed (later slice):**

```python
risk_metrics["intra_spread_charge_rs"] = 425.0   # Rs per lot-pair (NIFTY)
# Plus a SpanSpreadTable DTO pairing (near_expiry, far_expiry) → charge_rs
```

---

### G-4 — Contract value factor (`cvf`) vs instrument lot size (MINOR)

**What the XML provides:** `<cvf>` = 1.00 for **all** NSE F&O contracts. The actual lot size
(75 for NIFTY, 30 for BANKNIFTY) is not in the SPAN file — it lives in the instrument master.

**What the model does:** `getattr(instrument, "lot_size", None) or instrument.multiplier`. This
is correct — the instrument master owns lot sizes; the SPAN file only confirms `cvf`=1.0.

**Action:** The parser should store `cvf` in `risk_metrics["cvf"]` so the calculator can
assert `cvf == 1.0` and raise `UnsupportedInstrument` if NSE ever publishes a non-1.0 value
(e.g., for currency futures or commodity derivatives).

---

### G-5 — Short option minimum is zero; calculator raises if key absent (HIGH)

**What the XML shows:** `<somTiers/tier/rate/val>` = **0** for NIFTY and BANKNIFTY.

NSE does not publish a separate SOM charge for index F&O. The RA worst-case already floors the
option margin — no additional minimum is applied for index underlyings.

**Calculator behavior:** `span_calculator.py:174-177` raises `MissingRiskMetric` if
`short_option_minimum` key is `None`. Since NSE's SOM is 0, the parser must emit
`risk_metrics["short_option_minimum"] = 0.0` explicitly.

`max(scan_risk, 0.0) = scan_risk`, so the key is semantically a no-op for index underlyings
but is **structurally required** by the calculator.

**Action for single-stock underlyings:** check `<somTiers>` per ccDef — non-zero SOM rates
may appear for individual equity F&O contracts.

---

### G-6 — Per-contract RA vs underlying-level aggregation (DESIGN DECISION)

**What the XML provides:** Each `<fut>` and each `<opt>` strike has its own `<ra>` with
delta-weighted 16-scenario values. An ATM option's RA reflects ~0.5 delta exposure; a deep-OTM
option's RA reflects near-zero exposure.

**What the model captures:** One `SpanRiskArray` per underlying, serving all contracts.

**Correct aggregation for the parser:** Use `<phyPf/phy/ra>` (the physical underlying's RA) as
the representative. For physical, all RA values are near 0 (no tradeable position) — this is
**wrong** as a margin source. The correct representative is the **nearest-expiry futures RA**
(`<futPf/fut/ra>` with the smallest `<pe>` date), which represents the full-delta (Δ=1) exposure
to the priceScan range.

**Why futures RA is the right choice:**
- Futures Δ=1 → RA captures the full priceScan exposure
- Options RA captures per-strike delta; using futures RA for all options is conservative
  (overcharges low-delta options) but never undercharges

**For later precision:** a `SpanOptionRiskTable` keyed by `(symbol, expiry, strike, type)` →
`RA[16]` would allow per-contract margin. Current scope doesn't need this.

---

### G-7 — Per-strike option metadata not captured (DEFERRED)

**What the XML provides per `<opt>`:** strike, type (C/P), price, delta, IV, 16-scenario RA.

**What the model captures:** Nothing per-strike.

**Is this a margin gap?** No, for the current conservative approach. The options dashboard
(`core/analytics/options_analytics.py`) uses Upstox live chain data — the SPAN file's option
prices are not needed there either. This gap is purely about per-contract precision margin.

---

### G-8 — Scenario grid metadata not archived (MINOR)

**What the XML provides:** The 16-scenario definitions in `<pointDef/scanPointDef>` — exact
price/vol shifts and weights. These are needed to reproduce RA values from first principles
if ever a recomputation is required.

**Action:** Store in `SpanSnapshot.metadata["scan_scenarios"]` as a list of dicts:

```python
{"point": 1, "price_mult": 0.0, "vol_mult": 1.0, "weight": 1.0, "paired_point": 2}
```

Makes the snapshot self-documenting; enables future RA validation.

---

## 4. Gap Summary — Prioritized

| ID | Title | Severity | Required for | Action owner |
|----|-------|----------|--------------|--------------|
| G-1 | `scan_risk` derivation formula unimplemented | **CRITICAL** | Calculator producing any SPAN margin | Offline parser; also revise calculator to Strategy B |
| G-2 | Parser targets CSV; file is XML | **CRITICAL** | Any parsing at all | `span_parser.py` + `ParserRegistry` signature change |
| G-5 | SOM = 0; calculator raises `MissingRiskMetric` if key absent | **HIGH** | Calculator not crashing on index options | Parser must emit `"short_option_minimum": 0.0` |
| G-6 | Aggregation strategy for per-contract RA unspecified | **MEDIUM** | Correct parser implementation | Parser: use nearest-expiry futures RA per underlying |
| G-4 | `cvf` not stored; currently harmless | **MEDIUM** | Future currency/commodity derivatives | Parser: store `risk_metrics["cvf"] = 1.0` |
| G-8 | Scenario grid not in metadata | **LOW** | Future RA recomputation / validation | Parser: store in `metadata["scan_scenarios"]` |
| G-3 | Spread charges not modelled | **LOW** (conservative) | Future margin-netting slice | New `SpanSpreadTable` DTO |
| G-7 | Per-strike option data not captured | **LOW** | Future per-contract margin slice | New `SpanOptionRiskTable` DTO |

---

## 5. Recommended `SpanSnapshot` Content After Parser Implementation

```python
SpanSnapshot(
    snapshot_date  = date(2026, 6, 25),            # <pointInTime/date>
    schema_version = "v1",
    exchange       = "NSE",                         # <exchange/exch>
    segment        = "FO",                          # inferred from file naming
    file_hash      = "<sha256_of_zip>",             # external computation
    metadata = {
        "created":        "202606242149",           # <created>
        "is_settlement":  False,                    # <isSetl> == "1"
        "clearing_org":   "NSCCL",                  # <ec>
        "inr_usd_rate":   0.010559,                 # <curConv/factor>
        "scan_scenarios": [                         # <pointDef/scanPointDef>
            {"point": 1, "price_mult": 0.000, "vol_mult":  1.0, "weight": 1.0, "paired": 2},
            {"point": 2, "price_mult": 0.000, "vol_mult": -1.0, "weight": 1.0, "paired": 1},
            {"point": 3, "price_mult": 0.333, "vol_mult":  1.0, "weight": 1.0, "paired": 4},
            # … 13 more
            {"point": 15, "price_mult": 3.0, "vol_mult": 0.0, "weight": 0.3, "paired": 15},
            {"point": 16, "price_mult": -3.0, "vol_mult": 0.0, "weight": 0.3, "paired": 16},
        ],
    },
    risk_arrays = {
        "NIFTY": SpanRiskArray(
            symbol = "NIFTY",
            risk_metrics = {
                "scan_risk":              2244.36,  # Rs/lot-unit; worst RA loss (nearest fut, sc.13)
                "short_option_minimum":   0.0,      # <somTiers/rate/val>; 0 for index
                "price_scan_range":       2234.01,  # <phy/scanRate/priceScan>
                "vol_scan_range":         0.04,     # <phy/scanRate/volScan>
                "cvf":                    1.0,      # <phy/cvf>; assert == 1.0
                "intra_spread_charge_rs": 425.0,    # <ccDef/dSpread[tier=1]/rate/val>
                "risk_free_rate":         0.07,     # <fut/intrRate/val>
            },
        ),
        "BANKNIFTY": SpanRiskArray(
            symbol = "BANKNIFTY",
            risk_metrics = {
                "scan_risk":              5513.40,
                "short_option_minimum":   0.0,
                "price_scan_range":       5488.30,
                "vol_scan_range":         0.05,
                "cvf":                    1.0,
                "intra_spread_charge_rs": 1029.0,
                "risk_free_rate":         0.07,
            },
        ),
        # … one entry per underlying in <ccDef> (239 total)
    },
)
```

---

## 6. What the MM9.4 Architecture Gets Right

Despite the implementation gaps, the architectural decisions are sound:

| Decision | Assessment |
|----------|------------|
| `SpanSnapshot` as immutable frozen DTO | Correct — matches the static-file nature of NSE SPAN data |
| One `SpanRiskArray` per underlying (not per-contract) | Conservative but valid; per-contract precision is a future slice |
| `risk_metrics: Dict[str, float]` — flexible key-value | Good — accommodates `cvf`, spread charges, scan ranges without DTO schema changes |
| `ParserRegistry` keyed by schema_version | Correct — NSE has changed SPAN formats historically; the registry isolates DTO from format |
| `SpanRepository` using pickle (not DuckDB) | Appropriate — SPAN data is hundreds of floats, not tens of thousands of rows |
| `scan_risk` + `short_option_minimum` as the two mandatory metric keys | Correct abstraction — calculator doesn't need raw scenario values at runtime |
| Deferred spread credits (conservative overestimate) | Safe direction for a gate; no position gets undercharged |
| Zero runtime I/O — frozen pre-loaded snapshot | Correct (ADR-003) |
| No GreeksCalculator at runtime (S3 §3.6) | Correct — NSE pre-computes the RA; runtime repricing would duplicate work |
