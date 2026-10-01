# Räddningstjänst — Uppsala 2012
## Final Causal Synthesis v1.0

### Research question

Does Uppsala's transition from long-standing operational cooperation (K) to formal pooled authority through the common rescue board (A) in 2012 appear to have changed the population rate of building fires whose final extent spread beyond the object where the fire started?

The study is a local Uppsala-specific causal-feasibility case, not a general estimate of the effect of Swedish rescue-service mergers or common boards.

### Frozen design

- **Treatment process:** K → A, with formal A from 2012.
- **Clean pre-period:** 2007–2009.
- **Anticipation/implementation band:** 2010–2011.
- **Strict post-period:** 2012–2014.
- **Measurement-edge extension:** 2015 only as sensitivity.
- **Primary outcome:** population rate per 100,000 of B20 building-fire records ending beyond the start object (codes 2+3+4+5).
- **Primary donor:** Jönköping / RäddSam F.
- **Prespecified secondary donor:** Piteå–Älvsbyn / Femkanten.
- **Additional sensitivity donor:** Halmstad / RäddSam Halland.
- **Cluster robustness:** Skåne Nordväst pooled as one independence cluster.
- **Primary estimator:** period-aggregated controlled ratio-of-rate-ratios (RRR).
- Count-process intervals are descriptive count-process uncertainty intervals, not complete causal-confidence intervals.

## 1. Strict primary result

Against Jönköping, the locked strict RRR is **0.9311**, corresponding to a **6.9% lower relative change** in Uppsala during 2012–2014. The count-process interval is **0.683–1.269**, so sampling uncertainty is substantial.

The prespecified Piteå–Älvsbyn comparison gives **RRR 0.9347** (−6.5%), almost identical to the primary point estimate, with interval **0.637–1.372**.

The year-balanced sensitivities retain the direction: **0.9474** and **0.9395**.

## 2. Counterfactual robustness

The four system-level comparisons are:

| Counterfactual system | RRR | Direction |
|---|---:|---|
| Jönköping / RäddSam F | 0.931 | Uppsala-favorable |
| Piteå–Älvsbyn / Femkanten | 0.935 | Uppsala-favorable |
| Halmstad / RäddSam Halland | 1.105 | Opposite |
| Skåne Nordväst pooled | 0.921 | Uppsala-favorable |

Three of four plausible system-level counterfactuals point below 1. Particularly notable is the numerical clustering of the three favorable estimates: **0.921, 0.931, 0.935**.

Halmstad is a genuine counterexample rather than a technical failure: its RRR is **1.105**, with missingness bounds wholly above 1. The causal signal is therefore **not fully counterfactual-robust**.

Skåne Nordväst strengthens the directional majority but remains internally heterogeneous; the municipalities cannot be treated as independent replications.

## 3. Timing and anticipation

The 2011 diagnostic shows favorable Uppsala-relative divergence before the formal 2012 start:

- vs Jönköping: **0.665**
- vs Piteå–Älvsbyn: **0.801**

The post-2012 favorable direction was therefore already visible during the anticipation/implementation band.

This weakens a causal story in which the legal start date of 1 January 2012 acts as a discrete switch. It is, however, compatible with a broader institutional-transition effect beginning during preparation and implementation in 2010–2011.

The diagnostic cannot distinguish such anticipation from local shocks or ordinary annual fire-count variation.

## 4. Measurement-edge persistence

Adding 2015 to the post horizon preserves and slightly strengthens the favorable direction:

- Jönköping: strict **0.9311** → extended **0.9247**
- Piteå–Älvsbyn: strict **0.9347** → extended **0.8950**

The locked classification is **CORE_DIRECTION_PERSISTS_THROUGH_MEASUREMENT_EDGE**.

This is evidence of horizon persistence, not stronger causal identification. 2015 remains outside the primary window because it sits at the edge of the national reporting-regime transition.

## 5. Missingness and measurement

Missing final-extent records do not explain the primary Jönköping result or the Skåne NW robustness result: their worst-case missingness bounds remain below 1.

Piteå–Älvsbyn's strict missingness bounds cross 1 slightly, although its 2015-extended bounds remain below 1.

The study deliberately avoids the 2016–2018 staggered transition from insatsrapport to händelserapport in the primary analysis.

## 6. Mechanism evidence

Severity-threshold and conditional-share outcomes are mixed across donors. The data do **not** support a clean mechanism claim that formal integration improved fire suppression after arrival.

The population-rate outcome could reflect multiple system pathways, including prevention, incident mix, detection/dispatch, resource availability, suppression, or reporting/composition.

Therefore the study identifies, at most, a system-level association/effect signal rather than a specific operational mechanism.

## 7. Evidentiary judgment

### Direction
**Moderate support.** Three of four system-level counterfactuals are favorable, and three point estimates cluster tightly around a 6–8% relative reduction.

### Statistical precision
**Low.** All principal count-process intervals are wide and cross 1.

### Counterfactual robustness
**Moderate but incomplete.** Halmstad gives a legitimate opposite-direction result.

### Timing identification
**Weak for a discrete 2012 onset.** Favorable relative divergence is already visible in 2011.

### Measurement robustness
**Moderate.** The strict result remains stable through the 2015 measurement-edge sensitivity, but later reporting-regime years are not used.

### Mechanism specificity
**Low.** Secondary severity outcomes do not identify a consistent suppression mechanism.

## Final conclusion

> **The Uppsala case provides suggestive, non-conclusive causal evidence that the broader transition from established operational cooperation to formal integrated rescue-service governance was associated with a modest reduction in the population rate of building fires spreading beyond the start object. The strict primary estimate is approximately 7% favorable and is closely reproduced by two additional system-level counterfactuals, while one plausible donor gives the opposite direction. The favorable divergence is already visible in 2011, so the evidence supports an institutional-transition/process interpretation more strongly than a discrete causal effect beginning at the formal 2012 legal start. Wide count uncertainty, one treated municipality, counterfactual sensitivity, and inconsistent mechanism outcomes preclude a strong or general causal claim.**

## What this study can and cannot support

It can support the proposition that **organizational form may matter enough to merit larger causal study**, and that treating institutional reform as a transition process rather than a binary legal event is empirically important.

It cannot establish that common rescue boards generally improve outcomes, that Uppsala's formal 2012 legal change alone caused the observed difference, or that the effect operates specifically through improved suppression performance.

### Overall evidence label

**Suggestive causal signal / hypothesis-strengthening evidence — not confirmatory causal evidence.**
