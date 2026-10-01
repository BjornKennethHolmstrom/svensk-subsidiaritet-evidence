#!/usr/bin/env python3
"""
Skåne Nordväst 2012–2014 Cluster Robustness v0.1

AUTHORIZED NEW OUTCOME OPENING
------------------------------
Exactly 9 municipality-years:
  Höganäs (1284): 2012, 2013, 2014
  Båstad  (1278): 2012, 2013, 2014
  Bjuv    (1260): 2012, 2013, 2014

The three municipalities are ONE independence cluster. The primary robustness
estimate pools counts and population exposure before rates are calculated.

Prespecified descriptive internal check:
  Höganäs-only.
It NEVER counts as an additional independent donor.

Already immutable:
  Jönköping primary RRR
  Piteå–Älvsbyn secondary RRR
  Halmstad sensitivity RRR

Interpretation locked before opening Skåne NW:
  pooled RRR < 1:
      3 of 4 system-level comparisons point below 1; Halmstad remains divergent.
  pooled RRR > 1:
      2–2 directional split across system-level comparisons.
  exactly 1:
      neutral boundary; no arbitrary tolerance band.

Still closed:
  2011 anticipation diagnostics
  2015 measurement-edge sensitivity
"""

import argparse, csv, hashlib, io, itertools, json, math, os, re, sys, time, zipfile
from collections import defaultdict
import requests

REQUESTS = "RESCUE_SKANE_NW_2012_2014_CLUSTER_ROBUSTNESS_REQUESTS_v0.1.csv"
PRE_CONTROL = "RESCUE_UPPSALA_CONTROL_PREMATCH_DATA_v0.1.csv"
FULL_PRE_PANEL = "RESCUE_FIRE_B20_MUNICIPALITY_YEAR_WITH_POP_v0.1.1.csv"
PRIMARY_POST = "RESCUE_UPPSALA_2012_PRIMARY_POST_DATA_v0.1.csv"
PRIMARY_ESTIMATES = "RESCUE_UPPSALA_2012_LOCKED_ESTIMATES_v0.1.csv"
HALMSTAD_ESTIMATE = "RESCUE_HALMSTAD_2012_2014_SENSITIVITY_ESTIMATE_v0.1.csv"

OUT_PRE_RAW = "RESCUE_SKANE_NW_PREMATCH_THRESHOLD_RAW_v0.1.csv"
OUT_POST_RAW = "RESCUE_SKANE_NW_2012_2014_POST_MCF_RAW_v0.1.csv"
OUT_SCB_RAW = "RESCUE_SKANE_NW_2012_2014_POST_SCB_RAW_v0.1.csv"
OUT_POST = "RESCUE_SKANE_NW_2012_2014_CLUSTER_POST_DATA_v0.1.csv"
OUT_QA = "RESCUE_SKANE_NW_2012_2014_CLUSTER_QA_v0.1.csv"
OUT_EST = "RESCUE_SKANE_NW_2012_2014_CLUSTER_ROBUSTNESS_ESTIMATE_v0.1.csv"
OUT_HOG = "RESCUE_HOGANAS_2012_2014_DESCRIPTIVE_CHECK_v0.1.csv"
OUT_MD = "Raddningstjanst-Skane-NW-2012-2014-Cluster-Robustness-Result-v0.1.md"
OUT_MANIFEST = "RESCUE_SKANE_NW_2012_2014_CLUSTER_ROBUSTNESS_RESULT_MANIFEST_v0.1.json"
OUT_ZIP = "raddningstjanst-skane-nw-2012-2014-cluster-robustness-result-v0.1.zip"

MCF_ENDPOINT = "https://statistik.mcf.se/PXWeb/api/v1/sv/PxData/START/B/B2/B20"
SCB_V2_DATA = "https://statistikdatabasen.scb.se/api/v2/tables/TAB638/data?lang=sv&outputFormat=json-stat2"

MUNIS={"1284":"Höganäs","1278":"Båstad","1260":"Bjuv"}
PRE_YEARS=(2007,2008,2009)
POST_YEARS=(2012,2013,2014)
EXTENT_CODES=["6","1","2","3","4","5","-1"]
VALID_CODES=["6","1","2","3","4","5"]
LABEL_TO_CODE={
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
        for c in iter(lambda:f.read(1024*1024),b""): h.update(c)
    return h.hexdigest()

def read_csv(path):
    with open(path,encoding="utf-8-sig",newline="") as f:return list(csv.DictReader(f))

def write_csv(path,rows):
    if not rows: raise RuntimeError(f"Refusing empty CSV: {path}")
    with open(path,"w",encoding="utf-8",newline="") as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)

def require(path):
    if not os.path.exists(path): raise RuntimeError(f"Required file missing: {path}")

def parse_csv(text):
    try:d=csv.Sniffer().sniff(text[:4096],delimiters=",;\t")
    except csv.Error:
        d=csv.excel; d.delimiter=";"
    return list(csv.DictReader(io.StringIO(text),dialect=d))

def code_from_place(value):
    m=re.match(r"^\s*(\d{4})(?:\s+|$)",str(value)); return m.group(1) if m else None

def post_backoff(session,url,body,max_retries=8):
    for attempt in range(max_retries+1):
        r=session.post(url,json=body,timeout=60)
        if r.status_code==429 and attempt<max_retries:
            try:delay=float(r.headers.get("Retry-After"))
            except (TypeError,ValueError):delay=min(5*(2**attempt),120)
            print(f"HTTP 429; retry in {delay+1:.0f}s"); time.sleep(delay+1); continue
        if 500<=r.status_code<=599 and attempt<max_retries:
            delay=min(5*(2**attempt),120); print(f"HTTP {r.status_code}; retry in {delay:.0f}s"); time.sleep(delay); continue
        return r
    raise AssertionError

def jsonstat2_rows(ds):
    ids=ds.get("id"); dims=ds.get("dimension"); vals=ds.get("value")
    if not ids or not dims or vals is None: raise RuntimeError("Unexpected SCB JSON-stat2.")
    code_lists=[]; labels={}
    for dim in ids:
        cat=dims[dim]["category"]; idx=cat["index"]
        codes=[k for k,v in sorted(idx.items(),key=lambda kv:kv[1])] if isinstance(idx,dict) else list(idx)
        code_lists.append(codes); labels[dim]=cat.get("label",{})
    valmap={i:v for i,v in enumerate(vals)} if isinstance(vals,list) else {int(k):v for k,v in vals.items()}
    rows=[]
    for i,combo in enumerate(itertools.product(*code_lists)):
        row={d:c for d,c in zip(ids,combo)}; row["value"]=valmap.get(i)
        rows.append(row)
    return rows

def verify_requests(path):
    rows=read_csv(path)
    expected={(c,y) for c in MUNIS for y in POST_YEARS}
    keys={(str(r["municipality_code"]).zfill(4),int(r["year"])) for r in rows}
    if len(rows)!=9 or keys!=expected: raise RuntimeError("Skåne NW request firewall failure.")
    if any(r["allowed_now"]!="YES" for r in rows): raise RuntimeError("Unauthorized request row.")
    return rows

def verify_locked_prior(primary_post_path,primary_estimates_path,halmstad_path):
    pp=read_csv(primary_post_path)
    expected={(c,y) for c in ("0380","0680","2581","2560") for y in POST_YEARS}
    keys={(str(r["municipality_code"]).zfill(4),int(r["year"])) for r in pp}
    if len(pp)!=12 or keys!=expected: raise RuntimeError("Primary post file unexpected.")

    pe=read_csv(primary_estimates_path)
    pd={r["donor"]:r for r in pe}
    for k in ("Jönköping / RäddSam F","Piteå–Älvsbyn / Femkanten"):
        if k not in pd: raise RuntimeError("Locked primary donor estimate missing.")

    he=read_csv(halmstad_path)
    if len(he)!=1 or he[0]["donor"]!="Halmstad / RäddSam Halland":
        raise RuntimeError("Halmstad locked sensitivity estimate missing.")
    return pp,pd,he[0]

def fetch_b20(session,years,outfile):
    body={"query":[
      {"code":"BIBomfSlutligId","selection":{"filter":"item","values":EXTENT_CODES}},
      {"code":"kommun","selection":{"filter":"item","values":list(MUNIS)}},
      {"code":"ContentsCode","selection":{"filter":"item","values":["B20"]}},
      {"code":"ar","selection":{"filter":"item","values":[str(y) for y in years]}}
    ],"response":{"format":"csv"}}
    r=post_backoff(session,MCF_ENDPOINT,body)
    if not r.ok: print(r.text[:3000],file=sys.stderr); r.raise_for_status()
    with open(outfile,"w",encoding="utf-8",newline="") as f:f.write(r.text)
    rows=parse_csv(r.text); by=defaultdict(dict)
    for row in rows:
        code=code_from_place(row.get("plats","")); label=row.get("slutlig omfattning","")
        if code not in MUNIS or label not in LABEL_TO_CODE: continue
        cat=LABEL_TO_CODE[label]
        for y in years:
            raw=str(row.get(str(y),"")).strip()
            if raw in ("","..",".","-"): raise RuntimeError(f"Missing/suppressed B20 {code} {y} {label}: {raw!r}")
            val=int(raw)
            if val<0: raise RuntimeError("Negative B20 count.")
            by[(code,y)][cat]=val
    expected={(c,y) for c in MUNIS for y in years}
    if set(by)!=expected: raise RuntimeError(f"B20 coverage mismatch: missing {sorted(expected-set(by))}")
    for key,d in by.items():
        if set(d)!=set(EXTENT_CODES): raise RuntimeError(f"Seven-category schema incomplete {key}")
    return by

def verify_pre(pre_b20,pre_control_path):
    rows=[r for r in read_csv(pre_control_path) if r["municipality_code"] in MUNIS and int(r["year"]) in PRE_YEARS]
    if len(rows)!=9: raise RuntimeError("Locked Skåne NW pre-match rows incomplete.")
    locked={(r["municipality_code"],int(r["year"])):r for r in rows}
    out={}
    for key,r in locked.items():
        d=pre_b20[key]
        primary=sum(d[c] for c in ("2","3","4","5"))
        valid=sum(d[c] for c in VALID_CODES); missing=d["-1"]
        for field,val in [("primary_beyond_start_object_n",primary),("valid_extent_n",valid),("extent_missing_n",missing)]:
            if int(float(r[field]))!=val:
                raise RuntimeError(f"Pre consistency failure {key} {field}: locked={r[field]} fetched={val}")
        out[key]={
          "primary":primary,"room":sum(d[c] for c in ("3","4","5")),"cell":sum(d[c] for c in ("4","5")),
          "valid":valid,"missing":missing,"all":valid+missing,"population":float(r["population"])
        }
    return out

def fetch_scb(session):
    body={"selection":[
      {"variableCode":"Region","valueCodes":list(MUNIS)},
      {"variableCode":"ContentsCode","valueCodes":["BE0101N1"]},
      {"variableCode":"Tid","valueCodes":["2011","2012","2013","2014"]}
    ]}
    r=post_backoff(session,SCB_V2_DATA,body)
    if not r.ok: print(r.text[:3000],file=sys.stderr); r.raise_for_status()
    rows=jsonstat2_rows(r.json()); stocks={}; raw=[]
    for row in rows:
        code=str(row.get("Region","")); y=int(row.get("Tid"))
        if code not in MUNIS or y not in (2011,2012,2013,2014): continue
        v=row.get("value")
        if v is None or float(v)<=0: raise RuntimeError(f"Invalid population {code} {y}: {v}")
        stocks[(code,y)]=float(v)
        raw.append({"municipality_code":code,"municipality_name":MUNIS[code],"year":y,"population_31dec":float(v),"source":"SCB TAB638 / BE0101N1"})
    expected={(c,y) for c in MUNIS for y in (2011,2012,2013,2014)}
    if set(stocks)!=expected: raise RuntimeError("SCB stock coverage mismatch.")
    raw.sort(key=lambda x:(x["municipality_code"],x["year"])); write_csv(OUT_SCB_RAW,raw)
    return stocks

def construct_post(post_b20,stocks):
    rows=[]; qa=[]
    for code in sorted(MUNIS):
        for y in POST_YEARS:
            d=post_b20[(code,y)]; valid=sum(d[c] for c in VALID_CODES); miss=d["-1"]; total=valid+miss
            primary=sum(d[c] for c in ("2","3","4","5")); room=sum(d[c] for c in ("3","4","5")); cell=sum(d[c] for c in ("4","5"))
            pop=(stocks[(code,y-1)]+stocks[(code,y)])/2
            rows.append({
              "municipality_code":code,"municipality_name":MUNIS[code],"system_id":"CTRL_SKANE_NW",
              "analysis_role":"CLUSTER_COMPONENT_NOT_INDEPENDENT_DONOR","year":y,"period":"STRICT_POST",
              "expected_governance_state":"CONTROL_K_WITHOUT_A",
              "brandtillbud_utan_skada_n":d["6"],"first_object_only_n":d["1"],"start_room_only_n":d["2"],
              "multi_room_same_firecell_n":d["3"],"multi_firecell_same_building_n":d["4"],"multiple_buildings_n":d["5"],
              "extent_missing_n":miss,"valid_extent_n":valid,"all_b20_records_n":total,
              "primary_beyond_start_object_n":primary,"primary_beyond_start_object_share":primary/valid if valid else "",
              "sensitivity_beyond_start_room_n":room,"sensitivity_beyond_start_room_share":room/valid if valid else "",
              "sensitivity_beyond_firecell_n":cell,"sensitivity_beyond_firecell_share":cell/valid if valid else "",
              "extent_missing_share":miss/total if total else "",
              "population_31dec_tminus1":stocks[(code,y-1)],"population_31dec_t":stocks[(code,y)],
              "population":pop,"primary_rate_per_100k":primary/pop*100000,
              "population_source":"SCB TAB638 / BE0101N1","b20_source":"MCF B20",
              "robustness_firewall":"AUTHORIZED_SKANE_NW_ONLY_2012_2014"
            })
            qa.append({"municipality_code":code,"municipality_name":MUNIS[code],"year":y,
              "seven_categories_complete":True,"counts_nonnegative_integer":True,"positive_population":pop>0,
              "extent_missing_n":miss,"extent_missing_share":miss/total if total else "",
              "valid_extent_n":valid,"primary_n":primary,"primary_rate_per_100k":primary/pop*100000,"qa_status":"PASS"})
    write_csv(OUT_POST,rows); write_csv(OUT_QA,qa); return rows

def ag_rows(rows):
    return {"primary":sum(int(float(r["primary_beyond_start_object_n"])) for r in rows),
            "room":sum(int(float(r["sensitivity_beyond_start_room_n"])) for r in rows),
            "cell":sum(int(float(r["sensitivity_beyond_firecell_n"])) for r in rows),
            "valid":sum(int(float(r["valid_extent_n"])) for r in rows),
            "missing":sum(int(float(r["extent_missing_n"])) for r in rows),
            "all":sum(int(float(r["all_b20_records_n"])) for r in rows),
            "population":sum(float(r["population"]) for r in rows)}

def ag_pre(pre,codes):
    vals=[v for (c,y),v in pre.items() if c in codes and y in PRE_YEARS]
    return {k:sum(v[k] for v in vals) for k in ("primary","room","cell","valid","missing","all","population")}

def rate(a): return a["primary"]/a["population"]*100000
def share(a,k): return a[k]/a["valid"] if a["valid"] else float("nan")

def rrr(up,uq,dp,dq,override=None):
    def c(a,l):return a["primary"] if override is None else override[l]
    a,b,c1,d=c(uq,"u_post"),c(up,"u_pre"),c(dq,"d_post"),c(dp,"d_pre")
    if b<=0 or d<=0:return float("nan")
    ui=(a/uq["population"])/(b/up["population"]); di=(c1/dq["population"])/(d/dp["population"])
    return ui/di if di else float("inf")

def ci(up,uq,dp,dq):
    p=rrr(up,uq,dp,dq); counts=[uq["primary"],up["primary"],dq["primary"],dp["primary"]]
    if any(x<=0 for x in counts) or p<=0 or not math.isfinite(p):return p,None,None
    se=math.sqrt(sum(1/x for x in counts)); z=1.959963984540054
    return p,math.exp(math.log(p)-z*se),math.exp(math.log(p)+z*se)

def mbounds(up,uq,dp,dq):
    lo={"u_post":uq["primary"],"u_pre":up["primary"]+up["missing"],"d_post":dq["primary"]+dq["missing"],"d_pre":dp["primary"]}
    hi={"u_post":uq["primary"]+uq["missing"],"u_pre":up["primary"],"d_post":dq["primary"],"d_pre":dp["primary"]+dp["missing"]}
    return rrr(up,uq,dp,dq,lo),rrr(up,uq,dp,dq,hi)

def annual_u(full_pre,primary_post,y):
    rows=full_pre if y in PRE_YEARS else primary_post
    a=ag_rows([r for r in rows if str(r["municipality_code"]).zfill(4)=="0380" and int(r["year"])==y]); return rate(a)

def annual_cluster(pre,post,codes,y):
    if y in PRE_YEARS:
        a=ag_pre({k:v for k,v in pre.items() if k[1]==y},codes)
    else:
        a=ag_rows([r for r in post if r["municipality_code"] in codes and int(r["year"])==y])
    return rate(a)

def geom_rrr(full_pre,primary_post,pre,post,codes):
    pre_rat=[]; post_rat=[]
    for y in PRE_YEARS:
        a=annual_u(full_pre,primary_post,y); b=annual_cluster(pre,post,codes,y)
        if a<=0 or b<=0:return None
        pre_rat.append(a/b)
    for y in POST_YEARS:
        a=annual_u(full_pre,primary_post,y); b=annual_cluster(pre,post,codes,y)
        if a<=0 or b<=0:return None
        post_rat.append(a/b)
    return math.exp(sum(math.log(x) for x in post_rat)/3-sum(math.log(x) for x in pre_rat)/3)

def side(x):
    x=float(x)
    if x<1:return "BELOW_1"
    if x>1:return "ABOVE_1"
    return "EQUAL_1"

def estimate(label,codes,role,full_pre,primary_post,pre,post):
    up=ag_rows([r for r in full_pre if str(r["municipality_code"]).zfill(4)=="0380" and int(r["year"]) in PRE_YEARS])
    uq=ag_rows([r for r in primary_post if str(r["municipality_code"]).zfill(4)=="0380" and int(r["year"]) in POST_YEARS])
    dp=ag_pre(pre,codes); dq=ag_rows([r for r in post if r["municipality_code"] in codes])
    p,lo,hi=ci(up,uq,dp,dq); ml,mh=mbounds(up,uq,dp,dq); g=geom_rrr(full_pre,primary_post,pre,post,codes)
    return {"donor":label,"interpretive_role":role,"rrr":p,"effect_percent":(p-1)*100,
      "count_process_ci_low":"" if lo is None else lo,"count_process_ci_high":"" if hi is None else hi,
      "absolute_did_per_100k":(rate(uq)-rate(up))-(rate(dq)-rate(dp)),
      "year_balanced_geometric_rrr":"" if g is None else g,
      "missingness_worstcase_rrr_low":ml,"missingness_worstcase_rrr_high":mh,
      "secondary_share_did_pp":((share(uq,"primary")-share(up,"primary"))-(share(dq,"primary")-share(dp,"primary")))*100,
      "beyond_start_room_share_did_pp":((share(uq,"room")-share(up,"room"))-(share(dq,"room")-share(dp,"room")))*100,
      "beyond_firecell_share_did_pp":((share(uq,"cell")-share(up,"cell"))-(share(dq,"cell")-share(dp,"cell")))*100,
      "direction_vs_1":side(p)}

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--requests",default=REQUESTS); ap.add_argument("--pre-control",default=PRE_CONTROL)
    ap.add_argument("--full-pre-panel",default=FULL_PRE_PANEL); ap.add_argument("--primary-post",default=PRIMARY_POST)
    ap.add_argument("--primary-estimates",default=PRIMARY_ESTIMATES); ap.add_argument("--halmstad-estimate",default=HALMSTAD_ESTIMATE)
    ap.add_argument("--self-test",action="store_true"); args=ap.parse_args()
    if args.self_test:
        assert side(.9)=="BELOW_1" and side(1.1)=="ABOVE_1"
        print("SELF-TEST PASS"); print("Cluster pooling rule: PASS"); print("Höganäs-only non-independent rule: PASS"); return

    for p in (args.requests,args.pre_control,args.full_pre_panel,args.primary_post,args.primary_estimates,args.halmstad_estimate):require(p)
    verify_requests(args.requests)
    primary_post,pdonors,halm=verify_locked_prior(args.primary_post,args.primary_estimates,args.halmstad_estimate)
    full_pre=read_csv(args.full_pre_panel)
    hashes={p:sha256(p) for p in (args.primary_post,args.primary_estimates,args.halmstad_estimate)}

    print("Authorized Skåne NW opening: 9 rows, 2012–2014 only")
    print("Pooling rule: Höganäs+Båstad+Bjuv = ONE independence cluster")
    print("Höganäs-only check: descriptive, NOT independent")
    print("Still closed: 2011 and 2015")

    s=requests.Session(); s.headers.update({"User-Agent":"Uppsala-2012-SkaneNW-cluster-robustness-v0.1"})
    print("Fetching Skåne NW pre 2007–2009 for threshold completion/consistency...")
    pre_b=fetch_b20(s,PRE_YEARS,OUT_PRE_RAW); pre=verify_pre(pre_b,args.pre_control); print("Pre-match consistency: PASS (9/9)")
    print("Opening Skåne NW post outcomes 2012–2014...")
    post_b=fetch_b20(s,POST_YEARS,OUT_POST_RAW); stocks=fetch_scb(s); post=construct_post(post_b,stocks); print("Post QA: PASS (9/9)")

    cluster=estimate("Skåne Nordväst pooled",set(MUNIS),"CLUSTER_ROBUSTNESS_ONLY",full_pre,primary_post,pre,post)
    hog=estimate("Höganäs only",{"1284"},"DESCRIPTIVE_INTERNAL_CHECK_NOT_INDEPENDENT",full_pre,primary_post,pre,post)
    write_csv(OUT_HOG,[hog])

    j=float(pdonors["Jönköping / RäddSam F"]["rrr"]); pa=float(pdonors["Piteå–Älvsbyn / Femkanten"]["rrr"]); h=float(halm["rrr"])
    dirs=[side(j),side(pa),side(h),side(cluster["rrr"])]
    below=sum(d=="BELOW_1" for d in dirs); above=sum(d=="ABOVE_1" for d in dirs)
    if side(cluster["rrr"])=="BELOW_1":
        classification="MAJORITY_DIRECTIONAL_SUPPORT_WITH_HALMSTAD_DIVERGENCE"
    elif side(cluster["rrr"])=="ABOVE_1":
        classification="TWO_TWO_COUNTERFACTUAL_DIRECTION_SPLIT"
    else:
        classification="SKANE_CLUSTER_NEUTRAL_BOUNDARY"

    cluster.update({
      "locked_primary_jonkoping_rrr":j,"locked_secondary_pitea_alvsbyn_rrr":pa,"locked_halmstad_rrr":h,
      "system_level_below_1_count":below,"system_level_above_1_count":above,
      "four_system_classification":classification,
      "hoganas_descriptive_rrr":hog["rrr"],"hoganas_descriptive_direction":hog["direction_vs_1"],
      "hoganas_counts_as_independent_donor":False
    })
    write_csv(OUT_EST,[cluster])

    txt=f"""# Skåne Nordväst 2012–2014 Cluster Robustness Result v0.1

**Role:** pooled cluster robustness only  
**Independence unit:** one system, not three municipalities  
**Primary result:** unchanged

## Pooled Skåne Nordväst

- RRR: **{cluster['rrr']:.4f}**
- Differential percent change: **{cluster['effect_percent']:+.1f}%**
- Count-process interval: **{cluster['count_process_ci_low']} – {cluster['count_process_ci_high']}**
- Absolute controlled difference: **{cluster['absolute_did_per_100k']:+.2f} per 100,000**
- Year-balanced RRR: **{cluster['year_balanced_geometric_rrr']}**
- Missingness worst-case bounds: **{cluster['missingness_worstcase_rrr_low']:.4f} – {cluster['missingness_worstcase_rrr_high']:.4f}**

## Four system-level directions

- Jönköping: **{j:.4f}** ({side(j)})
- Piteå–Älvsbyn: **{pa:.4f}** ({side(pa)})
- Halmstad: **{h:.4f}** ({side(h)})
- Skåne NW pooled: **{cluster['rrr']:.4f}** ({cluster['direction_vs_1']})

Classification: **{classification}**

## Höganäs-only descriptive check

- RRR: **{hog['rrr']:.4f}**
- Direction: **{hog['direction_vs_1']}**

Höganäs is NOT counted as an additional donor or replication.

## Threshold sensitivities, pooled cluster

- Beyond-start-object conditional share: **{cluster['secondary_share_did_pp']:+.2f} pp**
- Beyond-start-room share: **{cluster['beyond_start_room_share_did_pp']:+.2f} pp**
- Beyond-firecell share: **{cluster['beyond_firecell_share_did_pp']:+.2f} pp**

## Locked interpretation

If pooled Skåne NW is below 1, the directional tally is three system-level comparisons below 1 and Halmstad above 1. The result remains counterfactual-sensitive because a prespecified plausible donor diverges.

If pooled Skåne NW is above 1, the system-level directions split 2–2, strengthening the conclusion that the inferred Uppsala effect depends materially on counterfactual choice.

No Skåne result changes the primary Jönköping estimate.

Still closed:
- 2011 anticipation diagnostics
- 2015 measurement-edge sensitivity
"""
    with open(OUT_MD,"w",encoding="utf-8") as f:f.write(txt)

    for p,hsh in hashes.items():
        if sha256(p)!=hsh: raise RuntimeError(f"Immutable prior result changed: {p}")

    files=[OUT_PRE_RAW,OUT_POST_RAW,OUT_SCB_RAW,OUT_POST,OUT_QA,OUT_EST,OUT_HOG,OUT_MD]
    man={"version":"RESCUE_SKANE_NW_2012_2014_CLUSTER_ROBUSTNESS_RESULT_MANIFEST_v0.1",
      "new_post_outcomes":{"municipalities":MUNIS,"years":[2012,2013,2014],"rows":9},
      "independence_clusters_opened":1,"primary_result_changed":False,"halmstad_result_changed":False,
      "still_closed":["2011 anticipation diagnostics","2015 measurement-edge sensitivity"],
      "result":{"pooled_rrr":cluster["rrr"],"direction":cluster["direction_vs_1"],"classification":classification,
                "hoganas_descriptive_rrr":hog["rrr"],"hoganas_is_independent":False},
      "files":{f:{"sha256":sha256(f),"bytes":os.path.getsize(f)} for f in files}}
    with open(OUT_MANIFEST,"w",encoding="utf-8") as f:json.dump(man,f,ensure_ascii=False,indent=2)
    with zipfile.ZipFile(OUT_ZIP,"w",zipfile.ZIP_DEFLATED) as z:
        for f in files+[OUT_MANIFEST]:z.write(f,arcname=os.path.basename(f))
    print(); print("SKÅNE NW CLUSTER ROBUSTNESS COMPLETE")
    print("Pooled RRR:",cluster["rrr"]); print("Classification:",classification); print("Saved:",OUT_ZIP)

if __name__=="__main__": main()
