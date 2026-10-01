#!/usr/bin/env python3
"""Historical 2002 Cohort — Locked Analysis Runner v0.1.1.

Parent statistical protocol frozen before 2003–2004 outcome unmasking.
This implementation incorporates only the subsequently frozen
Post-Unmask Data-Availability Amendment v0.1:

- Ekerö 2003, Ekerö 2004 and Bjuv 2004 are STRUCTURAL_REPORTING_ABSENCE.
- Those municipality-years are never converted to zero.
- Their population exposure is excluded together with the unavailable outcome.
- The original structural control pool is retained; no replacements are allowed.
- A required COMPLETE_CONTROL_EVENT_SENSITIVITY drops EV_SBFF_2007 and
  EV_RSNV_BJUV_2019 from all model years.
- The original estimator, outcome definitions, pre/post windows, item-nonresponse
  bounds, LOTO/LOCO and legal-form analyses remain unchanged.

Dependencies: numpy, requests.
Input --post-file remains the normalized long-form CSV used by v0.1, with columns
municipality_code, year, extent_category, count. Blank count cells are permitted
only for the three frozen structural-reporting-absence municipality-years.
"""

import argparse
import csv
import hashlib
import itertools
import json
import math
import os
import time
import zipfile
from collections import defaultdict

import numpy as np
import requests


PRE_PANEL = 'RESCUE_HISTORICAL_2002_PRETREATMENT_PANEL_WITH_RATE_v0.1.csv'
TREATED = 'RESCUE_HISTORICAL_2002_TREATMENT_COHORT_v0.1.csv'
CONTROLS = 'RESCUE_HISTORICAL_2002_CONTROL_RISK_SET_v0.1.csv'
POST_REQUEST = 'RESCUE_HISTORICAL_2002_PRIMARY_POST_UNMASK_REQUESTS_v0.1.csv'

OUT_EST = 'RESCUE_HISTORICAL_2002_LOCKED_ESTIMATES_v0.1.1.csv'
OUT_EVENT = 'RESCUE_HISTORICAL_2002_EVENT_PERIOD_RESULTS_v0.1.1.csv'
OUT_QA = 'RESCUE_HISTORICAL_2002_POST_QA_v0.1.1.csv'
OUT_RESULT = 'Raddningstjanst-Historical-2002-Locked-Analysis-Result-v0.1.1.md'
OUT_MAN = 'RESCUE_HISTORICAL_2002_LOCKED_ANALYSIS_RESULT_MANIFEST_v0.1.1.json'
OUT_ZIP = 'raddningstjanst-historical-2002-locked-analysis-result-v0.1.1.zip'

AMENDMENT_VERSION = 'Historical 2002 Cohort — Post-Unmask Data-Availability Amendment v0.1'
SCB_V2 = 'https://statistikdatabasen.scb.se/api/v2/tables/TAB638/data?lang=sv&outputFormat=json-stat2'

CATS = [
    'Ej angiven',
    'Endast rökutveckling',
    'I startföremålet',
    'I startutrymmet',
    'I flera rum',
    'I flera brandceller',
    'Branden släckt/slocknad',
]
PRIMARY = {'I startutrymmet', 'I flera rum', 'I flera brandceller'}
S1 = {'I flera rum', 'I flera brandceller'}
S2 = {'I flera brandceller'}

PRE = {1998, 1999, 2000}
POST = {2003, 2004}
MODEL_YEARS = PRE | POST

# Frozen after post-unmask clarification from MCF, before estimation.
STRUCTURAL_REPORTING_ABSENCE = {
    ('0125', 2003),  # Ekerö
    ('0125', 2004),  # Ekerö
    ('1260', 2004),  # Bjuv
}
COMPLETE_CONTROL_EVENT_DROP = {
    'EV_SBFF_2007',
    'EV_RSNV_BJUV_2019',
}


def read_csv(path):
    with open(path, encoding='utf-8-sig', newline='') as f:
        return list(csv.DictReader(f))


def write_csv(path, rows):
    fields = []
    for r in rows:
        for k in r:
            if k not in fields:
                fields.append(k)
    with open(path, 'w', encoding='utf-8', newline='') as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, '') for k in fields})


def code(x):
    return str(x).strip().zfill(4)


def sha(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest()


def parse_count(value):
    """Parse an observed count, preserving blank as None.

    Spreadsheet-to-CSV exports often render integer counts as e.g. ``0.0``;
    these are accepted only when they are exactly integer-valued.
    """
    s = '' if value is None else str(value).strip()
    if s == '':
        return None
    try:
        v = float(s)
    except ValueError as e:
        raise RuntimeError(f'Non-numeric count value {value!r}') from e
    if not math.isfinite(v) or v < 0 or abs(v - round(v)) > 1e-9:
        raise RuntimeError(f'Count must be a nonnegative integer; got {value!r}')
    return int(round(v))


def direction(irr, tol=1e-12):
    if abs(irr - 1.0) <= tol:
        return 'AT_1'
    return 'BELOW_1' if irr < 1 else 'ABOVE_1'


def jsonstat2_rows(ds):
    ids = ds['id']
    dims = ds['dimension']
    vals = ds['value']
    levels = []
    for d in ids:
        idx = dims[d]['category']['index']
        levels.append(
            [k for k, v in sorted(idx.items(), key=lambda z: z[1])]
            if isinstance(idx, dict)
            else list(idx)
        )
    vm = {i: v for i, v in enumerate(vals)} if isinstance(vals, list) else {int(k): v for k, v in vals.items()}
    for i, cmb in enumerate(itertools.product(*levels)):
        r = {d: c for d, c in zip(ids, cmb)}
        r['value'] = vm.get(i)
        yield r


def fetch_post_pop(codes):
    body = {
        'selection': [
            {'variableCode': 'Region', 'valueCodes': sorted(codes)},
            {'variableCode': 'ContentsCode', 'valueCodes': ['BE0101N1']},
            {'variableCode': 'Tid', 'valueCodes': ['2002', '2003', '2004']},
        ]
    }
    for a in range(6):
        r = requests.post(SCB_V2, json=body, timeout=60)
        if r.status_code != 429:
            break
        time.sleep(min(5 * 2**a, 60))
    r.raise_for_status()
    stocks = {}
    for x in jsonstat2_rows(r.json()):
        c = str(x['Region'])
        y = int(x['Tid'])
        if c in codes and y in (2002, 2003, 2004):
            stocks[(c, y)] = float(x['value'])
    if len(stocks) != 3 * len(codes):
        raise RuntimeError('Incomplete SCB 2002–2004 population grid')
    return stocks


def design(rows):
    events = sorted({r['event_id'] for r in rows})
    years = sorted({int(r['year']) for r in rows})
    base = years[0]
    cols = [f'EV:{e}' for e in events] + [f'YEAR:{y}' for y in years if y != base] + ['TREATED_X_POST']
    X = []
    for r in rows:
        y = int(r['year'])
        x = [float(r['event_id'] == e) for e in events]
        x += [float(y == yy) for yy in years if yy != base]
        x += [float(r['role'] == 'TREATED' and y in POST)]
        X.append(x)
    return np.asarray(X, float), cols


def fit(rows, outcome):
    if not rows:
        raise RuntimeError('Cannot fit model with zero rows')
    if any(float(r['population']) <= 0 for r in rows):
        raise RuntimeError('All included population exposures must be positive')

    X, cols = design(rows)
    y = np.asarray([float(r[outcome]) for r in rows])
    off = np.log(np.asarray([float(r['population']) for r in rows]))
    b = np.zeros(X.shape[1])

    for _ in range(150):
        eta = off + X @ b
        mu = np.exp(np.clip(eta, -30, 30))
        z = eta + (y - mu) / np.maximum(mu, 1e-12)
        A = (X.T * mu) @ X
        rhs = (X.T * mu) @ (z - off)
        nb = np.linalg.lstsq(A, rhs, rcond=None)[0]
        if np.max(np.abs(nb - b)) < 1e-10:
            b = nb
            break
        b = nb

    mu = np.exp(np.clip(off + X @ b, -30, 30))
    bread = np.linalg.pinv((X.T * mu) @ X)
    df = max(len(y) - np.linalg.matrix_rank(X), 1)
    phi = max(np.sum((y - mu) ** 2 / np.maximum(mu, 1e-12)) / df, 1e-12)
    cov_m = bread * phi

    clusters = [r['event_id'] for r in rows]
    meat = np.zeros_like(bread)
    for g in sorted(set(clusters)):
        ix = [i for i, v in enumerate(clusters) if v == g]
        score = X[ix].T @ (y[ix] - mu[ix])
        meat += np.outer(score, score)

    G = len(set(clusters))
    N = len(y)
    p = np.linalg.matrix_rank(X)
    if G <= 1:
        raise RuntimeError('Event-cluster sandwich requires at least two clusters')
    corr = (G / (G - 1)) * ((N - 1) / max(N - p, 1))
    cov_c = bread @ meat @ bread * corr

    j = cols.index('TREATED_X_POST')
    beta = b[j]
    sem = math.sqrt(max(cov_m[j, j], 0))
    sec = math.sqrt(max(cov_c[j, j], 0))
    return {
        'beta': beta,
        'irr': math.exp(beta),
        'dispersion_phi': phi,
        'model_ci_low': math.exp(beta - 1.96 * sem),
        'model_ci_high': math.exp(beta + 1.96 * sem),
        'cluster_ci_low': math.exp(beta - 1.96 * sec),
        'cluster_ci_high': math.exp(beta + 1.96 * sec),
        'n_event_year_rows': len(rows),
        'n_event_clusters': G,
    }


def safe_rate(count, exposure):
    return count / exposure * 1e5 if exposure > 0 else ''


def safe_within_event_irr(pre_count, pre_exposure, post_count, post_exposure):
    if pre_count <= 0 or pre_exposure <= 0 or post_exposure <= 0:
        return ''
    return (post_count / post_exposure) / (pre_count / pre_exposure)


def self_test():
    assert parse_count('') is None
    assert parse_count(None) is None
    assert parse_count('0') == 0
    assert parse_count('12.0') == 12
    try:
        parse_count('1.5')
        raise AssertionError('fractional count should fail')
    except RuntimeError:
        pass
    assert STRUCTURAL_REPORTING_ABSENCE == {('0125', 2003), ('0125', 2004), ('1260', 2004)}
    assert COMPLETE_CONTROL_EVENT_DROP == {'EV_SBFF_2007', 'EV_RSNV_BJUV_2019'}
    assert direction(0.9) == 'BELOW_1'
    assert direction(1.1) == 'ABOVE_1'
    assert direction(1.0) == 'AT_1'
    print('SELF-TEST PASS')
    print('Model years: 1998,1999,2000,2003,2004')
    print('2001/2002 excluded: PASS')
    print('Structural reporting absence: Ekerö 2003; Ekerö 2004; Bjuv 2004')
    print('No-zero-imputation rule: PASS')
    print('Complete-control-event sensitivity: EV_SBFF_2007; EV_RSNV_BJUV_2019')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--post-file')
    ap.add_argument('--self-test', action='store_true')
    a = ap.parse_args()

    if a.self_test:
        self_test()
        return
    if not a.post_file:
        raise SystemExit('--post-file required')

    for p in [PRE_PANEL, TREATED, CONTROLS, POST_REQUEST]:
        if not os.path.exists(p):
            raise RuntimeError(f'Missing frozen input: {p}')

    pre = read_csv(PRE_PANEL)
    treated = read_csv(TREATED)
    controls = read_csv(CONTROLS)
    req = read_csv(POST_REQUEST)
    raw = read_csv(a.post_file)

    expected = {(code(r['municipality_code']), int(r['year'])) for r in req}
    if len(expected) != 84 or {y for c, y in expected} != {2003, 2004}:
        raise RuntimeError('Frozen post whitelist invalid')
    if not STRUCTURAL_REPORTING_ABSENCE.issubset(expected):
        raise RuntimeError('Amendment structural-reporting-absence keys are not all in frozen whitelist')
    if {int(r['year']) for r in raw} != {2003, 2004}:
        raise RuntimeError('Post file must contain only 2003–2004')
    if len(raw) != len(expected) * len(CATS):
        raise RuntimeError(f'Post file must contain exactly {len(expected) * len(CATS)} category rows; got {len(raw)}')

    d = defaultdict(dict)
    for r in raw:
        k = (code(r['municipality_code']), int(r['year']))
        cat = r['extent_category'].strip()
        if k not in expected:
            raise RuntimeError(f'Unexpected post key {k}')
        if cat not in CATS:
            raise RuntimeError(f'Unexpected category {cat}')
        if cat in d[k]:
            raise RuntimeError(f'Duplicate category {k} {cat}')
        d[k][cat] = parse_count(r.get('count'))

    qa = []
    qa_failures = []
    for k in sorted(expected):
        missing_categories = sorted(set(CATS) - set(d.get(k, {})))
        values = [d.get(k, {}).get(cat) for cat in CATS]
        blank_count_cells = sum(v is None for v in values)
        expected_absence = k in STRUCTURAL_REPORTING_ABSENCE

        if missing_categories:
            availability = 'INVALID_MISSING_CATEGORY_ROWS'
            qa_status = 'FAIL'
        elif expected_absence and blank_count_cells == len(CATS):
            availability = 'STRUCTURAL_REPORTING_ABSENCE'
            qa_status = 'PASS'
        elif expected_absence:
            availability = 'INVALID_EXPECTED_ABSENCE_NOT_FULLY_BLANK'
            qa_status = 'FAIL'
        elif blank_count_cells == 0:
            availability = 'OBSERVED'
            qa_status = 'PASS'
        else:
            availability = 'INVALID_PARTIAL_OR_UNEXPECTED_BLANK_COUNTS'
            qa_status = 'FAIL'

        rec = {
            'municipality_code': k[0],
            'year': k[1],
            'qa_status': qa_status,
            'data_availability_status': availability,
            'blank_count_cells': blank_count_cells,
            'missing_categories': ';'.join(missing_categories),
            'expected_structural_absence': 'YES' if expected_absence else 'NO',
        }
        qa.append(rec)
        if qa_status != 'PASS':
            qa_failures.append(rec)

    write_csv(OUT_QA, qa)
    if qa_failures:
        raise RuntimeError(f'Post QA failed for {len(qa_failures)} municipality-years; see {OUT_QA}')

    observed_post_keys = expected - STRUCTURAL_REPORTING_ABSENCE
    actual_structural = {
        (r['municipality_code'], int(r['year']))
        for r in qa
        if r['data_availability_status'] == 'STRUCTURAL_REPORTING_ABSENCE'
    }
    if actual_structural != STRUCTURAL_REPORTING_ABSENCE:
        raise RuntimeError('Observed structural reporting absence does not exactly match frozen amendment')
    if len(observed_post_keys) != 81:
        raise RuntimeError('Amended post coverage must be exactly 81 observed municipality-years')

    codes = {c for c, y in expected}
    stocks = fetch_post_pop(codes)
    pops = {(c, 2003): (stocks[c, 2002] + stocks[c, 2003]) / 2 for c in codes}
    pops.update({(c, 2004): (stocks[c, 2003] + stocks[c, 2004]) / 2 for c in codes})

    role_event = {}
    legal = {}
    for r in treated:
        role_event[code(r['municipality_code'])] = ('TREATED', r['event_id'])
        legal[r['event_id']] = r['legal_form']
    for r in controls:
        role_event[code(r['municipality_code'])] = ('CONTROL', r['future_event_id'])

    if set(role_event) != codes:
        missing_map = sorted(codes - set(role_event))
        extra_map = sorted(set(role_event) - codes)
        raise RuntimeError(f'Role/event map mismatch. Missing={missing_map}, extra={extra_map}')

    # Amendment invariants: all structurally missing post observations are controls,
    # and map to exactly the two frozen sensitivity-drop events.
    missing_events = set()
    for c, y in STRUCTURAL_REPORTING_ABSENCE:
        role, event = role_event[c]
        if role != 'CONTROL':
            raise RuntimeError(f'Structural reporting absence unexpectedly belongs to treated unit: {(c, y)}')
        missing_events.add(event)
    if missing_events != COMPLETE_CONTROL_EVENT_DROP:
        raise RuntimeError(f'Amendment event mapping mismatch: {missing_events}')

    mun = []
    for r in pre:
        mun.append({
            'municipality_code': code(r['municipality_code']),
            'year': int(r['year']),
            'role': r['role'],
            'event_id': r['event_id'],
            'population': float(r['mean_population']),
            'primary_n': int(r['primary_beyond_start_object_n']),
            's1_n': int(r['beyond_one_room_n']),
            's2_n': int(r['multi_firecell_n']),
            'all_n': int(r['all_extent_n']),
            'missing_n': int(r['extent_missing_n']),
            'valid_n': int(r['valid_extent_n']),
        })

    # Available-observation execution: structurally absent municipality-years are
    # omitted entirely, so their population exposure is omitted with their outcome.
    for c, y in sorted(observed_post_keys):
        v = d[c, y]
        if any(v[x] is None for x in CATS):
            raise RuntimeError(f'Observed post key contains blank count after QA: {(c, y)}')
        role, event = role_event[c]
        mun.append({
            'municipality_code': c,
            'year': y,
            'role': role,
            'event_id': event,
            'population': pops[c, y],
            'primary_n': sum(v[x] for x in PRIMARY),
            's1_n': sum(v[x] for x in S1),
            's2_n': sum(v[x] for x in S2),
            'all_n': sum(v.values()),
            'missing_n': v['Ej angiven'],
            'valid_n': sum(v[x] for x in CATS if x != 'Ej angiven'),
        })

    agg = defaultdict(lambda: defaultdict(float))
    for r in mun:
        if r['year'] not in MODEL_YEARS:
            raise RuntimeError('Outcome firewall/model-year violation')
        k = (r['role'], r['event_id'], r['year'])
        for f in ['population', 'primary_n', 's1_n', 's2_n', 'all_n', 'missing_n', 'valid_n']:
            agg[k][f] += r[f]

    rows = [{'role': role, 'event_id': e, 'year': y, **v} for (role, e, y), v in sorted(agg.items())]

    treated_events = sorted({r['event_id'] for r in rows if r['role'] == 'TREATED'})
    control_events = sorted({r['event_id'] for r in rows if r['role'] == 'CONTROL'})
    if len(treated_events) != 5:
        raise RuntimeError(f'Expected 5 treated events; got {len(treated_events)}')
    if len(control_events) != 20:
        raise RuntimeError(f'Expected 20 frozen control events; got {len(control_events)}')

    estimates = []
    primary = fit(rows, 'primary_n')
    estimates.append({'analysis': 'PRIMARY', 'execution': 'AVAILABLE_OBSERVATION', 'outcome': 'primary_n', **primary})

    for label, key in [
        ('S1_BEYOND_ONE_ROOM', 's1_n'),
        ('S2_MULTI_FIRECELL', 's2_n'),
        ('QA_ALL_RECORDS', 'all_n'),
    ]:
        estimates.append({'analysis': label, 'outcome': key, **fit(rows, key)})

    for label, keep in [
        ('PW1_ENDPOINTS_ONLY', {1998, 2000, 2003, 2004}),
        ('PW2_LATEST_PRE', {2000, 2003, 2004}),
    ]:
        estimates.append({
            'analysis': label,
            'outcome': 'primary_n',
            **fit([r for r in rows if r['year'] in keep], 'primary_n'),
        })

    # Existing frozen item-nonresponse (Ej angiven) adversarial bounds.
    low = []
    high = []
    for r in rows:
        lo = dict(r)
        hi = dict(r)
        ispre = r['year'] in PRE
        ispost = r['year'] in POST
        ist = r['role'] == 'TREATED'
        if (ist and ispre) or ((not ist) and ispost):
            lo['primary_n'] += r['missing_n']
        if (ist and ispost) or ((not ist) and ispre):
            hi['primary_n'] += r['missing_n']
        low.append(lo)
        high.append(hi)
    lr = fit(low, 'primary_n')['irr']
    hr = fit(high, 'primary_n')['irr']
    blo, bhi = min(lr, hr), max(lr, hr)
    estimates.append({
        'analysis': 'MISSINGNESS_BOUND',
        'outcome': 'primary_n',
        'irr_low_bound': blo,
        'irr_high_bound': bhi,
    })

    # Required amendment sensitivity: remove both affected singleton control events
    # from every pre and post model year. No replacement controls are introduced.
    complete_control_rows = [r for r in rows if r['event_id'] not in COMPLETE_CONTROL_EVENT_DROP]
    data_availability_sens = fit(complete_control_rows, 'primary_n')
    estimates.append({
        'analysis': 'COMPLETE_CONTROL_EVENT_SENSITIVITY',
        'dropped_events': ';'.join(sorted(COMPLETE_CONTROL_EVENT_DROP)),
        'outcome': 'primary_n',
        **data_availability_sens,
    })

    # Existing frozen event-dependence robustness.
    for e in treated_events:
        estimates.append({
            'analysis': 'LOTO_TREATED',
            'dropped_event': e,
            'outcome': 'primary_n',
            **fit([r for r in rows if r['event_id'] != e], 'primary_n'),
        })
    for e in control_events:
        estimates.append({
            'analysis': 'LOCO_CONTROL',
            'dropped_event': e,
            'outcome': 'primary_n',
            **fit([r for r in rows if r['event_id'] != e], 'primary_n'),
        })

    for form in ['COMMON_BOARD', 'KOMMUNALFORBUND']:
        subset = {e for e, v in legal.items() if v == form}
        estimates.append({
            'analysis': 'LEGAL_FORM_DESCRIPTIVE',
            'legal_form': form,
            'outcome': 'primary_n',
            **fit([r for r in rows if r['role'] == 'CONTROL' or r['event_id'] in subset], 'primary_n'),
        })

    ev = []
    for role, e in sorted({(r['role'], r['event_id']) for r in rows}):
        a_pre = [r for r in rows if r['role'] == role and r['event_id'] == e and r['year'] in PRE]
        b_post = [r for r in rows if r['role'] == role and r['event_id'] == e and r['year'] in POST]
        cp = sum(r['primary_n'] for r in a_pre)
        ep = sum(r['population'] for r in a_pre)
        cq = sum(r['primary_n'] for r in b_post)
        eq = sum(r['population'] for r in b_post)
        post_years = sorted({int(r['year']) for r in b_post})
        ev.append({
            'role': role,
            'event_id': e,
            'pre_count': cp,
            'pre_exposure': ep,
            'post_count': cq if b_post else '',
            'post_exposure': eq if b_post else '',
            'pre_years_observed': ';'.join(map(str, sorted({int(r['year']) for r in a_pre}))),
            'post_years_observed': ';'.join(map(str, post_years)),
            'post_window_complete': 'YES' if set(post_years) == POST else 'NO',
            'pre_rate_per_100k': safe_rate(cp, ep),
            'post_rate_per_100k': safe_rate(cq, eq),
            'within_event_irr': safe_within_event_irr(cp, ep, cq, eq),
        })

    write_csv(OUT_EVENT, ev)
    write_csv(OUT_EST, estimates)

    p = primary['irr']
    primary_direction = direction(p)
    same = lambda x: direction(x) == primary_direction and primary_direction != 'AT_1'

    pw = [r['irr'] for r in estimates if r['analysis'].startswith('PW')]
    loto = [r['irr'] for r in estimates if r['analysis'] == 'LOTO_TREATED']
    loco = [r['irr'] for r in estimates if r['analysis'] == 'LOCO_CONTROL']

    preflag = 'PREWINDOW_DIRECTION_ROBUST' if all(map(same, pw)) else 'PREWINDOW_SENSITIVE'
    ltflag = 'TREATED_EVENT_DIRECTION_ROBUST' if all(map(same, loto)) else 'TREATED_EVENT_SENSITIVE'
    lcflag = 'CONTROL_EVENT_DIRECTION_ROBUST' if all(map(same, loco)) else 'CONTROL_EVENT_SENSITIVE'
    missflag = 'MISSINGNESS_DIRECTION_ROBUST' if (bhi < 1 or blo > 1) else 'MISSINGNESS_DIRECTION_NOT_ROBUST'

    da_irr = data_availability_sens['irr']
    daflag = (
        'DATA_AVAILABILITY_DIRECTION_ROBUST'
        if direction(p) == direction(da_irr) and direction(p) in {'BELOW_1', 'ABOVE_1'}
        else 'DATA_AVAILABILITY_DIRECTION_SENSITIVE'
    )

    structural_text = '; '.join(f'{c}-{y}' for c, y in sorted(STRUCTURAL_REPORTING_ABSENCE))
    dropped_text = '; '.join(sorted(COMPLETE_CONTROL_EVENT_DROP))

    report = f'''# Historical 2002 Cohort — Locked Analysis Result v0.1.1

Primary execution: **AVAILABLE_OBSERVATION** under `{AMENDMENT_VERSION}`.

Primary IRR: **{p:.4f}** ({primary_direction})

Pearson-scaled model interval: **{primary['model_ci_low']:.4f}–{primary['model_ci_high']:.4f}**
Event-cluster sandwich interval: **{primary['cluster_ci_low']:.4f}–{primary['cluster_ci_high']:.4f}**

## Post-unmask data availability

- structural reporting absence: **{structural_text}**
- missing municipality-years coded as zero: **NO**
- corresponding population exposure retained: **NO**
- replacement control municipalities introduced: **NO**
- complete-control-event sensitivity drops: **{dropped_text}**
- complete-control-event sensitivity IRR: **{da_irr:.4f}** ({direction(da_irr)})
- data availability: **{daflag}**

## Frozen robustness checks

- pre-window: **{preflag}**
- item nonresponse (`Ej angiven`): **{missflag}** ({blo:.4f}–{bhi:.4f})
- leave-one-treated: **{ltflag}**
- leave-one-control: **{lcflag}**

No binary p<0.05 success/failure rule is used. 2001 and 2002 are excluded from the causal model. The primary estimator and estimand are unchanged from the pre-unmask frozen protocol.
'''
    with open(OUT_RESULT, 'w', encoding='utf-8') as f:
        f.write(report)

    files = [OUT_EST, OUT_EVENT, OUT_QA, OUT_RESULT]
    manifest = {
        'version': 'RESCUE_HISTORICAL_2002_LOCKED_ANALYSIS_RESULT_v0.1.1',
        'parent_protocol': 'Raddningstjanst-Historical-2002-Estimator-Analysis-Protocol-v0.1',
        'data_availability_amendment': AMENDMENT_VERSION,
        'execution': 'AVAILABLE_OBSERVATION',
        'primary_irr': p,
        'complete_control_event_sensitivity_irr': da_irr,
        'structural_reporting_absence': [
            {'municipality_code': c, 'year': y} for c, y in sorted(STRUCTURAL_REPORTING_ABSENCE)
        ],
        'complete_control_event_drop': sorted(COMPLETE_CONTROL_EVENT_DROP),
        'no_zero_imputation': True,
        'missing_exposure_excluded': True,
        'replacement_controls_introduced': False,
        'flags': {
            'data_availability': daflag,
            'prewindow': preflag,
            'missingness_item_nonresponse': missflag,
            'loto': ltflag,
            'loco': lcflag,
        },
        'inputs': {
            PRE_PANEL: {'sha256': sha(PRE_PANEL), 'bytes': os.path.getsize(PRE_PANEL)},
            TREATED: {'sha256': sha(TREATED), 'bytes': os.path.getsize(TREATED)},
            CONTROLS: {'sha256': sha(CONTROLS), 'bytes': os.path.getsize(CONTROLS)},
            POST_REQUEST: {'sha256': sha(POST_REQUEST), 'bytes': os.path.getsize(POST_REQUEST)},
            os.path.basename(a.post_file): {'sha256': sha(a.post_file), 'bytes': os.path.getsize(a.post_file)},
        },
        'runner': {
            'filename': os.path.basename(__file__),
            'sha256': sha(__file__) if os.path.exists(__file__) else None,
        },
        'files': {x: {'sha256': sha(x), 'bytes': os.path.getsize(x)} for x in files},
    }
    with open(OUT_MAN, 'w', encoding='utf-8') as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)

    with zipfile.ZipFile(OUT_ZIP, 'w', zipfile.ZIP_DEFLATED) as z:
        for x in files + [OUT_MAN]:
            z.write(x, arcname=os.path.basename(x))

    print(report)
    print('Saved', OUT_ZIP)


if __name__ == '__main__':
    main()
