# M4a — Compression → Expansion: Non-Confirmatory Characterization Report

**Protocol:** `M4A_COMPRESSION_EXPANSION_PROTOCOL.md` v1.0 (frozen before any outcome; one logged amendment, A1, to the
verifier only). **Log:** `M4A_COMPRESSION_EXPANSION_RESEARCH_LOG.md`. **Branch:** `research/m4a-compression-expansion`
(worktree `F:\Nifty_m4a`). **Status:** GR-1.4 non-confirmatory characterization — TRAIN 2012-01-02 → 2017-12-29 and
VAL 2018-01-01 → 2022-12-30 are signal-spent windows (GR-1.3); **nothing below is a confirmation, no HOLDOUT was read (none
exists in this package), no strategy was built, the Vault mechanism map and closure ledger were not modified.**
Every table is script-generated from `data/research/m4a_compress/results/` (copied to `docs/reports/research/m4a_compress/`).

---

## 1. Answer

**On the pre-registered contrast, M4a shows no support — and every cell, stage, horizon and year points the other way.**
A low trailing ATR10/ATR60 state (bottom 20 % of its own 252-session history, onset only) is followed by a *smaller*
normalised forward range than the normal-state complement and than the high-dispersion state. All four primary cells are
wrong-signed in VAL (one-sided p ≈ 1, Holm p = 1), all four are wrong-signed in TRAIN, all 44 year-by-cell values in TRAIN and
VAL are negative, and the block-bootstrap 95 % interval excludes zero on the negative side in every cell. The minimum
detectable effect in VAL is 0.036–0.059 (units of the name's own baseline), so a positive effect of that size is excluded.

**Characterization outcome: C5, construct-scoped, NON-CONFIRMATORY** — the pre-declared criterion was tested on data and
failed; **M4a stays open** (it is not closed as a mechanism), and this run gives **no reason to spend a fresh confirmatory
window on this contrast.**

**What this does not say.** The negative sign is what volatility persistence predicts: the compression cohort is *selected
on a low recent range* (ATR10), and forward range tracks recent range (protocol §11(iv), stated before the run; the same
sign appears on random regime-switching synthetic data in the pre-freeze scale test). The contrast is against the
*unconditional* complement, not against names with the same current range level, so it cannot show whether compression carries
information *beyond the level of recent range*. That level-controlled question is untested and would be a new
pre-registration (§10).

## 2. What was run

Frozen specification (protocol §5–§7): D2 = ATR10/ATR60 of `(H−L)/C[s−1]`, trailing-252 percentile ending at t (t included,
`#(window ≤ x_t)/252`, complete windows only), compression = percentile ≤ 0.20, onset = no compression state on the prior 20
sessions; PIT top-200 daily panel (the certified BKV-1 dev snapshot, panel hash `46de7d4d…` asserted at load; nothing after
2022-12-30 loadable). Primary outcome `E_range = mean_{t+1..t+h}((H−L)/C[s−1]) / median_{t−251..t}(same)`, h ∈ {5, 20}. Estimand:
cohort-by-date `d(t) = mean_C(E) − mean_X(E)`, one-sided Newey–West with lag = h, **four primary cells** (h × {normal, persistence}),
Holm at α = 0.05 on VAL. Operator-confirmed pins (protocol §10): normal cohort = the literal complement (not in compression at t,
≥ 100 names/date); persistence comparator = the high-state cohort (percentile ≥ 0.80, onset-mirrored). D1 (RV10/RV60, same
percentile) is declared robustness only.

## 3. Primary result

**VAL 2018-01-01 → 2022-12-30 (the decision stage):**

| h | comparator | n C events | n X events | pair dates | dates < floor | mean E (C) | mean E (X) | d-bar | NW SE | t | p (1-sided) | Holm p | MDE80 | bound d-bar | Holm bound p |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 5 | persistence | 3,069 | 3,105 | 514 | 0 | 1.0329 | 1.2640 | -0.2321 | 0.0237 | -9.7817 | 1.0000 | 1.0000 | 0.0590 | -0.2364 | 1.0000 |
| 20 | persistence | 3,050 | 3,053 | 510 | 0 | 1.0861 | 1.1978 | -0.0866 | 0.0145 | -5.9891 | 1.0000 | 1.0000 | 0.0359 | -0.0894 | 1.0000 |
| 5 | normal | 3,069 | 189,466 | 701 | 116 | 1.0329 | 1.1855 | -0.1118 | 0.0163 | -6.8763 | 1.0000 | 1.0000 | 0.0404 | -0.1148 | 1.0000 |
| 20 | normal | 3,050 | 187,413 | 696 | 114 | 1.0861 | 1.1799 | -0.0592 | 0.0146 | -4.0602 | 1.0000 | 1.0000 | 0.0363 | -0.0637 | 1.0000 |

**TRAIN 2012-01-02 → 2017-12-29 (descriptive, takes no decision):**

| h | comparator | n C events | n X events | pair dates | dates < floor | mean E (C) | mean E (X) | d-bar | NW SE | t | p (1-sided) | Holm p | MDE80 | bound d-bar | Holm bound p |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 5 | persistence | 3,774 | 3,706 | 663 | 0 | 1.0266 | 1.2189 | -0.1729 | 0.0143 | -12.0647 | 1.0000 | 1.0000 | 0.0356 | -0.1729 | 1.0000 |
| 20 | persistence | 3,742 | 3,674 | 656 | 0 | 1.0606 | 1.1591 | -0.0802 | 0.0108 | -7.4548 | 1.0000 | 1.0000 | 0.0268 | -0.0813 | 1.0000 |
| 5 | normal | 3,774 | 225,657 | 897 | 115 | 1.0266 | 1.1241 | -0.0711 | 0.0075 | -9.5324 | 1.0000 | 1.0000 | 0.0185 | -0.0735 | 1.0000 |
| 20 | normal | 3,742 | 223,303 | 885 | 115 | 1.0606 | 1.1156 | -0.0414 | 0.0073 | -5.7034 | 1.0000 | 1.0000 | 0.0180 | -0.0467 | 1.0000 |

`d-bar` and `MDE80` are in units of the name's own trailing-median range; `mean E` columns are date-cohort means. "Holm p" is over the
four VAL cells (TRAIN Holm is shown for information only). "bound d-bar / Holm bound p" is the pre-specified worst-case
attrition bound (dropped C events set to the smallest retained C value, dropped comparator events to the largest retained X
value): it barely moves anything because attrition is tiny (§4). **No cell is VAL-consistent** (each has d̄ ≤ 0).

## 4. Event counts, formation dates, attrition

**VAL:**

| h | comparator | C events | C dates | X events | X dates | pair dates | dropped C | dropped X | value missing |
|---|---|---|---|---|---|---|---|---|---|
| 5 | persistence | 3,069 | 817 | 3,105 | 856 | 514 | 0 | 2 | 0 |
| 20 | persistence | 3,050 | 810 | 3,053 | 844 | 510 | 1 | 2 | 0 |
| 5 | normal | 3,069 | 817 | 189,466 | 1,228 | 701 | 0 | 45 | 0 |
| 20 | normal | 3,050 | 810 | 187,413 | 1,213 | 696 | 1 | 175 | 0 |

**TRAIN:**

| h | comparator | C events | C dates | X events | X dates | pair dates | dropped C | dropped X | value missing |
|---|---|---|---|---|---|---|---|---|---|
| 5 | persistence | 3,774 | 1,012 | 3,706 | 1,019 | 663 | 1 | 1 | 0 |
| 20 | persistence | 3,742 | 1,000 | 3,674 | 1,009 | 656 | 3 | 3 | 0 |
| 5 | normal | 3,774 | 1,012 | 225,657 | 1,448 | 897 | 1 | 52 | 0 |
| 20 | normal | 3,742 | 1,000 | 223,303 | 1,433 | 885 | 3 | 183 | 0 |

"pair dates" are the formation dates on which the contrast exists (≥ 1 compression event and the comparator floor met);
"dates < floor" is the number of dates with compression events and a normal cohort under 100 names that were excluded. The dropped events
(no forward window) are at most 0.1 % of any cohort. Accounting identities hold exactly (`formed = resolved + dropped + value missing
+ contained-out`; VP4):

| block | formed | resolved | dropped | value missing | excluded by containment |
|---|---|---|---|---|---|
| h5_C | 3,071 | 3,069 | 0 | 0 | 2 |
| h5_N | 190,468 | 189,466 | 45 | 0 | 957 |
| h5_P | 3,164 | 3,105 | 2 | 0 | 57 |
| h20_C | 3,071 | 3,050 | 1 | 0 | 20 |
| h20_N | 190,468 | 187,413 | 175 | 0 | 2,880 |
| h20_P | 3,164 | 3,053 | 2 | 0 | 109 |

## 5. The persistence comparison and cohort levels

The vs-persistence cells compare compression with the high-dispersion state (`pct ≥ 0.80`). Cohort levels (mean and median E,
D2), so the sign is visible rather than inferred:

**VAL:**

| h | cohort | events | dates | mean E (events) | median E | mean E (date-cohort) |
|---|---|---|---|---|---|---|
| 5 | C | 3,069 | 817 | 1.0527 | 0.9853 | 1.0329 |
| 5 | N | 189,466 | 1,228 | 1.2040 | 1.0797 | 1.1855 |
| 5 | P | 3,105 | 856 | 1.2925 | 1.1894 | 1.2640 |
| 20 | C | 3,050 | 810 | 1.0904 | 1.0407 | 1.0861 |
| 20 | N | 187,413 | 1,213 | 1.1955 | 1.0945 | 1.1799 |
| 20 | P | 3,053 | 844 | 1.2276 | 1.1463 | 1.1978 |

**TRAIN:**

| h | cohort | events | dates | mean E (events) | median E | mean E (date-cohort) |
|---|---|---|---|---|---|---|
| 5 | C | 3,774 | 1,012 | 1.0195 | 0.9577 | 1.0266 |
| 5 | N | 225,657 | 1,448 | 1.1370 | 1.0539 | 1.1241 |
| 5 | P | 3,706 | 1,019 | 1.2573 | 1.1587 | 1.2189 |
| 20 | C | 3,742 | 1,000 | 1.0624 | 1.0242 | 1.0606 |
| 20 | N | 223,303 | 1,433 | 1.1262 | 1.0749 | 1.1156 |
| 20 | P | 3,674 | 1,009 | 1.1752 | 1.1195 | 1.1591 |

Compression names (C) go on to a forward range about equal to their own trailing median, the complement (N) to a range
clearly above it, and the high-state names (P) to the highest — the ordering persistence implies. (A mean-over-median E above 1
is the ordinary skew of a daily range and is common to all three cohorts.)

## 6. Stability

**By year (d-bar per formation year, VAL then TRAIN):**

| year | h20 normal | h20 persistence | h5 normal | h5 persistence |
|---|---|---|---|---|
| 2018 | -0.0748 | -0.1378 | -0.1447 | -0.3357 |
| 2019 | -0.0523 | -0.0678 | -0.1024 | -0.2502 |
| 2020 | -0.1237 | -0.0837 | -0.2176 | -0.2442 |
| 2021 | -0.0459 | -0.0945 | -0.0747 | -0.1923 |
| 2022 | -0.0115 | -0.0479 | -0.0445 | -0.1510 |

| year | h20 normal | h20 persistence | h5 normal | h5 persistence |
|---|---|---|---|---|
| 2012 | -0.0276 | -0.0770 | -0.0549 | -0.1181 |
| 2013 | -0.0819 | -0.1376 | -0.1278 | -0.2782 |
| 2014 | -0.0497 | -0.0644 | -0.0636 | -0.1628 |
| 2015 | -0.0022 | -0.0312 | -0.0298 | -0.1053 |
| 2016 | -0.0365 | -0.0816 | -0.0714 | -0.1751 |
| 2017 | -0.0472 | -0.0982 | -0.0759 | -0.2158 |

Every value is negative: the result is not a single regime. **Concentration by date** (VAL, then TRAIN; top-10 dates are the ten
largest d(t)):

| cell | dates | d-bar | median d | d-bar ex top-10 | share of sum in top-10 | share d>0 |
|---|---|---|---|---|---|---|
| h5_normal | 701 | -0.1118 | -0.0992 | -0.1261 | -0.1118 | 0.2611 |
| h5_persistence | 514 | -0.2321 | -0.1790 | -0.2529 | -0.0684 | 0.2879 |
| h20_normal | 696 | -0.0592 | -0.0459 | -0.0719 | -0.1969 | 0.3448 |
| h20_persistence | 510 | -0.0866 | -0.0609 | -0.1047 | -0.1857 | 0.3941 |

| cell | dates | d-bar | median d | d-bar ex top-10 | share of sum in top-10 | share d>0 |
|---|---|---|---|---|---|---|
| h5_normal | 897 | -0.0711 | -0.0797 | -0.0815 | -0.1337 | 0.3032 |
| h5_persistence | 663 | -0.1729 | -0.1517 | -0.1877 | -0.0696 | 0.3137 |
| h20_normal | 885 | -0.0414 | -0.0455 | -0.0474 | -0.1330 | 0.3198 |
| h20_persistence | 656 | -0.0802 | -0.0673 | -0.0916 | -0.1247 | 0.3628 |

Removing the ten most favourable dates makes d̄ *more* negative; only 26–39 % of VAL dates have d(t) > 0. (The "share of sum in
top-10" column has no meaning when the sum is negative and is shown only for completeness.)

## 7. D1 robustness (RV10/RV60, same percentile construction; disclosure only)

**VAL:**

| h | comparator | n C | n X | pair dates | mean E (C) | mean E (X) | d-bar | t | p | Holm p (info) | MDE80 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 5 | normal | 3,345 | 189,868 | 899 | 1.0884 | 1.1808 | -0.0642 | -5.1680 | 1.0000 | 1.0000 | 0.0309 |
| 5 | persistence | 3,345 | 3,255 | 686 | 1.0884 | 1.2895 | -0.1934 | -7.1493 | 1.0000 | 1.0000 | 0.0673 |
| 20 | normal | 3,319 | 187,752 | 886 | 1.1310 | 1.1770 | -0.0333 | -3.3085 | 0.9995 | 1.0000 | 0.0250 |
| 20 | persistence | 3,319 | 3,197 | 675 | 1.1310 | 1.2040 | -0.0692 | -4.9645 | 1.0000 | 1.0000 | 0.0347 |

**TRAIN:**

| h | comparator | n C | n X | pair dates | mean E (C) | mean E (X) | d-bar | t | p | Holm p (info) | MDE80 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 5 | normal | 4,060 | 224,609 | 1,133 | 1.0613 | 1.1225 | -0.0513 | -7.6502 | 1.0000 | 1.0000 | 0.0167 |
| 5 | persistence | 4,060 | 3,985 | 924 | 1.0613 | 1.2013 | -0.1432 | -11.5784 | 1.0000 | 1.0000 | 0.0308 |
| 20 | normal | 4,023 | 222,331 | 1,120 | 1.0874 | 1.1143 | -0.0257 | -5.6922 | 1.0000 | 1.0000 | 0.0112 |
| 20 | persistence | 4,023 | 3,952 | 915 | 1.0874 | 1.1371 | -0.0466 | -5.4569 | 1.0000 | 1.0000 | 0.0213 |

The estimator makes no difference to the sign: D1 is wrong-signed in all four cells in both stages (the two definitions of
compression select overlapping but not identical names; D1 has more compression dates that pass the floor).

## 8. Secondary outcomes (report-only, unadjusted, non-classifying) and signed move (descriptive)

**Realized-volatility expansion and absolute forward move, D2, VAL:**

| outcome | h | comparator | pair dates | mean (C) | mean (X) | d-bar | t | p (unadj.) | MDE80 |
|---|---|---|---|---|---|---|---|---|---|
| E_vol | 5 | normal | 701 | 0.8091 | 0.9082 | -0.0607 | -4.6074 | 1.0000 | 0.0327 |
| E_abs | 5 | normal | 701 | 0.7202 | 0.7757 | -0.0167 | -0.8517 | 0.8027 | 0.0489 |
| E_vol | 5 | persistence | 514 | 0.8091 | 0.9476 | -0.1228 | -5.2687 | 1.0000 | 0.0580 |
| E_abs | 5 | persistence | 514 | 0.7202 | 0.8262 | -0.0741 | -2.1484 | 0.9839 | 0.0858 |
| E_vol | 20 | normal | 696 | 0.9065 | 0.9753 | -0.0327 | -3.0715 | 0.9989 | 0.0265 |
| E_abs | 20 | normal | 696 | 0.8088 | 0.8219 | 0.0226 | 1.1624 | 0.1227 | 0.0483 |
| E_vol | 20 | persistence | 510 | 0.9065 | 0.9920 | -0.0418 | -2.8764 | 0.9979 | 0.0361 |
| E_abs | 20 | persistence | 510 | 0.8088 | 0.8814 | -4.93e-04 | -0.0132 | 0.5053 | 0.0927 |

**TRAIN:**

| outcome | h | comparator | pair dates | mean (C) | mean (X) | d-bar | t | p (unadj.) | MDE80 |
|---|---|---|---|---|---|---|---|---|---|
| E_vol | 5 | normal | 897 | 0.8145 | 0.8835 | -0.0458 | -4.3302 | 1.0000 | 0.0263 |
| E_abs | 5 | normal | 897 | 0.7181 | 0.7519 | -0.0161 | -1.0469 | 0.8523 | 0.0383 |
| E_vol | 5 | persistence | 663 | 0.8145 | 0.9492 | -0.1234 | -5.9168 | 1.0000 | 0.0519 |
| E_abs | 5 | persistence | 663 | 0.7181 | 0.7929 | -0.0727 | -2.3533 | 0.9905 | 0.0768 |
| E_vol | 20 | normal | 885 | 0.9031 | 0.9432 | -0.0304 | -3.1232 | 0.9991 | 0.0242 |
| E_abs | 20 | normal | 885 | 0.7551 | 0.7692 | -0.0220 | -1.2780 | 0.8992 | 0.0427 |
| E_vol | 20 | persistence | 656 | 0.9031 | 0.9791 | -0.0505 | -3.0168 | 0.9987 | 0.0416 |
| E_abs | 20 | persistence | 656 | 0.7551 | 0.7822 | -0.0119 | -0.4130 | 0.6601 | 0.0719 |

The realized-volatility contrast is negative like the range. The *absolute move* contrast is smaller than the range contrast and mixed in sign: negative in most cells (the 5/persistence cell is
negative in both stages, t ≈ −2.2 VAL and −2.4 TRAIN, unadjusted), slightly positive only in VAL 20/normal (+0.023, p = 0.12); no cell is
positive-significant and none is promoted. That is a descriptive observation among 8 unadjusted secondary cells per stage and is **not** a finding.

**Signed forward move — descriptive means only, no test of any kind (VAL, then TRAIN):**

| h | cohort | events | mean signed move | date-cohort mean | share > 0 |
|---|---|---|---|---|---|
| 5 | C | 3,069 | -0.0278 | 0.0274 | 0.4787 |
| 5 | N | 189,466 | -0.0274 | -0.0156 | 0.5012 |
| 5 | P | 3,105 | -0.0330 | -0.0271 | 0.5069 |
| 20 | C | 3,050 | 0.0067 | 0.0145 | 0.5154 |
| 20 | N | 187,413 | -0.0432 | -0.0268 | 0.5114 |
| 20 | P | 3,053 | -0.1391 | -0.0990 | 0.4792 |

| h | cohort | events | mean signed move | date-cohort mean | share > 0 |
|---|---|---|---|---|---|
| 5 | C | 3,774 | 0.0484 | 0.0438 | 0.5180 |
| 5 | N | 225,657 | 0.0408 | 0.0332 | 0.5188 |
| 5 | P | 3,706 | 0.0062 | 0.0064 | 0.5189 |
| 20 | C | 3,742 | 0.0600 | 0.0650 | 0.5299 |
| 20 | N | 223,303 | 0.0628 | 0.0574 | 0.5343 |
| 20 | P | 3,674 | 0.0268 | 0.0154 | 0.5340 |

## 9. Report-only tests (unadjusted)

**VAL:**

| h | comparator | d-bar | event-wtd d | boot CI lo | boot CI hi | cluster b | cluster t | cluster p | perm p |
|---|---|---|---|---|---|---|---|---|---|
| 5 | persistence | -0.2321 | -0.2275 | -0.2799 | -0.1872 | -0.2540 | -8.2107 | 1.0000 | 1.0000 |
| 20 | persistence | -0.0866 | -0.0789 | -0.1141 | -0.0619 | -0.1449 | -5.2715 | 1.0000 | 1.0000 |
| 5 | normal | -0.1118 | -0.0860 | -0.1580 | -0.0761 | -0.1094 | -7.4566 | 1.0000 | 1.0000 |
| 20 | normal | -0.0592 | -0.0450 | -0.0939 | -0.0325 | -0.0692 | -6.1548 | 1.0000 | 1.0000 |

**TRAIN:**

| h | comparator | d-bar | event-wtd d | boot CI lo | boot CI hi | cluster b | cluster t | cluster p | perm p |
|---|---|---|---|---|---|---|---|---|---|
| 5 | persistence | -0.1729 | -0.1697 | -0.2000 | -0.1455 | -0.2015 | -11.9103 | 1.0000 | 1.0000 |
| 20 | persistence | -0.0802 | -0.0652 | -0.1024 | -0.0586 | -0.0827 | -7.0063 | 1.0000 | 1.0000 |
| 5 | normal | -0.0711 | -0.0651 | -0.0859 | -0.0562 | -0.0886 | -11.5095 | 1.0000 | 1.0000 |
| 20 | normal | -0.0414 | -0.0337 | -0.0576 | -0.0271 | -0.0481 | -7.5738 | 1.0000 | 1.0000 |

Event-weighted contrast, block-bootstrap 95 % CI, two-way (entity, date) clustered event contrast and within-date permutation p all
agree with the Newey–West result. (`cluster p` and `perm p` are one-sided for d̄ > 0, hence ≈ 1.)

## 10. What a successor would have to be

* This characterization gives no evidence in favour of spending an unread window on the *same* contrast.
* The untested question is level-controlled: does compression predict expansion **among names with the same current short-run
  range** (e.g. matched on ATR10 percentile or on trailing range level), i.e. does the ATR10/ATR60 *ratio* carry information beyond
  the *level* of recent range? That is a different estimand, needs its own pre-registration (with the persistence control declared
  before any read), its own power-feasibility check (RFA) and a genuinely unread surface (inventory §9.4: India VIX 1m/EOD, the
  101 unread vendor-N100 1m names, or a future window). It is **not** authorised or started by this report.
* Nothing here is a trading result; there is no cost model and no strategy.

## 11. Independent verification

| stage | check | result | detail |
|---|---|---|---|
| TRAIN | VP1 SQL vs engine (D2) | PASS | 230,327 ledger rows = 230,327 SQL rows; 1,841,660 values; max |pct| diff 0.0e+00; max |E| diff 4.9e-14; flag mismatches 0 |
| TRAIN | VP1 SQL vs engine (D1) | PASS | 229,373 ledger rows = 229,373 SQL rows; 1,834,084 values; max |pct| diff 4.0e-03; max |E| diff 4.9e-14; flag mismatches 0 |
| TRAIN | VP2 raw as-traded loops | PASS | 11 verified of 12 sampled; skipped for a corporate action 1; max |E| diff 1.4e-15 |
| TRAIN | VP3 statistics (manual NW + statsmodels kernel) | PASS | max abs diff d_mean 9.7e-17, d_se 1.0e-16, d_t 2.7e-15, d_p 1.1e-16, kernel_se 9.7e-17, n_pair 0.0e+00 |
| TRAIN | VP4 accounting / uniqueness / exclusivity | PASS | identities exact |
| TRAIN | VP5 price basis | PASS | adjusted = raw on CA-free names (max rel diff 0.0e+00); CA rebuild agreement 3000/3000 |
| VAL | VP1 SQL vs engine (D2) | PASS | 193,539 ledger rows = 193,539 SQL rows; 1,531,992 values; max |pct| diff 0.0e+00; max |E| diff 1.2e-13; flag mismatches 0 |
| VAL | VP1 SQL vs engine (D1) | PASS | 194,190 ledger rows = 194,190 SQL rows; 1,537,136 values; max |pct| diff 0.0e+00; max |E| diff 2.6e-13; flag mismatches 0 |
| VAL | VP2 raw as-traded loops | PASS | 10 verified of 12 sampled; skipped for a corporate action 2; max |E| diff 3.7e-15 |
| VAL | VP3 statistics (manual NW + statsmodels kernel) | PASS | max abs diff d_mean 9.7e-17, d_se 9.2e-17, d_t 2.7e-15, d_p 1.1e-16, kernel_se 9.4e-17, n_pair 0.0e+00 |
| VAL | VP4 accounting / uniqueness / exclusivity | PASS | identities exact |
| VAL | VP5 price basis | PASS | adjusted = raw on CA-free names (max rel diff 0.0e+00); CA rebuild agreement 3000/3000 |

VP1 compares 3.1–3.7 million ledger values per stage with a pure-SQL re-derivation (own calendar, membership, ranges, means, `list_filter`
percentile, onset rule, windows) with **zero** missing or extra rows, **zero** flag or status mismatches, percentile and E
agreeing to ~1e-13. **Amendment A1:** on the first TRAIN verification VP1 stopped on the D1 robustness variant: one row of 229,373
(MARKSANS, session 1596, normal cohort) differed by exactly 1/252 in percentile because the window holds an exact mathematical
tie between two ratios that the numpy and SQL float paths break differently (confirmed by direct recomputation). It was
investigated before anything was changed; the verifier tolerance was amended (a percentile difference passes only if it is an integer
number of 1/252 steps no larger than the count of tied window values), tested, and the freeze re-recorded with history. No engine,
cohort, outcome, analysis or classification code changed and no result changed. That row is the only percentile difference in the
whole verification.

**Label:** C5 (construct-scoped; NON-CONFIRMATORY characterization: no VAL-consistent cell; M4a stays open)

| cell (h,comparator) | d-bar | Holm p | attrition-fragile |
|---|---|---|---|
| 5,normal | -0.1118 | 1.0000 | 1 |
| 5,persistence | -0.2321 | 1.0000 | 1 |
| 20,normal | -0.0592 | 1.0000 | 1 |
| 20,persistence | -0.0866 | 1.0000 | 1 |

## 12. Vault taxonomy mapping (the ledger is not modified)

| Item | Mapping |
|---|---|
| This run | **C5, construct-scoped, non-confirmatory** (criterion tested on data, failed; the D2 ATR-ratio compression state, onset, PIT top-200 daily, range-expansion outcome, complement and high-state comparators) |
| M4a as a mechanism | unchanged: **C — open** (construct-scoped negative; the level-controlled question is untested) |
| Sealed / unread windows | untouched: no HOLDOUT read; the 2023-01-02 → present equity window was never loaded; TRAIN/VAL were already signal-spent |
| C6 / C7 / C8 | not reached (no VAL-consistent cell; no HOLDOUT; no economic gate) |
| Register | owed to the operator (not done here): an exposure-register row for this 2012–2022 equity-EOD read |

## 13. Pre-run predictions (protocol §11), checked

(i) Accounting identities and C∩N = C∩P = ∅: **hold exactly** (VP4). (ii) The diagnostics counts reproduce: D2 compression events TRAIN 3,790 / VAL 3,071 in
the diagnostics vs 3,774 / 3,069 resolved at h = 5 here (the difference is the events whose window is not available or leaves the stage).
(iii) VP1 agrees row-for-row with zero exceptions: **yes** (after the tie-tolerance amendment for one D1 row). (iv) Sign: **d̄ < 0 in all
four cells and stages** — predicted for the persistence cells and "probably" for the normal cells; the modal outcome C5 occurred.

## 14. Reproducibility and limits

TRAIN and VAL were re-run from the hashed snapshot into a scratch directory under the final freeze; every result file is
byte-identical (parquet ledgers frame-identical) — `repro_check.json`. Limits: TRAIN/VAL are spent, so this is a characterization;
~3–4 compression names per formation date make the per-date contrast noisy (the MDE is reported and is small relative to the
observed effects); dropped-window attrition is negligible; the persistence cells are a demanding comparator by construction; only one
universe, one estimator family and two horizons were examined, as pre-registered.

## 15. Files

`scripts/m4a_compress/{common,panel,state,cohorts,outcome,analyze,classify,stats,diagnostics,freeze,run_stage,verify_independent,build_report}.py`,
`tests/m4a_compress/` (55 tests: state, cohorts, outcome, analysis, panel, governance, synthetic end-to-end), protocol `.md` + `.json`,
freeze record `m4a_compress_FREEZE.json`, research log, result bundle `docs/reports/research/m4a_compress/`.
