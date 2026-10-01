# Räddningstjänst — Historical 2002 Cohort
## Post-Unmask Data-Availability Amendment v0.1

**Date:** 2026-09-30  
**Status:** FROZEN AFTER POST-OUTCOME UNMASKING, BEFORE ESTIMATION  
**Parent protocol:** `Raddningstjanst-Historical-2002-Estimator-Analysis-Protocol-v0.1`  
**Scope:** Data-availability handling only  
**Estimator status:** UNCHANGED  
**Primary estimand status:** UNCHANGED

---

## 1. Purpose

This amendment resolves an unforeseen data-availability condition discovered only after the frozen 2003–2004 post-treatment extract was opened.

It does **not** revise:

- the causal question;
- the treated cohort;
- the structural control risk set;
- the treatment definition;
- the primary outcome;
- the primary estimator;
- the population exposure definition;
- the clean pre-period;
- the strict post-period;
- the uncertainty specification;
- the pre-window sensitivities;
- the item-nonresponse sensitivity;
- the leave-one-event-out analyses;
- the legal-form descriptive analysis;
- or the interpretation rules frozen before post-outcome unmasking.

Its sole purpose is to specify, before estimation, how complete municipality-year reporting loss in the post period will be handled.

---

## 2. Trigger for amendment

The frozen post-treatment request covered:

- 42 municipalities;
- calendar years 2003 and 2004;
- seven locked `Brandens omfattning vid ankomst` categories;
- 84 municipality-years in total.

Structural inspection of the returned MCF extract established that the requested keys and category rows were present, but all seven category counts were blank for exactly three municipality-years:

| Municipality | Year | Role | Event |
|---|---:|---|---|
| Ekerö | 2003 | Control | `EV_SBFF_2007` |
| Ekerö | 2004 | Control | `EV_SBFF_2007` |
| Bjuv | 2004 | Control | `EV_RSNV_BJUV_2019` |

All other requested municipality-years contain observed category counts.

Observed post-period coverage is therefore:

- **81 / 84 municipality-years complete**;
- **18 / 18 treated municipality-years complete**;
- **63 / 66 control municipality-years complete**.

---

## 3. External clarification from MCF

After structural QA and before estimation, MCF was asked whether the blank municipality-years represented:

1. missing values only for the arrival-extent variable; or
2. complete absence of incident reports.

MCF confirmed that **incident reports are missing entirely** for:

- Ekerö 2003;
- Ekerö 2004;
- Bjuv 2004.

MCF further confirmed that it therefore cannot determine even the total number of incidents for these municipality-years.

The agency explained that submission of incident reports was voluntary during this historical period; a statutory reporting requirement was introduced only later.

Consequently, the missing municipality-years cannot be reconstructed, bounded using observed annual incident totals, or interpreted as zero-event years.

---

## 4. Missingness classification

The three missing municipality-years are classified as:

`STRUCTURAL_REPORTING_ABSENCE`

This is distinct from the previously frozen category:

`ITEM_NONRESPONSE`

represented by `Ej angiven`.

### `ITEM_NONRESPONSE`

An incident report exists, but arrival extent is unspecified.

This remains governed by the adversarial missingness sensitivity frozen in the parent protocol.

### `STRUCTURAL_REPORTING_ABSENCE`

No incident reports are available for the municipality-year.

Neither the primary numerator nor the total number of reported building fires is observed.

These municipality-years therefore contain **no usable outcome information** and must not be assigned zero counts.

The two missingness mechanisms must remain analytically separate.

---

## 5. No replacement controls

No municipality will be substituted for Ekerö or Bjuv.

The structural control risk set was frozen before historical post-treatment outcomes were opened using pre-specified eligibility rules.

Introducing replacement municipalities after post-outcome unmasking would modify the pre-outcome control selection and create an avoidable post-outcome researcher degree of freedom.

Therefore:

> **The original structural control risk set remains frozen.**

The missing observations are handled as missing data within that frozen design, not by constructing a new control pool.

---

## 6. Primary execution rule

The primary analysis will use an **available-observation execution of the original frozen model**.

The original primary model remains:

\[
Y_{et} \sim \operatorname{Poisson}(\mu_{et})
\]

\[
\log(\mu_{et})
=
\alpha_e
+
\gamma_t
+
\beta(Treated_e \times Post_t)
+
\log(Exposure_{et})
\]

with:

- institutional event fixed effects `α_e`;
- unrestricted calendar-year fixed effects `γ_t`;
- the frozen treatment × post coefficient `β`;
- annual mean population as the exposure offset.

No zero values will be created for structurally missing municipality-years.

### Event-year aggregation

Municipality-level observed counts and exposures continue to be summed to their frozen institutional-event unit.

For municipality-years classified as `STRUCTURAL_REPORTING_ABSENCE`:

- outcome count is missing;
- that municipality's population exposure must **not** remain in the corresponding outcome exposure denominator;
- only municipalities with observed incident-report data contribute count and exposure to that event-year.

This preserves correspondence between observed numerator and exposure.

### Consequence for the two affected events

`EV_SBFF_2007` consists only of Ekerö in the frozen control architecture.

Therefore:

- its clean pre-period observations remain available;
- its 2003 and 2004 outcome observations are unavailable;
- no synthetic post observations are created.

`EV_RSNV_BJUV_2019` consists only of Bjuv.

Therefore:

- its clean pre-period observations remain available;
- its 2003 post observation remains available;
- its 2004 observation is unavailable.

All unaffected events retain their original observations.

---

## 7. Complete-control-event sensitivity

A required data-availability sensitivity analysis will remove both affected control events **entirely from all model years**:

- `EV_SBFF_2007`;
- `EV_RSNV_BJUV_2019`.

The model will then be refitted without any observations from these two events.

This produces a structurally balanced sensitivity in which every retained control event has observed outcome support across all included clean-pre and strict-post years.

No other element of the model may change.

This analysis is labelled:

`COMPLETE_CONTROL_EVENT_SENSITIVITY`

and is secondary to the available-observation primary execution.

---

## 8. Data-availability robustness classification

After both models are executed:

### `DATA_AVAILABILITY_DIRECTION_ROBUST`

if the primary IRR and the complete-control-event sensitivity IRR remain on the same side of 1.

### `DATA_AVAILABILITY_DIRECTION_SENSITIVE`

if the two point estimates fall on opposite sides of 1, or one is exactly 1 to numerical precision.

No new significance threshold or effect-size threshold is introduced.

The full estimates and intervals must be reported regardless of this classification.

---

## 9. Existing item-nonresponse sensitivity remains unchanged

The parent protocol's adversarial sensitivity for `Ej angiven` remains in force exactly as frozen.

It must be run separately from the present structural-reporting-absence sensitivity.

The amendment does not alter the frozen lower-IRR or upper-IRR assignments for item nonresponse.

Reporting must therefore distinguish:

1. uncertainty due to classification-level item nonresponse (`Ej angiven`); and
2. uncertainty due to complete municipality-year reporting absence.

These mechanisms must not be pooled into one generic missingness calculation.

---

## 10. Existing event-dependence robustness remains unchanged

The previously frozen event-dependence analyses remain required.

These include:

- leave-one-treated-event-out refits;
- leave-one-control-event-out refits.

For the available-observation primary execution, the original frozen event set remains the reference set even where an event has incomplete post support.

The complete-control-event sensitivity is an additional predefined analysis and does not replace the original LOCO exercise.

Where a leave-one-control-event-out fit removes an event already contributing no information to part of the post period, this should simply be documented rather than redefined.

---

## 11. No worst-case count bounds

The initial post-unmask QA contemplated bounding a wholly missing municipality-year primary count between:

\[
0
\]

and

\[
N_{\text{all building-fire incidents}}
\]

if the total number of incidents were observable.

MCF has confirmed that no such annual incident total is available for the three affected municipality-years.

Therefore this bounding analysis is **not feasible** and is retired before estimation.

No replacement upper bound will be invented from:

- neighbouring years;
- population rates;
- national averages;
- other municipalities;
- interpolation;
- model prediction;
- or post hoc imputation.

---

## 12. No outcome-informed model modification

The discovery of structural reporting absence does not authorize:

- changing the Poisson specification;
- adding event-specific trends;
- changing the pre-period;
- changing the post-period;
- changing treatment coding;
- selecting a different control set;
- weighting controls according to observed outcomes;
- introducing matching after outcome inspection;
- replacing missing controls with newly selected municipalities;
- changing the primary severity threshold;
- or changing the interpretation standard.

Any future departure from the parent protocol must be documented as a separate amendment with an explicit reason.

---

## 13. Interpretation

The primary available-observation estimate remains an observational difference-in-differences estimate for the frozen historical cohort.

The structural missingness creates an additional limitation:

> Two control events have incomplete strict-post reporting support, while all five treated institutional events retain complete post-period reporting.

This asymmetry must be reported explicitly.

The complete-control-event sensitivity tests whether the estimated treatment direction depends on retaining those incompletely observed control events.

Neither analysis can establish that the missing reporting is statistically ignorable.

The historical reporting system was not designed for this causal study, and absence of submitted reports may correlate with municipal administrative capacity or other institutional characteristics.

Accordingly, reporting completeness remains a substantive measurement limitation.

---

## 14. Required final reporting

The final Historical 2002 Cohort report must now include, in addition to all requirements in the parent protocol:

1. the three structurally missing municipality-years;
2. MCF's confirmation that incident reports are entirely absent;
3. the distinction between structural reporting absence and `Ej angiven`;
4. the available-observation primary estimate;
5. the complete-control-event sensitivity estimate;
6. the `DATA_AVAILABILITY_DIRECTION_ROBUST` or `DATA_AVAILABILITY_DIRECTION_SENSITIVE` classification;
7. explicit confirmation that missing municipality-years were never coded as zero;
8. explicit confirmation that no replacement municipalities were introduced;
9. explicit confirmation that no post-outcome information was used to alter the primary estimator;
10. the caveat that treated post-period reporting is complete while control reporting is not.

These requirements supplement rather than replace the original reporting rules.

---

## 15. Updated execution sequence

The permitted sequence after this amendment is frozen is:

1. preserve the original MCF 2003–2004 extract unchanged;
2. record the three municipality-years as `STRUCTURAL_REPORTING_ABSENCE`;
3. implement the available-observation aggregation rule;
4. implement the complete-control-event sensitivity;
5. preserve all original estimator and robustness specifications;
6. hash/freeze the amended analysis implementation;
7. execute the locked analysis;
8. report all required estimates and sensitivities without post-result model tuning.

No further outcome-based design choice is permitted between steps 6 and 7.

---

## 16. Amendment decision

\[
\boxed{
\textbf{POST-UNMASK DATA AVAILABILITY: RESOLVED WITH PRESPECIFIED AMENDMENT}
}
\]

The historical 2002 replication remains analytically executable.

The three municipality-year reporting losses do not invalidate the cohort, but they require explicit available-observation handling and a complete-control-event sensitivity.

The parent causal estimand and estimator remain frozen and unchanged.

**Analysis status after amendment freeze:**

`AUTHORIZED_FOR_LOCKED_EXECUTION`
