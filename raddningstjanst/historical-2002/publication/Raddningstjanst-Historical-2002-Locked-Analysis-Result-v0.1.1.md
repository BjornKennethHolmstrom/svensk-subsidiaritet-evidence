# Historical 2002 Cohort — Locked Analysis Result v0.1.1

Primary execution: **AVAILABLE_OBSERVATION** under `Historical 2002 Cohort — Post-Unmask Data-Availability Amendment v0.1`.

Primary IRR: **1.9530** (ABOVE_1)

Pearson-scaled model interval: **1.2165–3.1355**
Event-cluster sandwich interval: **1.1620–3.2827**

## Post-unmask data availability

- structural reporting absence: **0125-2003; 0125-2004; 1260-2004**
- missing municipality-years coded as zero: **NO**
- corresponding population exposure retained: **NO**
- replacement control municipalities introduced: **NO**
- complete-control-event sensitivity drops: **EV_RSNV_BJUV_2019; EV_SBFF_2007**
- complete-control-event sensitivity IRR: **1.9484** (ABOVE_1)
- data availability: **DATA_AVAILABILITY_DIRECTION_ROBUST**

## Frozen robustness checks

- pre-window: **PREWINDOW_DIRECTION_ROBUST**
- item nonresponse (`Ej angiven`): **MISSINGNESS_DIRECTION_ROBUST** (1.5339–2.0184)
- leave-one-treated: **TREATED_EVENT_DIRECTION_ROBUST**
- leave-one-control: **CONTROL_EVENT_DIRECTION_ROBUST**

No binary p<0.05 success/failure rule is used. 2001 and 2002 are excluded from the causal model. The primary estimator and estimand are unchanged from the pre-unmask frozen protocol.
