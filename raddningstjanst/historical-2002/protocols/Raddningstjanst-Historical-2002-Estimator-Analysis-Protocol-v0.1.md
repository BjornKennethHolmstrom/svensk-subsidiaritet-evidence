# Räddningstjänst — Historical 2002 Cohort
## Estimator & Analysis Protocol Freeze v0.1

**Status:** FROZEN BEFORE POST-OUTCOME UNMASKING  
**Outcome firewall:** 2003–2004 CLOSED at protocol creation.

## Causal question

For the five exact Swedish rescue-service institutional transitions entering full formal authority pooling in 2002, what was the short-run change in the population rate of building fires that had spread beyond the start object at rescue-service arrival, relative to structurally eligible future-treated systems that remained without full A through 2004?

## Analysis unit and support

The independence unit is the institutional event/system, not the municipality.

- Treated: 5 exact 2002 events / 9 municipalities.
- Controls: 20 future-treatment event clusters / 33 municipalities.
- Municipal counts and mean-population exposures are summed within event-year.

## Time lock

- Clean pre: 1998, 1999, 2000.
- Excluded anticipation/implementation: 2001, 2002.
- Strict post: 2003, 2004.
- 2005 and later excluded from the strict replication because of the reporting-form revision.

2001 and 2002 do not enter the primary causal model.

## Primary outcome

`ARRIVAL_BEYOND_START_OBJECT_RATE_PER_100K`

Primary numerator:
- Brand i ett rum (`I startutrymmet` in the database);
- Brand i flera rum;
- Brand i flera brandceller.

`Ej angiven` is item nonresponse, not a severity category.

Exposure is annual mean population:
`M_t = (P_(t-1)+P_t)/2`, SCB TAB638 / BE0101N1.

## Primary estimator

For institutional event `e` and included calendar year `t`:

`Y_et ~ Poisson(mu_et)`

`log(mu_et) = alpha_e + gamma_t + beta*(Treated_e × Post_t) + log(Exposure_et)`

where `alpha_e` are event fixed effects and `gamma_t` unrestricted calendar-year fixed effects.

Primary effect: `IRR = exp(beta)`.

- IRR < 1 = treated-favorable relative change.
- IRR > 1 = treated-adverse relative change.

No event-specific linear trend is included in the primary model.

## Uncertainty

No `p < .05` success/failure rule is permitted.

Required:
1. Pearson-dispersion-scaled Poisson 95% model interval, labelled a count-process/model interval rather than a full causal-confidence interval.
2. Event-cluster sandwich 95% interval as secondary robustness, with an explicit few-treated-cluster caveat.

## Pre-window sensitivities

PW1: endpoints-only pre = 1998 + 2000; post = 2003–2004.  
PW2: latest-clean-pre = 2000 only; post = 2003–2004.

If primary, PW1 and PW2 point estimates stay on the same side of 1:
`PREWINDOW_DIRECTION_ROBUST`; otherwise `PREWINDOW_SENSITIVE`.

## Missingness sensitivity

Two adversarial assignments are frozen.

Lower-IRR assignment:
- treated pre missing → primary;
- treated post missing → non-primary;
- control pre missing → non-primary;
- control post missing → primary.

Upper-IRR assignment reverses all four choices.

If the resulting adversarial IRR interval includes 1:
`MISSINGNESS_DIRECTION_NOT_ROBUST`; otherwise `MISSINGNESS_DIRECTION_ROBUST`.

## Event dependence

Five leave-one-treated-event-out refits are required.  
Twenty leave-one-control-event-out refits are required.

Any sign flip across 1 is reported as sensitivity, not hidden by the pooled estimate.

## Secondary outcomes

- Beyond one room rate: several rooms + several fire cells.
- Multi-firecell rate.
- Primary share among valid records.
- All building-fire record rate as reporting/composition QA.
- Missing-share QA.

Secondary severity outcomes are mechanism/coherence evidence and cannot override the primary outcome.

## Legal-form heterogeneity

Common-board treated events (2) and municipal-federation treated events (3) are estimated separately against the full controls as descriptive heterogeneity only. No subgroup significance claim is permitted.

## Final reporting rule

The final report must jointly state:
- primary direction and IRR;
- both intervals and whether they cross 1;
- PW1/PW2 direction;
- adversarial missingness bounds;
- all five LOTO estimates;
- LOCO range;
- secondary severity results;
- legal-form descriptive results;
- pretrend and measurement caveats.

The cohort alone cannot establish a general effect of mergers/common boards/federations.

## Activation

The exact 84 municipality-year 2003–2004 whitelist is frozen in
`RESCUE_HISTORICAL_2002_PRIMARY_POST_UNMASK_REQUESTS_v0.1.csv`.

Post outcomes may be requested/opened only after this protocol manifest is frozen.
