# Historical 2002 Cohort

Den här grenen är en oberoende historisk replication med fem institutionella
first-full-`A` events och nio behandlade kommuner.

## Design

- clean pre: 1998–2000;
- anticipation/implementation excluded: 2001–2002;
- strict post: 2003–2004;
- primary outcome: `ARRIVAL_BEYOND_START_OBJECT_RATE_PER_100K`;
- primary estimator: event-year Poisson DiD med event- och kalenderårs-FE samt
  population offset.

## Läsordning

1. replication architecture;
2. primary-rate pretrend audit;
3. frozen estimator & analysis protocol;
4. post-unmask data-availability amendment;
5. locked analysis result;
6. frozen cohort finding.

## Kataloger

- `publication/` — human-readable audit/result/finding.
- `protocols/` — frozen architecture, estimator protocol and amendment.
- `results/` — compact machine-readable locked output.
- `reproducibility/` — runner and exact frozen inputs included in the source
  package.

Den primära locked runnern kan self-testas lokalt:

```bash
cd reproducibility
python3 run_historical_2002_locked_analysis_v0.1.1.py --self-test
```

För en full rerun används den inkluderade normalized post-filen:

```bash
python3 run_historical_2002_locked_analysis_v0.1.1.py \
  --post-file normalized-2003-2004.csv
```
