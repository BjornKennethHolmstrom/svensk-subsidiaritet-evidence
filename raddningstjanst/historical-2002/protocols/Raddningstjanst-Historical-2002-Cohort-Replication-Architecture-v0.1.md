# Räddningstjänst — Historical 2002 Cohort Replication Architecture v0.1

**Status:** structural replication architecture frozen; **post-treatment outcome firewall CLOSED**.

## Why this is the next replication

The Uppsala 2012 case produced hypothesis-strengthening but non-confirmatory evidence. The strongest next test is not another sensitivity on Uppsala, but an independent historical cohort in a different reporting period.

The 2002 cohort contains **5 independent exact full-A institutional events / 9 municipalities**:

1. Falköping–Tidaholm — common rescue board
2. Höglandets Räddningstjänstförbund — Nässjö, Vetlanda
3. Nerikes Brandkår — Askersund
4. Skara–Götene — common rescue board
5. Värends Räddningstjänstförbund — Alvesta, Växjö

All nine are exact first-treatment candidates in the locked treatment-history reconstruction.

## Measurement regime

The replication is deliberately bounded to the historical `Insatsrapport-96` regime.

- clean pre: **1998–2000**
- anticipation/buffer: **2001**
- treatment year: **2002**
- strict post: **2003–2004**
- **2005 and later excluded from the strict replication**

Historical Räddningsverket reports use the same arrival-extent categories throughout the period and the 2005 publication explicitly distinguishes the old `Insatsrapport-96` from the new `Insatsrapport-05`.

## Outcome schema

Primary candidate outcome:

`ARRIVAL_BEYOND_START_OBJECT_RATE_PER_100K`

Numerator:
- Brand i ett rum
- Brand i flera rum
- Brand i flera brandceller

Denominator:
- annual mean SCB population, `(P_t + P_t-1)/2`

The interpretation is deliberately different from the Uppsala B20 final-extent outcome: this historical measure captures how far the fire had spread **when the rescue service arrived**, and therefore reflects pre-arrival system performance and incident environment rather than suppression after arrival alone.

Secondary and sensitivity outcomes are locked in `RESCUE_HISTORICAL_ARRIVAL_EXTENT_SCHEMA_v0.1.csv`.

## Structural control risk set

Controls are chosen **before any historical severity outcomes are opened**.

Eligibility:

1. exact future first full-A event in the locked treatment history;
2. first full A **>= 2006**;
3. municipality exists throughout 1998–2004.

Why >=2006 rather than >=2005:

A municipality first treated in 2005 would have 2004 as its own `t-1` year. Because 2004 is part of the replication's strict post window, such a unit could already be in anticipation/implementation and is therefore excluded.

Result:

- **33 municipalities**
- **20 future treatment-event clusters**

Knivsta is excluded because it did not exist throughout the pre-period.

The future event ID is the planned **independence cluster** for controls. This is an analytical clustering device to prevent future multi-municipality mergers from being counted as independent replications; it does not claim that those municipalities were already one organization in 1998–2004.

## Outcome firewall

### OPEN NOW
Only the exact **1998–2000 pre-treatment request list**:
- 42 municipalities total = 9 treated + 33 structural controls
- 126 municipality-years
- arrival-extent categories only

### CLOSED
- 2001 anticipation outcomes
- 2002 treatment-year outcomes
- 2003–2004 strict post outcomes

The closed post request list is already enumerated and hashed, but must not be requested or opened until the pre-treatment feasibility audit is complete and the estimator protocol is frozen.

## What must happen after the pre-treatment extract

The pre-treatment-only audit must determine:

1. archive coverage and category completeness;
2. municipality/event missingness;
3. primary-count sparsity;
4. event-level population exposure;
5. treated-vs-control pre-dynamics;
6. whether an event-level RRR estimator is numerically stable or a count-model formulation is preferable.

Only then should the exact estimator and inference/robustness rules be frozen.

No post-treatment outcome should influence that choice.

## Evidence hierarchy / non-overclaiming

This replication is potentially stronger than Uppsala because it has five independent treatment events rather than one. It is not automatically causal merely because N is larger.

Key remaining threats include:
- heterogeneous formal-A forms (common board vs federation);
- heterogeneous background K cooperation that is incompletely observed historically;
- small event counts;
- non-random selection into 2002 integration;
- historical reporting completeness.

The study should therefore target a replicated **directional institutional signal**, not a universal merger coefficient.

## Source anchors

- Treatment cohort: `RESCUE_TREATMENT_LOCK_CANDIDATES_v0.2.csv`
- Treatment-history reconstruction: `Raddningstjanst-Treatment-History-Reconstruction-v0.2.md`
- Historical measurement-regime lock: `RESCUE_FIRE_MEASUREMENT_REGIMES_v0.1.csv`
- Existing archive request architecture: `MCF_FIRE_ARCHIVE_REQUEST_v0.1.md`

Historical public documentation:
- 1998 `Räddningstjänst i siffror`: https://rib.msb.se/filer/pdf/15051.pdf
- 1999 report: https://rib.msb.se/filer/pdf/16195.pdf
- 2000 report: https://rib.msb.se/filer/pdf/17755.pdf
- 2001 report: https://rib.msb.se/filer/pdf/17796.pdf
- 2002 report: https://rib.msb.se/filer/pdf/18922.pdf
- 2004 / nine-year report: https://rib.msb.se/Filer/pdf/20836.pdf
