# CB-N50 TRAIN Report — Signal Construction & Validation
Generated: 2026-08-01

**Window:** 2016-01-01 to 2019-12-31
**Trading days:** 986
**IC observations:** 983

## Feature Lookback Selection (Bonferroni m=9)

| Feature | L | Mean IC | NW t | p_raw | Significant? |
|---------|---|---------|------|-------|-------------|
| momentum | 5 | -0.040661 | -7.15 | 0.000000 | YES |
| momentum | 10 | -0.028082 | -4.77 | 0.000002 | YES |
| momentum | 20 | -0.020718 | -3.48 | 0.000520 | YES |
| reversal | 1 | 0.045875 | 8.42 | 0.000000 | YES |
| basis | 1 | 0.055679 | 12.13 | 0.000000 | YES |

**Best momentum lookback: L=20**

## Feature Sign Check

- momentum: IC=-0.020718 (WRONG SIGN — dropped)
- reversal: IC=0.045875 (OK)
- basis: IC=0.055679 (OK)

Dropped: momentum
Active: reversal, basis

## Combined Signal (retained features)

- Mean IC: 0.058674
- IC Std: 0.167917
- AC1: -0.0627
- NW Mean: 0.058674
- NW SE: 0.005166
- NW t-statistic: 11.3583
- p-value (raw): 0.000000
- Bonferroni alpha: 0.005556 (m=9)
- **Significant: YES**

**G1 Gate (IC significance): PASS**
**G2 Gate (features with correct sign): PASS**

## Breadth Threshold Verification

- Breadth mean: 0.5397
- LONG days: 48 (4.9%), mean Nifty next-day return: -2.4 bps
- SHORT days: 2 (0.2%), mean Nifty return: 49.4 bps
- FLAT days: 935 (94.9%), mean Nifty return: 5.1 bps
- Directional: FAIL (LONG > SHORT: -2.4 > 49.4 bps)
