# Historical 2002 Cohort — Primary-Rate Pretrend Audit Result v0.1

**Outcome firewall:** PASS — only 1998–2000 fire outcomes were used.  
**SCB denominator:** TAB638 / BE0101N1, 31-Dec stocks, annual mean `(P[t-1]+P[t])/2`.

## Materialization

- SCB stock rows: **168/168**
- annual-mean denominator rows: **126/126**
- municipality-year primary rates: **126/126**
- treated events with complete 3-year rates: **5/5**
- control events with complete 3-year rates: **20/20**

## Population-pooled primary rates per 100,000

| Year | Treated | Control | Treated/control RR |
|---|---:|---:|---:|
| 1998 | 24.7461 | 29.1905 | 0.8477 |
| 1999 | 24.0479 | 33.5749 | 0.7162 |
| 2000 | 18.2259 | 20.0814 | 0.9076 |

Log-linear treated/control RR slope: **+0.034114 per year**  
Direction: **POSITIVE**

## Event-equal slope diagnostic

- mean treated event slope: **-4.0406 per 100k/year**
- mean control event slope: **+0.2807**
- treated minus control slope gap: **-4.3214**
- exact 5-of-25 descriptive permutation tail fraction: **0.3595** over **53,130** allocations

The permutation number is a *descriptive rank diagnostic only*. Treatment was not randomized and this is not a causal/randomization p-value.

## Missingness sensitivity

Worst-case annual treated/control RR bounds:

| Year | Lower | Observed | Upper |
|---|---:|---:|---:|
| 1998 | 0.8043 | 0.8477 | 1.4512 |
| 1999 | 0.6920 | 0.7162 | 0.7162 |
| 2000 | 0.9057 | 0.9076 | 0.9076 |

Observed log-RR slope: **+0.034114**  
Lower-bound trajectory slope: **+0.059359**  
Upper-bound trajectory slope: **-0.234678**

Classification: **MISSINGNESS_CAN_CHANGE_RELATIVE_TREND_DIRECTION**

## Methodological interpretation

No binary parallel-trends pass/fail rule is applied. With only three clean pre years, the audit is used to characterize:

1. relative pre-period direction;
2. dispersion across independent institutional events;
3. sensitivity to the concentrated 1998 missingness.

All ingredients required for a separate **Estimator & Analysis Protocol Freeze** are now available without opening post outcomes.

**2001–2004 remain closed.**
