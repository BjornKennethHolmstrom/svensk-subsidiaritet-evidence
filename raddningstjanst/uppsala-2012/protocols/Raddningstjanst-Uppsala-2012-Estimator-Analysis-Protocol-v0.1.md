# Uppsala 2012 — Estimator & Analysis Protocol v0.1

**Protocol status:** METHOD LOCKED; PRIMARY OUTCOME UNMASKING BLOCKED UNTIL JÖNKÖPING A=0 ACTIVATION GATE PASSES  
**Protocol date:** 2026-09-10  
**Primary strict window:** 2007–2009 vs 2012–2014  
**Anticipation excluded:** 2010–2011  
**Post-treatment B20 outcomes inspected while writing this protocol:** **0**

## 1. Purpose

This protocol fixes the estimand, donor hierarchy, analysis windows, estimators, missing-data rules, sensitivities, inference language and outcome-unmask sequence **before** Uppsala's 2012–2014 B20 outcomes are opened.

The goal is not to maximize the chance of obtaining a clean treatment effect. The goal is to make it difficult to change the design after seeing whether the observed effect is attractive.

## 2. What treatment is actually being estimated?

The treatment is **not** the creation of an entirely new three-municipality rescue organization from three independent services.

The treatment-history reconstruction records that Uppsala's first strict full-A event is the common Tierp–Uppsala–Östhammar rescue board beginning **2012-01-01**, while Tierp and Östhammar had already entered full A through Räddningstjänsten Norduppland in **2005**. Uppsala also participated in county-level rescue cooperation and shared leadership before 2012.

Therefore the treated-outcome unit is **Uppsala municipality**, and the causal contrast is:

> **Uppsala under existing operational cooperation K → Uppsala formally integrated into pooled authority A with already-integrated neighbouring partners.**

The ATT-like estimand is the short-run effect on Uppsala's severe building-fire rate in 2012–2014 relative to the counterfactual in which Uppsala had remained in a comparable **K-without-A** governance state.

This is a narrower and more defensible estimand than “the effect of municipal rescue-service mergers”.

## 3. Time lock

**Primary clean pre-period:** 2007, 2008, 2009.  
**Anticipation/implementation band:** 2010, 2011 — excluded from primary estimation.  
**Primary post-period:** 2012, 2013, 2014.  
**2015:** measurement-edge extended-horizon sensitivity only, after strict result.

The 2009 deeper-cooperation study is handled in a conservative anticipation sensitivity using only 2007–2008 as clean pre.

## 4. Outcome lock

Primary:

`FIRE_FINAL_BEYOND_START_OBJECT_RATE_PER_100K`

Numerator = B20 final-extent codes `2+3+4+5`.

Exposure:

\[
M_t = (P_{31/12,t-1}+P_{31/12,t})/2.
\]

Rate:

\[
R_{it}=100000 \times C_{it}/M_{it}.
\]

Secondary conditional share:

\[
S_{it}=C_{2+3+4+5}/C_{6+1+2+3+4+5}.
\]

Previously locked threshold sensitivities:

- beyond start room: `(3+4+5)/valid extent`;
- beyond firecell: `(4+5)/valid extent`.

No ordinal severity score may be introduced.

## 5. Frozen donor hierarchy

### Primary — Jönköping / RäddSam F

Jönköping was selected structurally before the completed pre-match values were known.

Pre-match diagnostics:
- mean-rate ratio vs Uppsala: 0.794;
- raw RMSE: 9.75;
- slope difference: +2.51 per 100,000/year;
- 475 valid B20 records / 119 primary events.

**Activation gate:** before any 2012–2014 primary outcomes are opened, archive contemporaneous evidence confirming that Jönköping remained **A=0 with no commitment to pooled authority through 2014**.

If this gate fails or remains materially ambiguous:

> **HALT the primary causal analysis. Do not silently substitute another donor.**

Current public information continues to describe RäddSam F as inter-municipal cooperation based on agreements while Jönköping's rescue service is a Jönköping municipal administration, but the contemporaneous 2014 archival lock remains required.

### Secondary — Piteå–Älvsbyn / Femkanten

Role: **prespecified secondary donor + K→later-A path sensitivity**.

Pre-match:
- mean ratio 1.125;
- RMSE 5.12;
- slope difference +0.19;
- shape RMSE 0.95.

It is not promoted to primary because its strongest shared-chief K begins around 2010 and scale differs markedly from Uppsala.

Piteå and Älvsbyn are pooled as one control system:

\[
R_{PA,t}=100000\times
\frac{C_{Piteå,t}+C_{Älvsbyn,t}}
{M_{Piteå,t}+M_{Älvsbyn,t}}.
\]

### Halmstad / RäddSam Halland

Sensitivity only if exact pre-2010 shared/system-leadership K comparable to Uppsala is verified **before** Halmstad's 2012–2014 outcomes are opened.

Otherwise Halmstad remains descriptive only.

### Skåne Nordväst

Cluster robustness only. Höganäs, Båstad and Bjuv are population-pooled and never treated as three independent donors.

## 6. Why synthetic control is not primary

There are only **three clean pre-treatment outcome years** and four independent candidate K systems. Outcome-optimized synthetic weights would therefore have substantial scope to fit noise.

Abadie's methodological guidance emphasizes data requirements and the risk of overfitting with short pre-treatment histories. Therefore no synthetic-control, synthetic-DiD or other outcome-optimized donor weights are used.

Reference: https://www.aeaweb.org/articles?id=10.1257/jel.20191450

## 7. Primary estimator

For Uppsala U and Jönköping J:

\[
IRR_U=
\frac{C_{U,post}/E_{U,post}}
{C_{U,pre}/E_{U,pre}}
\]

\[
IRR_J=
\frac{C_{J,post}/E_{J,post}}
{C_{J,pre}/E_{J,pre}}
\]

\[
RRR=\frac{IRR_U}{IRR_J}.
\]

Interpretation:
- `RRR = 1`: same proportional before/after change as Jönköping;
- `RRR < 1`: Uppsala's severe-fire rate fell more, or rose less;
- `RRR > 1`: Uppsala's rate rose more, or fell less.

Also report `100*(RRR-1)%`.

## 8. Absolute companion

Report:

\[
\Delta_{abs} =
(R_{U,post}-R_{U,pre})
-
(R_{J,post}-R_{J,pre})
\]

in severe events per 100,000.

## 9. Year-balanced sensitivity

\[
RRR_{year}=
\frac{GM(R_{U,t}/R_{J,t}),\ t=2012:2014}
{GM(R_{U,t}/R_{J,t}),\ t=2007:2009}.
\]

If any annual rate is zero, this sensitivity is unavailable. No continuity correction is permitted.

## 10. Count-process interval

Report a 95% Poisson count-process interval:

\[
SE[\log(RRR)] =
\sqrt{
1/C_{U,post}+
1/C_{U,pre}+
1/C_{J,post}+
1/C_{J,pre}
}.
\]

\[
CI=\exp[\log(RRR)\pm1.96SE].
\]

This is explicitly a **count-process interval, not a full causal-confidence interval**. It does not quantify donor choice, parallel-trend, treatment-state or spillover uncertainty.

If an aggregated count is zero, no log interval is computed and no continuity correction is added.

## 11. No conventional few-cluster p-value

There is one treated outcome unit and only a handful of independent comparison systems. Standard large-cluster DiD inference is therefore not used as primary evidence.

Conley and Taber show why standard DiD inference can be misleading with very few policy changes.

Reference: https://www.nber.org/papers/t0312

No `p < .05` rule defines success or failure. A tiny placebo rank may later be shown descriptively but is not called an exact causal p-value.

## 12. Donor robustness rule

Always display the Jönköping and Piteå–Älvsbyn RRRs side by side.

Locked rule:

> If their point estimates lie on opposite sides of 1, label the result **DONOR_SENSITIVE / INCONCLUSIVE**, regardless of the Jönköping count-process interval.

Same-direction estimates are reported as directional consistency, not statistical proof.

## 13. Missing final extent

Always report `Uppgift saknas` and worst-case RRR bounds.

Minimum RRR assignment:
- Uppsala post missing → nonsevere;
- Uppsala pre missing → severe;
- donor post missing → severe;
- donor pre missing → nonsevere.

Maximum RRR = reverse assignments.

If the bound crosses 1, flag `MISSINGNESS_DIRECTION_NOT_ROBUST`.

No missing record may be recoded after seeing the observed effect direction.

## 14. Data-quality stop rules

Before effect computation:
1. exactly one municipality-year for each requested unit/year;
2. underlying raw extraction contains all seven locked B20 extent categories exactly once;
3. category codes unchanged;
4. positive SCB mean population;
5. no duplicate keys;
6. strict primary file contains only 2012–2014.

At freeze, the known-missingness ledger contains **zero known 2012–2014 flags** for protocol municipalities.

A newly discovered reporting break is logged; years are never silently removed after seeing outcomes.

## 15. Prespecified sensitivities

1. **Conservative anticipation:** pre = 2007–2008; 2009–2011 treated as anticipation.
2. **2015 edge:** add 2015 only after strict result, after donor-state verification through 2015.
3. **Secondary conditional share:** beyond-first-object share.
4. **Threshold shares:** beyond start room and beyond firecell.
5. **Skåne NW cluster robustness:** pooled cluster; Höganäs-only descriptive check.
6. **Optional PPML/Poisson DID check:** annual counts with log population offset, unit FE and year FE; point-estimate diagnostic only.

## 16. Outcome-unmask sequence

### Gate 0

Before any strict post outcome:
- protocol files hashed/frozen;
- Jönköping A=0/no-A-commitment through 2014 = PASS.

If not PASS: stop.

### Batch 1 — strict primary

Open exactly **12 municipality-years**:
- Uppsala 2012–2014;
- Jönköping 2012–2014;
- Piteå 2012–2014;
- Älvsbyn 2012–2014.

Immediately run the locked runner and save the immutable strict result.

### Batch 2 — diagnostics

Only after Batch 1:
- Halmstad 2012–2014 if K gate passes;
- Höganäs/Båstad/Bjuv 2012–2014;
- 2011 anticipation diagnostic;
- 2015 measurement-edge extension.

Batch 2 cannot change the primary donor, estimator or time window.

## 17. Required interpretation flags

Final output exposes:
- `PRIMARY_RRR_DIRECTION`;
- `COUNT_PROCESS_INTERVAL_CROSSES_1`;
- `PRIMARY_SECONDARY_DONOR_SIGN_CONSISTENT`;
- `MISSINGNESS_BOUNDS_CROSS_1`;
- `STRUCTURAL_ACTIVATION_GATE_STATUS`;
- `MEASUREMENT_CAVEATS`.

There is no automatic causal success/failure label.

## 18. Generalization boundary

At most, this design estimates the short-run Uppsala-specific effect of formal authority integration into the 2012 common-board arrangement relative to structurally selected K-without-A comparators.

It does not identify the average effect of Swedish rescue-service mergers/federations, nor the 2012 effect on Tierp/Östhammar, which already had prior A histories.

## 19. Activation decision

\[
\boxed{\textbf{METHOD PROTOCOL: FROZEN v0.1}}
\]

\[
\boxed{\textbf{PRIMARY OUTCOME UNMASK: NOT YET — JÖNKÖPING A=0 ARCHIVAL GATE OPEN}}
\]

Once that structural gate is closed, no further outcome-based design decision is required before Batch 1.

## 20. Method references

- Abadie, A. (2021), *Using Synthetic Controls: Feasibility, Data Requirements, and Methodological Aspects.*  
  https://www.aeaweb.org/articles?id=10.1257/jel.20191450
- Conley, T. G. & Taber, C. R. (2011), *Inference with “Difference in Differences” with a Small Number of Policy Changes.*  
  https://www.nber.org/papers/t0312
- Arkhangelsky et al. (2021), *Synthetic Difference-in-Differences.* Relevant method class but not selected here because clean pre-treatment support is too short for outcome-optimized weighting.  
  https://pubs.aeaweb.org/doi/10.1257/aer.20190159

## 21. Frozen pre-treatment Uppsala reference

| Year | Severe count | Mean population | Rate / 100,000 |
|---:|---:|---:|---:|
| 2007 | 90 | 186364.0 | 48.29 |
| 2008 | 53 | 189104.5 | 28.03 |
| 2009 | 85 | 192709.5 | 44.11 |

No post-treatment outcome value is contained in this protocol.
