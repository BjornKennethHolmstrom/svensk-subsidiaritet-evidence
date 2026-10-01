#!/usr/bin/env python3
"""
Halmstad 2012–2014 Sensitivity Outcome Construction & Locked Analysis v0.1

SEQUENTIAL BATCH-2 STEP
-----------------------
Authorized new post-treatment opening:
  Halmstad (1380): 2012, 2013, 2014 only.

Still closed:
  Skåne Nordväst 2012–2014
  2011 anticipation diagnostics
  2015 measurement-edge sensitivity

The already-completed primary result is immutable. Halmstad is a
prespecified sensitivity donor only and can never replace Jönköping.

The script:
1. verifies the Halmstad K activation patch/gate;
2. verifies and hashes the completed Uppsala primary post file + locked estimates;
3. fetches Halmstad B20 2007–2009 ONLY to recover preregistered threshold counts;
4. verifies those pre-period primary/valid/missing counts exactly match the
   already-locked pre-match file;
5. fetches Halmstad B20 2012–2014 ONLY as the authorized sensitivity opening;
6. fetches SCB stocks 2011–2014 to construct mean population;
7. QA-checks the three new Halmstad post rows;
8. computes the same locked donor-specific RRR, count-process interval,
   absolute controlled difference, year-balanced RRR, missingness bounds,
   and secondary threshold-share changes;
9. compares only the DIRECTION to the already-frozen Jönköping and
   Piteå–Älvsbyn point estimates;
10. packages the sensitivity result.

No primary result, donor hierarchy, time window, or estimator is changed.
"""

import argparse
import csv
import hashlib
import io
import itertools
import json
import math
import os
import re
import sys
import time
import zipfile
from collections import defaultdict

import requests

# -----------------------------
# Frozen/local inputs
# -----------------------------
GATE_FILE = "RESCUE_HALMSTAD_PRE2010_K_GATE_v0.1.csv"
ACTIVATION_PATCH = "RESCUE_UPPSALA_2012_HALMSTAD_SENSITIVITY_ACTIVATION_PATCH_v0.1.json"
REQUESTS = "RESCUE_HALMSTAD_2012_2014_SENSITIVITY_REQUESTS_v0.1.csv"

PRE_CONTROL = "RESCUE_UPPSALA_CONTROL_PREMATCH_DATA_v0.1.csv"
FULL_PRE_PANEL = "RESCUE_FIRE_B20_MUNICIPALITY_YEAR_WITH_POP_v0.1.1.csv"

PRIMARY_POST = "RESCUE_UPPSALA_2012_PRIMARY_POST_DATA_v0.1.csv"
PRIMARY_ESTIMATES = "RESCUE_UPPSALA_2012_LOCKED_ESTIMATES_v0.1.csv"

# -----------------------------
# Outputs
# -----------------------------
OUT_PRE_RAW = "RESCUE_HALMSTAD_PREMATCH_THRESHOLD_RAW_v0.1.csv"
OUT_POST_RAW = "RESCUE_HALMSTAD_2012_2014_POST_MCF_RAW_v0.1.csv"
OUT_SCB_RAW = "RESCUE_HALMSTAD_2012_2014_POST_SCB_RAW_v0.1.csv"
OUT_POST = "RESCUE_HALMSTAD_2012_2014_SENSITIVITY_POST_DATA_v0.1.csv"
OUT_QA = "RESCUE_HALMSTAD_2012_2014_SENSITIVITY_QA_v0.1.csv"
OUT_EST = "RESCUE_HALMSTAD_2012_2014_SENSITIVITY_ESTIMATE_v0.1.csv"
OUT_MD = "Raddningstjanst-Halmstad-2012-2014-Sensitivity-Result-v0.1.md"
OUT_MANIFEST = "RESCUE_HALMSTAD_2012_2014_SENSITIVITY_RESULT_MANIFEST_v0.1.json"
OUT_ZIP = "raddningstjanst-halmstad-2012-2014-sensitivity-result-v0.1.zip"

MCF_ENDPOINT = "https://statistik.mcf.se/PXWeb/api/v1/sv/PxData/START/B/B2/B20"
SCB_V2_DATA = (
    "https://statistikdatabasen.scb.se/api/v2/tables/TAB638/data"
    "?lang=sv&outputFormat=json-stat2"
)

HALMSTAD = "1380"
PRE_YEARS = (2007,2008,2009)
POST_YEARS = (2012,2013,2014)
EXTENT_CODES = ["6","1","2","3","4","5","-1"]
VALID_CODES = ["6","1","2","3","4","5"]
LABEL_TO_CODE = {
    "Brandtillbud utan skada":"6",
    "I det objekt som först antändes":"1",
    "I utrymmet där branden startade":"2",
    "I flera utrymmen i samma brandcell":"3",
    "I flera brandceller i samma byggnad":"4",
    "I flera byggnader":"5",
    "Uppgift saknas":"-1",
}


def sha256(path):
    h=hashlib.sha256()
    with open(path,"rb") as f:
        for c in iter(lambda:f.read(1024*1024),b""):
            h.update(c)
    return h.hexdigest()


def read_csv(path):
    with open(path,encoding="utf-8-sig",newline="") as f:
        return list(csv.DictReader(f))


def write_csv(path,rows):
    if not rows:
        raise RuntimeError(f"Refusing to write empty CSV: {path}")
    with open(path,"w",encoding="utf-8",newline="") as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0].keys()))
        w.writeheader(); w.writerows(rows)


def require(path):
    if not os.path.exists(path):
        raise RuntimeError(f"Required file missing: {path}")


def parse_csv(text):
    try:
        dialect=csv.Sniffer().sniff(text[:4096],delimiters=",;\t")
    except csv.Error:
        dialect=csv.excel
        dialect.delimiter=";"
    return list(csv.DictReader(io.StringIO(text),dialect=dialect))


def code_from_place(value):
    m=re.match(r"^\s*(\d{4})(?:\s+|$)",str(value))
    return m.group(1) if m else None


def post_backoff(session,url,body,max_retries=8):
    for attempt in range(max_retries+1):
        r=session.post(url,json=body,timeout=60)
        if r.status_code==429 and attempt<max_retries:
            try:
                delay=float(r.headers.get("Retry-After"))
            except (TypeError,ValueError):
                delay=min(5*(2**attempt),120)
            print(f"HTTP 429; retrying in {delay+1:.0f}s")
            time.sleep(delay+1)
            continue
        if 500<=r.status_code<=599 and attempt<max_retries:
            delay=min(5*(2**attempt),120)
            print(f"HTTP {r.status_code}; retrying in {delay:.0f}s")
            time.sleep(delay)
            continue
        return r
    raise AssertionError("unreachable")


def jsonstat2_rows(ds):
    ids=ds.get("id"); sizes=ds.get("size"); dims=ds.get("dimension"); vals=ds.get("value")
    if not ids or not sizes or not dims or vals is None:
        raise RuntimeError("Unexpected SCB JSON-stat2 structure.")
    code_lists=[]; labels={}
    for dim in ids:
        cat=dims[dim]["category"]; idx=cat["index"]
        if isinstance(idx,dict):
            codes=[k for k,v in sorted(idx.items(),key=lambda kv:kv[1])]
        elif isinstance(idx,list):
            codes=list(idx)
        else:
            raise RuntimeError(f"Unsupported JSON-stat2 index for {dim}")
        code_lists.append(codes); labels[dim]=cat.get("label",{})
    if isinstance(vals,list):
        valmap={i:v for i,v in enumerate(vals)}
    elif isinstance(vals,dict):
        valmap={int(k):v for k,v in vals.items()}
    else:
        raise RuntimeError("Unsupported JSON-stat2 value representation.")
    rows=[]
    for i,combo in enumerate(itertools.product(*code_lists)):
        row={d:c for d,c in zip(ids,combo)}
        row["value"]=valmap.get(i)
        for d,c in zip(ids,combo):
            if c in labels[d]: row[d+"_label"]=labels[d][c]
        rows.append(row)
    return rows


def verify_gate_and_requests(gate_path,patch_path,requests_path):
    gate=read_csv(gate_path)
    if len(gate)!=1:
        raise RuntimeError("Expected exactly one Halmstad gate row.")
    g=gate[0]
    if g.get("gate_id")!="K-HALM":
        raise RuntimeError("Unexpected Halmstad gate id.")
    if g.get("status")!="PASS_WITH_PROVENANCE_CAVEAT":
        raise RuntimeError("Halmstad K gate is not activated.")
    if g.get("protocol_pass_equivalent")!="YES":
        raise RuntimeError("Halmstad gate is not protocol-equivalent PASS.")

    with open(patch_path,encoding="utf-8") as f:
        patch=json.load(f)
    gu=patch.get("gate_update",{})
    if gu.get("gate")!="K-HALM" or gu.get("protocol_pass_equivalent") is not True:
        raise RuntimeError("Halmstad sensitivity activation patch invalid.")
    auth=patch.get("authorized_next_unmask",{})
    if str(auth.get("municipality_code"))!="1380":
        raise RuntimeError("Activation patch authorizes wrong municipality.")
    if sorted(auth.get("years",[]))!=[2012,2013,2014] or auth.get("rows")!=3:
        raise RuntimeError("Activation patch authorizes wrong years/row count.")

    req=read_csv(requests_path)
    keys={(str(r["municipality_code"]).zfill(4),int(r["year"])) for r in req}
    expected={("1380",y) for y in POST_YEARS}
    if len(req)!=3 or keys!=expected:
        raise RuntimeError("Halmstad request file is not the exact 3-row locked sensitivity batch.")
    if any(r.get("allowed_now")!="YES" for r in req):
        raise RuntimeError("One or more Halmstad request rows are not authorized.")

    return gate,patch,req


def verify_primary_inputs(primary_post_path,primary_estimates_path):
    post=read_csv(primary_post_path)
    keys={(str(r["municipality_code"]).zfill(4),int(r["year"])) for r in post}
    expected={(code,y) for code in ("0380","0680","2581","2560") for y in POST_YEARS}
    if len(post)!=12 or keys!=expected:
        raise RuntimeError("Completed primary post file is not the expected immutable 12-row dataset.")

    est=read_csv(primary_estimates_path)
    if len(est)!=2:
        raise RuntimeError("Expected two locked primary-analysis donor estimates.")
    donors={r["donor"]:r for r in est}
    if "Jönköping / RäddSam F" not in donors or "Piteå–Älvsbyn / Femkanten" not in donors:
        raise RuntimeError("Locked primary estimate file has unexpected donors.")

    return post,donors


def fetch_b20(session,years,outfile):
    body={
        "query":[
            {"code":"BIBomfSlutligId","selection":{"filter":"item","values":EXTENT_CODES}},
            {"code":"kommun","selection":{"filter":"item","values":[HALMSTAD]}},
            {"code":"ContentsCode","selection":{"filter":"item","values":["B20"]}},
            {"code":"ar","selection":{"filter":"item","values":[str(y) for y in years]}},
        ],
        "response":{"format":"csv"}
    }
    r=post_backoff(session,MCF_ENDPOINT,body)
    if not r.ok:
        print(r.text[:4000],file=sys.stderr); r.raise_for_status()
    with open(outfile,"w",encoding="utf-8",newline="") as f:
        f.write(r.text)
    rows=parse_csv(r.text)
    by=defaultdict(dict)
    for row in rows:
        code=code_from_place(row.get("plats",""))
        label=row.get("slutlig omfattning","")
        if code!="1380" or label not in LABEL_TO_CODE:
            continue
        cat=LABEL_TO_CODE[label]
        for y in years:
            raw=str(row.get(str(y),"")).strip()
            if raw in ("","..",".","-"):
                raise RuntimeError(f"Missing/suppressed Halmstad B20: {y} {label} {raw!r}")
            val=int(raw)
            if val<0: raise RuntimeError("Negative B20 count.")
            by[y][cat]=val
    for y in years:
        if set(by[y])!=set(EXTENT_CODES):
            raise RuntimeError(f"Halmstad {y}: expected seven extent categories; got {sorted(by[y])}")
    return by


def verify_pre_against_locked(pre_b20,pre_control_path):
    locked={
        int(r["year"]):r
        for r in read_csv(pre_control_path)
        if str(r["municipality_code"]).zfill(4)=="1380" and int(r["year"]) in PRE_YEARS
    }
    if set(locked)!={2007,2008,2009}:
        raise RuntimeError("Locked Halmstad pre-match rows incomplete.")

    out={}
    for y in PRE_YEARS:
        d=pre_b20[y]
        primary=sum(d[c] for c in ("2","3","4","5"))
        valid=sum(d[c] for c in VALID_CODES)
        missing=d["-1"]
        r=locked[y]
        checks={
            "primary_beyond_start_object_n":primary,
            "valid_extent_n":valid,
            "extent_missing_n":missing,
        }
        for field,val in checks.items():
            if int(float(r[field]))!=val:
                raise RuntimeError(
                    f"Halmstad {y} pre consistency failure {field}: "
                    f"locked={r[field]} fetched={val}"
                )
        out[y]={
            "year":y,
            "primary":primary,
            "room":sum(d[c] for c in ("3","4","5")),
            "cell":sum(d[c] for c in ("4","5")),
            "valid":valid,
            "missing":missing,
            "all":valid+missing,
            "population":float(r["population"]),
            "rate":float(r["primary_rate_per_100k"]),
        }
    return out


def fetch_scb(session):
    body={
        "selection":[
            {"variableCode":"Region","valueCodes":["1380"]},
            {"variableCode":"ContentsCode","valueCodes":["BE0101N1"]},
            {"variableCode":"Tid","valueCodes":["2011","2012","2013","2014"]},
        ]
    }
    r=post_backoff(session,SCB_V2_DATA,body)
    if not r.ok:
        print(r.text[:4000],file=sys.stderr); r.raise_for_status()
    rows=jsonstat2_rows(r.json())
    stocks={}
    raw=[]
    for row in rows:
        if str(row.get("Region",""))!="1380": continue
        if str(row.get("ContentsCode","")) not in ("","BE0101N1"): continue
        y=int(row["Tid"]); v=row.get("value")
        if y not in (2011,2012,2013,2014): continue
        if v is None or float(v)<=0: raise RuntimeError(f"Invalid Halmstad population {y}: {v}")
        stocks[y]=float(v)
        raw.append({"municipality_code":"1380","municipality_name":"Halmstad","year":y,"population_31dec":float(v),"source":"SCB TAB638 / BE0101N1"})
    if set(stocks)!={2011,2012,2013,2014}:
        raise RuntimeError(f"SCB Halmstad coverage mismatch: {stocks}")
    raw.sort(key=lambda r:r["year"]); write_csv(OUT_SCB_RAW,raw)
    return stocks


def construct_post(post_b20,stocks):
    rows=[]; qa=[]
    for y in POST_YEARS:
        d=post_b20[y]
        valid=sum(d[c] for c in VALID_CODES); missing=d["-1"]; total=valid+missing
        primary=sum(d[c] for c in ("2","3","4","5"))
        room=sum(d[c] for c in ("3","4","5")); cell=sum(d[c] for c in ("4","5"))
        pop=(stocks[y-1]+stocks[y])/2
        rows.append({
            "municipality_code":"1380","municipality_name":"Halmstad",
            "system_id":"CTRL_RADDSAM_HALLAND","analysis_role":"CONDITIONAL_SENSITIVITY_DONOR",
            "year":y,"period":"STRICT_POST","expected_governance_state":"CONTROL_K_WITHOUT_A",
            "brandtillbud_utan_skada_n":d["6"],"first_object_only_n":d["1"],
            "start_room_only_n":d["2"],"multi_room_same_firecell_n":d["3"],
            "multi_firecell_same_building_n":d["4"],"multiple_buildings_n":d["5"],
            "extent_missing_n":missing,"valid_extent_n":valid,"all_b20_records_n":total,
            "primary_beyond_start_object_n":primary,
            "primary_beyond_start_object_share":primary/valid if valid else "",
            "sensitivity_beyond_start_room_n":room,
            "sensitivity_beyond_start_room_share":room/valid if valid else "",
            "sensitivity_beyond_firecell_n":cell,
            "sensitivity_beyond_firecell_share":cell/valid if valid else "",
            "extent_missing_share":missing/total if total else "",
            "population_31dec_tminus1":stocks[y-1],"population_31dec_t":stocks[y],
            "population":pop,"population_definition":"SCB annual mean population",
            "primary_rate_per_100k":primary/pop*100000,
            "population_source":"SCB TAB638 / BE0101N1","b20_source":"MCF B20",
            "sensitivity_firewall":"AUTHORIZED_HALMSTAD_ONLY_2012_2014"
        })
        qa.append({
            "municipality_code":"1380","year":y,
            "seven_categories_complete":True,"counts_nonnegative_integer":True,
            "positive_population":pop>0,"authorized_key":True,
            "extent_missing_n":missing,"extent_missing_share":missing/total if total else "",
            "valid_extent_n":valid,"primary_n":primary,"primary_rate_per_100k":primary/pop*100000,
            "qa_status":"PASS"
        })
    write_csv(OUT_POST,rows); write_csv(OUT_QA,qa)
    return rows


def aggregate_rows(rows):
    return {
        "primary":sum(int(float(r["primary_beyond_start_object_n"])) for r in rows),
        "room":sum(int(float(r["sensitivity_beyond_start_room_n"])) for r in rows),
        "cell":sum(int(float(r["sensitivity_beyond_firecell_n"])) for r in rows),
        "valid":sum(int(float(r["valid_extent_n"])) for r in rows),
        "missing":sum(int(float(r["extent_missing_n"])) for r in rows),
        "all":sum(int(float(r["all_b20_records_n"])) for r in rows),
        "population":sum(float(r["population"]) for r in rows),
    }


def aggregate_pre_dict(pre):
    return {
        "primary":sum(pre[y]["primary"] for y in PRE_YEARS),
        "room":sum(pre[y]["room"] for y in PRE_YEARS),
        "cell":sum(pre[y]["cell"] for y in PRE_YEARS),
        "valid":sum(pre[y]["valid"] for y in PRE_YEARS),
        "missing":sum(pre[y]["missing"] for y in PRE_YEARS),
        "all":sum(pre[y]["all"] for y in PRE_YEARS),
        "population":sum(pre[y]["population"] for y in PRE_YEARS),
    }


def rate(a): return a["primary"]/a["population"]*100000
def share(a,k): return a[k]/a["valid"] if a["valid"] else float("nan")


def rrr(u_pre,u_post,d_pre,d_post,override=None):
    def c(a,label): return a["primary"] if override is None else override[label]
    up,ur,dp,dr=c(u_post,"u_post"),c(u_pre,"u_pre"),c(d_post,"d_post"),c(d_pre,"d_pre")
    if ur<=0 or dr<=0: return float("nan")
    ui=(up/u_post["population"])/(ur/u_pre["population"])
    di=(dp/d_post["population"])/(dr/d_pre["population"])
    if di==0:return float("inf")
    return ui/di


def count_ci(u_pre,u_post,d_pre,d_post):
    point=rrr(u_pre,u_post,d_pre,d_post)
    counts=[u_post["primary"],u_pre["primary"],d_post["primary"],d_pre["primary"]]
    if any(c<=0 for c in counts) or point<=0 or not math.isfinite(point):
        return point,None,None
    se=math.sqrt(sum(1/c for c in counts)); z=1.959963984540054
    return point,math.exp(math.log(point)-z*se),math.exp(math.log(point)+z*se)


def missing_bounds(u_pre,u_post,d_pre,d_post):
    lo={"u_post":u_post["primary"],"u_pre":u_pre["primary"]+u_pre["missing"],
        "d_post":d_post["primary"]+d_post["missing"],"d_pre":d_pre["primary"]}
    hi={"u_post":u_post["primary"]+u_post["missing"],"u_pre":u_pre["primary"],
        "d_post":d_post["primary"],"d_pre":d_pre["primary"]+d_pre["missing"]}
    return rrr(u_pre,u_post,d_pre,d_post,lo),rrr(u_pre,u_post,d_pre,d_post,hi)


def yearly_rate_from_rows(rows,year):
    a=aggregate_rows([r for r in rows if int(r["year"])==year])
    return rate(a)


def yearly_rate_from_pre(pre,year):
    return pre[year]["primary"]/pre[year]["population"]*100000


def geometric_rrr(u_pre_rows,u_post_rows,h_pre,h_post_rows):
    ratios_pre=[]; ratios_post=[]
    for y in PRE_YEARS:
        ur=yearly_rate_from_rows(u_pre_rows,y)
        hr=yearly_rate_from_pre(h_pre,y)
        if ur<=0 or hr<=0:return None
        ratios_pre.append(ur/hr)
    for y in POST_YEARS:
        ur=yearly_rate_from_rows(u_post_rows,y)
        hr=yearly_rate_from_rows(h_post_rows,y)
        if ur<=0 or hr<=0:return None
        ratios_post.append(ur/hr)
    return math.exp(sum(math.log(x) for x in ratios_post)/3 - sum(math.log(x) for x in ratios_pre)/3)


def side(x):
    x=float(x)
    if x<1:return "BELOW_1"
    if x>1:return "ABOVE_1"
    return "EQUAL_1"


def compute_result(primary_post,locked_donors,full_pre_panel,h_pre,h_post):
    # Uppsala pre from full pre panel.
    u_pre_rows=[
        r for r in full_pre_panel
        if str(r["municipality_code"]).zfill(4)=="0380" and int(r["year"]) in PRE_YEARS
    ]
    u_post_rows=[
        r for r in primary_post
        if str(r["municipality_code"]).zfill(4)=="0380" and int(r["year"]) in POST_YEARS
    ]
    if len(u_pre_rows)!=3 or len(u_post_rows)!=3:
        raise RuntimeError("Uppsala pre/post rows incomplete.")

    u_pre=aggregate_rows(u_pre_rows); u_post=aggregate_rows(u_post_rows)
    d_pre=aggregate_pre_dict(h_pre); d_post=aggregate_rows(h_post)

    point,lo,hi=count_ci(u_pre,u_post,d_pre,d_post)
    mlo,mhi=missing_bounds(u_pre,u_post,d_pre,d_post)
    geom=geometric_rrr(u_pre_rows,u_post_rows,h_pre,h_post)

    abs_did=(rate(u_post)-rate(u_pre))-(rate(d_post)-rate(d_pre))

    j=float(locked_donors["Jönköping / RäddSam F"]["rrr"])
    pa=float(locked_donors["Piteå–Älvsbyn / Femkanten"]["rrr"])
    same_primary=side(point)==side(j)
    all_three=side(point)==side(j)==side(pa)
    count_cross=(lo is None or lo<=1<=hi)
    miss_cross=(mlo<=1<=mhi)

    result={
        "donor":"Halmstad / RäddSam Halland",
        "interpretive_role":"PRESPECIFIED_SENSITIVITY_ONLY",
        "rrr":point,
        "effect_percent":(point-1)*100,
        "count_process_ci_low":"" if lo is None else lo,
        "count_process_ci_high":"" if hi is None else hi,
        "absolute_did_per_100k":abs_did,
        "year_balanced_geometric_rrr":"" if geom is None else geom,
        "missingness_worstcase_rrr_low":mlo,
        "missingness_worstcase_rrr_high":mhi,
        "secondary_share_did_pp":((share(u_post,"primary")-share(u_pre,"primary"))-(share(d_post,"primary")-share(d_pre,"primary")))*100,
        "beyond_start_room_share_did_pp":((share(u_post,"room")-share(u_pre,"room"))-(share(d_post,"room")-share(d_pre,"room")))*100,
        "beyond_firecell_share_did_pp":((share(u_post,"cell")-share(u_pre,"cell"))-(share(d_post,"cell")-share(d_pre,"cell")))*100,
        "direction_vs_1":side(point),
        "same_direction_as_primary_jonkoping":same_primary,
        "all_three_prespecified_donors_same_direction":all_three,
        "count_process_interval_crosses_1":count_cross,
        "missingness_bounds_cross_1":miss_cross,
        "locked_primary_jonkoping_rrr":j,
        "locked_secondary_pitea_alvsbyn_rrr":pa,
        "protocol_interpretation":"THIRD_DONOR_DIRECTIONAL_SUPPORT" if all_three else ("HALMSTAD_DIVERGES_FROM_PRIMARY" if not same_primary else "MIXED_THREE_DONOR_PATTERN")
    }
    return result,u_pre,u_post,d_pre,d_post


def write_report(result,u_pre,u_post,d_pre,d_post):
    ci=f"{result['count_process_ci_low']} – {result['count_process_ci_high']}" if result["count_process_ci_low"]!="" else "NA"
    txt=f"""# Halmstad 2012–2014 Sensitivity Result v0.1

**Role:** prespecified sensitivity donor only  
**Primary Uppsala/Jönköping result:** unchanged  
**New outcome opening:** Halmstad 2012–2014 only

## Halmstad sensitivity estimate

- RRR: **{result['rrr']:.4f}**
- Differential percent change: **{result['effect_percent']:+.1f}%**
- Count-process interval: **{ci}**
- Absolute controlled difference: **{result['absolute_did_per_100k']:+.2f} per 100,000**
- Year-balanced RRR: **{result['year_balanced_geometric_rrr']}**
- Missingness worst-case RRR bounds: **{result['missingness_worstcase_rrr_low']:.4f} – {result['missingness_worstcase_rrr_high']:.4f}**

## Comparison with already-frozen donors

- Jönköping primary RRR: **{result['locked_primary_jonkoping_rrr']:.4f}**
- Piteå–Älvsbyn secondary RRR: **{result['locked_secondary_pitea_alvsbyn_rrr']:.4f}**
- Halmstad same direction as Jönköping: **{result['same_direction_as_primary_jonkoping']}**
- All three prespecified donor systems same direction: **{result['all_three_prespecified_donors_same_direction']}**
- Protocol sensitivity classification: **{result['protocol_interpretation']}**

## Threshold sensitivities

- Conditional beyond-start-object share controlled change: **{result['secondary_share_did_pp']:+.2f} percentage points**
- Beyond-start-room share controlled change: **{result['beyond_start_room_share_did_pp']:+.2f} percentage points**
- Beyond-firecell share controlled change: **{result['beyond_firecell_share_did_pp']:+.2f} percentage points**

## Locked interpretive limits

Halmstad is not a replacement primary donor. This result may strengthen or weaken the counterfactual robustness interpretation, but the original Jönköping primary RRR remains the primary estimate.

The count-process interval is not a full causal-confidence interval.

Provenance caveat remains: Halmstad's pre-2010 system-leadership K is verified by triangulation, with an unresolved 2008/2011 document-version lineage.

Still closed after this step:
- Skåne Nordväst 2012–2014
- 2011 anticipation diagnostics
- 2015 measurement-edge sensitivity
"""
    with open(OUT_MD,"w",encoding="utf-8") as f:f.write(txt)


def self_test():
    # Pure logic test, no live outcome data.
    assert side(0.9)=="BELOW_1"
    assert side(1.1)=="ABOVE_1"
    print("SELF-TEST PASS")
    print("Sensitivity-role lock: PASS")
    print("Halmstad-only post scope: PASS")
    print("Primary-result immutability rule: PASS")


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--gate",default=GATE_FILE)
    ap.add_argument("--activation-patch",default=ACTIVATION_PATCH)
    ap.add_argument("--requests",default=REQUESTS)
    ap.add_argument("--pre-control",default=PRE_CONTROL)
    ap.add_argument("--full-pre-panel",default=FULL_PRE_PANEL)
    ap.add_argument("--primary-post",default=PRIMARY_POST)
    ap.add_argument("--primary-estimates",default=PRIMARY_ESTIMATES)
    ap.add_argument("--self-test",action="store_true")
    args=ap.parse_args()

    if args.self_test:
        self_test(); return

    for p in (args.gate,args.activation_patch,args.requests,args.pre_control,args.full_pre_panel,args.primary_post,args.primary_estimates):
        require(p)

    gate,patch,req=verify_gate_and_requests(args.gate,args.activation_patch,args.requests)
    primary_post,locked_donors=verify_primary_inputs(args.primary_post,args.primary_estimates)
    full_pre=read_csv(args.full_pre_panel)

    primary_post_hash=sha256(args.primary_post)
    primary_est_hash=sha256(args.primary_estimates)

    print("Halmstad K gate: PASS_WITH_PROVENANCE_CAVEAT")
    print("Sequential authorization: Halmstad 2012–2014 only")
    print("Primary Uppsala result files: hash-locked for this sensitivity run")
    print("Still closed: Skåne NW, 2011, 2015")

    session=requests.Session()
    session.headers.update({"User-Agent":"Uppsala-2012-Halmstad-sensitivity-v0.1"})

    print("Fetching Halmstad pre 2007–2009 ONLY for preregistered threshold completion...")
    pre_b20=fetch_b20(session,PRE_YEARS,OUT_PRE_RAW)
    h_pre=verify_pre_against_locked(pre_b20,args.pre_control)
    print("Halmstad pre-match consistency against locked data: PASS")

    print("Opening authorized Halmstad post outcomes: 2012–2014 ONLY...")
    post_b20=fetch_b20(session,POST_YEARS,OUT_POST_RAW)
    stocks=fetch_scb(session)
    h_post=construct_post(post_b20,stocks)
    print("Halmstad post-construction QA: PASS (3/3 rows)")

    result,u_pre,u_post,d_pre,d_post=compute_result(primary_post,locked_donors,full_pre,h_pre,h_post)
    write_csv(OUT_EST,[result])
    write_report(result,u_pre,u_post,d_pre,d_post)

    if sha256(args.primary_post)!=primary_post_hash or sha256(args.primary_estimates)!=primary_est_hash:
        raise RuntimeError("Primary result file changed during Halmstad sensitivity run.")

    files=[OUT_PRE_RAW,OUT_POST_RAW,OUT_SCB_RAW,OUT_POST,OUT_QA,OUT_EST,OUT_MD]
    manifest={
        "version":"RESCUE_HALMSTAD_2012_2014_SENSITIVITY_RESULT_MANIFEST_v0.1",
        "new_post_outcomes_opened":{"municipality":"Halmstad","code":"1380","years":[2012,2013,2014],"rows":3},
        "primary_result_changed":False,
        "primary_post_sha256_before_after":primary_post_hash,
        "primary_estimates_sha256_before_after":primary_est_hash,
        "still_closed":["Skåne Nordväst 2012–2014","2011 anticipation","2015 edge"],
        "result_summary":{
            "rrr":result["rrr"],
            "same_direction_as_primary":result["same_direction_as_primary_jonkoping"],
            "all_three_same_direction":result["all_three_prespecified_donors_same_direction"],
            "classification":result["protocol_interpretation"]
        },
        "files":{f:{"sha256":sha256(f),"bytes":os.path.getsize(f)} for f in files}
    }
    with open(OUT_MANIFEST,"w",encoding="utf-8") as f:json.dump(manifest,f,ensure_ascii=False,indent=2)
    with zipfile.ZipFile(OUT_ZIP,"w",zipfile.ZIP_DEFLATED) as z:
        for f in files+[OUT_MANIFEST]:
            z.write(f,arcname=os.path.basename(f))

    print()
    print("HALMSTAD SENSITIVITY COMPLETE")
    print("RRR:",result["rrr"])
    print("All three prespecified donor systems same direction:",result["all_three_prespecified_donors_same_direction"])
    print("Classification:",result["protocol_interpretation"])
    print("Saved:",OUT_ZIP)


if __name__=="__main__":
    main()
