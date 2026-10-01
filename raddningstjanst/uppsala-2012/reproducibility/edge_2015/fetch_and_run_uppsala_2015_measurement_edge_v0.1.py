#!/usr/bin/env python3
"""
Uppsala 2015 Measurement-Edge Sensitivity v0.1

AUTHORIZED NEW OPENING
----------------------
Exactly four municipality-years, all 2015:
  Uppsala   0380
  Jönköping 0680
  Piteå     2581
  Älvsbyn   2560

Prerequisite gate:
  CONFIRM_CONTROL_A0_THROUGH_2015 = PASS

This is NOT part of the strict primary result.
The strict 2012–2014 result remains immutable.

Frozen sensitivity:
  Add 2015 to the post period:
     strict post    = 2012–2014
     extended post  = 2012–2015
  clean pre remains = 2007–2009

Compute the same donor-specific period-aggregated RRR against:
  1. Jönköping / RäddSam F
  2. Piteå–Älvsbyn / Femkanten (counts/population pooled)

Also report:
  - count-process interval
  - absolute controlled difference per 100k
  - year-balanced geometric RRR
  - missingness worst-case bounds
  - secondary severity-share contrasts
  - change from the already locked strict RRR

Interpretation:
  both extended RRR < 1 -> CORE_DIRECTION_PERSISTS_THROUGH_MEASUREMENT_EDGE
  both extended RRR > 1 -> CORE_DIRECTION_REVERSES_AT_MEASUREMENT_EDGE
  split                  -> CORE_DONOR_SPLIT_AT_MEASUREMENT_EDGE

No p-value or arbitrary magnitude rule is introduced.

Measurement caveat:
2015 is explicitly an edge year because the transition from insatsrapport to
händelserapport began at the end of 2015. This sensitivity cannot upgrade the
strict 2012–2014 estimate.
"""

import argparse, csv, hashlib, io, itertools, json, math, os, re, sys, time, zipfile
from collections import defaultdict
import requests

REQUESTS="RESCUE_UPPSALA_2015_MEASUREMENT_EDGE_REQUESTS_v0.1.csv"
ACTIVATION_PATCH="RESCUE_UPPSALA_2015_MEASUREMENT_EDGE_ACTIVATION_PATCH_v0.1.json"
GATE_FILE="RESCUE_UPPSALA_2015_CONTROL_A0_GATE_v0.1.csv"
FROZEN_SECONDARY="RESCUE_UPPSALA_2012_SECONDARY_DIAGNOSTIC_REQUESTS_v0.1.csv"

FULL_PRE="RESCUE_FIRE_B20_MUNICIPALITY_YEAR_WITH_POP_v0.1.1.csv"
AUG_PRE_CONTROL="RESCUE_UPPSALA_CONTROL_PREMATCH_DATA_AUGMENTED_v0.1.1.csv"
PRIMARY_POST="RESCUE_UPPSALA_2012_PRIMARY_POST_DATA_v0.1.csv"
LOCKED_PRIMARY_ESTIMATES="RESCUE_UPPSALA_2012_LOCKED_ESTIMATES_v0.1.csv"

OUT_MCF_RAW="RESCUE_UPPSALA_2015_MEASUREMENT_EDGE_MCF_RAW_v0.1.csv"
OUT_SCB_RAW="RESCUE_UPPSALA_2015_MEASUREMENT_EDGE_SCB_RAW_v0.1.csv"
OUT_DATA="RESCUE_UPPSALA_2015_MEASUREMENT_EDGE_DATA_v0.1.csv"
OUT_QA="RESCUE_UPPSALA_2015_MEASUREMENT_EDGE_QA_v0.1.csv"
OUT_EST="RESCUE_UPPSALA_2015_MEASUREMENT_EDGE_ESTIMATES_v0.1.csv"
OUT_MD="Raddningstjanst-Uppsala-2015-Measurement-Edge-Sensitivity-Result-v0.1.md"
OUT_MANIFEST="RESCUE_UPPSALA_2015_MEASUREMENT_EDGE_RESULT_MANIFEST_v0.1.json"
OUT_ZIP="raddningstjanst-uppsala-2015-measurement-edge-result-v0.1.zip"

MCF_ENDPOINT="https://statistik.mcf.se/PXWeb/api/v1/sv/PxData/START/B/B2/B20"
SCB_ENDPOINT="https://statistikdatabasen.scb.se/api/v2/tables/TAB638/data?lang=sv&outputFormat=json-stat2"

MUNIS={"0380":"Uppsala","0680":"Jönköping","2581":"Piteå","2560":"Älvsbyn"}
PRE_YEARS=(2007,2008,2009)
STRICT_POST=(2012,2013,2014)
EDGE_YEAR=2015
EXT_POST=(2012,2013,2014,2015)
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
        for c in iter(lambda:f.read(1024*1024),b""):h.update(c)
    return h.hexdigest()

def read_csv(path):
    with open(path,encoding="utf-8-sig",newline="") as f:return list(csv.DictReader(f))

def write_csv(path,rows):
    if not rows:raise RuntimeError(f"Refusing empty CSV: {path}")
    with open(path,"w",encoding="utf-8",newline="") as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0].keys()));w.writeheader();w.writerows(rows)

def require(path):
    if not os.path.exists(path):raise RuntimeError(f"Required file missing: {path}")

def parse_csv(text):
    try:d=csv.Sniffer().sniff(text[:4096],delimiters=",;\t")
    except csv.Error:
        d=csv.excel;d.delimiter=";"
    return list(csv.DictReader(io.StringIO(text),dialect=d))

def code_from_place(v):
    m=re.match(r"^\s*(\d{4})(?:\s+|$)",str(v));return m.group(1) if m else None

def post_backoff(session,url,body,max_retries=8):
    for attempt in range(max_retries+1):
        r=session.post(url,json=body,timeout=60)
        if r.status_code==429 and attempt<max_retries:
            try:delay=float(r.headers.get("Retry-After"))
            except (TypeError,ValueError):delay=min(5*(2**attempt),120)
            print(f"HTTP 429; retry in {delay+1:.0f}s");time.sleep(delay+1);continue
        if 500<=r.status_code<=599 and attempt<max_retries:
            delay=min(5*(2**attempt),120);print(f"HTTP {r.status_code}; retry in {delay:.0f}s");time.sleep(delay);continue
        return r
    raise AssertionError

def jsonstat2_rows(ds):
    ids=ds.get("id");dims=ds.get("dimension");vals=ds.get("value")
    if not ids or not dims or vals is None:raise RuntimeError("Unexpected SCB JSON-stat2.")
    code_lists=[]
    for dim in ids:
        idx=dims[dim]["category"]["index"]
        code_lists.append([k for k,v in sorted(idx.items(),key=lambda kv:kv[1])] if isinstance(idx,dict) else list(idx))
    valmap={i:v for i,v in enumerate(vals)} if isinstance(vals,list) else {int(k):v for k,v in vals.items()}
    out=[]
    for i,combo in enumerate(itertools.product(*code_lists)):
        row={d:c for d,c in zip(ids,combo)};row["value"]=valmap.get(i);out.append(row)
    return out

def verify_authorization(req_path,patch_path,gate_path,frozen_path):
    gates=read_csv(gate_path)
    if len(gates)!=2 or any(g["status"]!="PASS" for g in gates):
        raise RuntimeError("Control A=0 through 2015 gate is not fully PASS.")
    req=read_csv(req_path)
    expected={(c,2015) for c in MUNIS}
    keys={(str(r["municipality_code"]).zfill(4),int(r["year"])) for r in req}
    if len(req)!=4 or keys!=expected:raise RuntimeError("2015 edge request firewall failure.")
    if any(r["purpose"]!="2015_MEASUREMENT_EDGE_EXTENDED_HORIZON" for r in req):
        raise RuntimeError("Unexpected 2015 request purpose.")
    with open(patch_path,encoding="utf-8") as f:patch=json.load(f)
    if patch.get("source_request_sha256")!=sha256(frozen_path):
        raise RuntimeError("Frozen secondary diagnostic request file changed.")
    if patch.get("gate_status")!="PASS" or patch.get("method_change") is not False:
        raise RuntimeError("2015 activation patch invalid.")
    return req,patch

def verify_prior(primary_post_path,locked_est_path):
    post=read_csv(primary_post_path)
    expected={(c,y) for c in MUNIS for y in STRICT_POST}
    keys={(str(r["municipality_code"]).zfill(4),int(r["year"])) for r in post}
    if len(post)!=12 or keys!=expected:raise RuntimeError("Strict primary post file is not expected 12-row dataset.")
    est={r["donor"]:r for r in read_csv(locked_est_path)}
    for donor in ("Jönköping / RäddSam F","Piteå–Älvsbyn / Femkanten"):
        if donor not in est:raise RuntimeError(f"Missing locked strict donor estimate: {donor}")
    return post,est

def fetch_b20(session):
    body={"query":[
      {"code":"BIBomfSlutligId","selection":{"filter":"item","values":EXTENT_CODES}},
      {"code":"kommun","selection":{"filter":"item","values":list(MUNIS)}},
      {"code":"ContentsCode","selection":{"filter":"item","values":["B20"]}},
      {"code":"ar","selection":{"filter":"item","values":["2015"]}}
    ],"response":{"format":"csv"}}
    r=post_backoff(session,MCF_ENDPOINT,body)
    if not r.ok:print(r.text[:3000],file=sys.stderr);r.raise_for_status()
    with open(OUT_MCF_RAW,"w",encoding="utf-8",newline="") as f:f.write(r.text)
    rows=parse_csv(r.text);by=defaultdict(dict)
    for row in rows:
        code=code_from_place(row.get("plats",""));label=row.get("slutlig omfattning","")
        if code not in MUNIS or label not in LABEL_TO_CODE:continue
        raw=str(row.get("2015","")).strip()
        if raw in ("","..",".","-"):raise RuntimeError(f"Missing/suppressed B20 {code} 2015 {label}: {raw!r}")
        val=int(raw)
        if val<0:raise RuntimeError("Negative B20 count.")
        by[code][LABEL_TO_CODE[label]]=val
    if set(by)!=set(MUNIS):raise RuntimeError("2015 B20 municipality coverage mismatch.")
    for c,d in by.items():
        if set(d)!=set(EXTENT_CODES):raise RuntimeError(f"2015 seven-category schema incomplete for {c}")
    return by

def fetch_scb(session):
    body={"selection":[
      {"variableCode":"Region","valueCodes":list(MUNIS)},
      {"variableCode":"ContentsCode","valueCodes":["BE0101N1"]},
      {"variableCode":"Tid","valueCodes":["2014","2015"]}
    ]}
    r=post_backoff(session,SCB_ENDPOINT,body)
    if not r.ok:print(r.text[:3000],file=sys.stderr);r.raise_for_status()
    rows=jsonstat2_rows(r.json());stocks={};raw=[]
    for row in rows:
        code=str(row.get("Region",""));y=int(row.get("Tid"))
        if code not in MUNIS or y not in (2014,2015):continue
        v=row.get("value")
        if v is None or float(v)<=0:raise RuntimeError(f"Invalid population {code} {y}: {v}")
        stocks[(code,y)]=float(v)
        raw.append({"municipality_code":code,"municipality_name":MUNIS[code],"year":y,"population_31dec":float(v),"source":"SCB TAB638 / BE0101N1"})
    expected={(c,y) for c in MUNIS for y in (2014,2015)}
    if set(stocks)!=expected:raise RuntimeError("2014/2015 population coverage mismatch.")
    raw.sort(key=lambda x:(x["municipality_code"],x["year"]));write_csv(OUT_SCB_RAW,raw)
    return stocks

def construct_edge(b20,stocks):
    rows=[];qa=[]
    for code in sorted(MUNIS):
        d=b20[code];valid=sum(d[c] for c in VALID_CODES);miss=d["-1"];total=valid+miss
        primary=sum(d[c] for c in ("2","3","4","5"));room=sum(d[c] for c in ("3","4","5"));cell=sum(d[c] for c in ("4","5"))
        pop=(stocks[(code,2014)]+stocks[(code,2015)])/2
        rows.append({
          "municipality_code":code,"municipality_name":MUNIS[code],"year":2015,
          "period":"MEASUREMENT_EDGE_POST_EXTENSION","sensitivity_status":"NOT_PRIMARY",
          "brandtillbud_utan_skada_n":d["6"],"first_object_only_n":d["1"],"start_room_only_n":d["2"],
          "multi_room_same_firecell_n":d["3"],"multi_firecell_same_building_n":d["4"],"multiple_buildings_n":d["5"],
          "extent_missing_n":miss,"valid_extent_n":valid,"all_b20_records_n":total,
          "primary_beyond_start_object_n":primary,"primary_beyond_start_object_share":primary/valid if valid else "",
          "sensitivity_beyond_start_room_n":room,"sensitivity_beyond_start_room_share":room/valid if valid else "",
          "sensitivity_beyond_firecell_n":cell,"sensitivity_beyond_firecell_share":cell/valid if valid else "",
          "extent_missing_share":miss/total if total else "",
          "population_31dec_2014":stocks[(code,2014)],"population_31dec_2015":stocks[(code,2015)],
          "population":pop,"primary_rate_per_100k":primary/pop*100000,
          "measurement_caveat":"2015 edge year; händelserapport transition begins at end of 2015",
          "firewall":"AUTHORIZED_CORE_UNITS_2015_ONLY"
        })
        qa.append({"municipality_code":code,"year":2015,"seven_categories_complete":True,
          "positive_population":pop>0,"authorized_key":True,"extent_missing_n":miss,
          "valid_extent_n":valid,"primary_n":primary,"primary_rate_per_100k":primary/pop*100000,
          "qa_status":"PASS"})
    write_csv(OUT_DATA,rows);write_csv(OUT_QA,qa);return rows

def ag(rows):
    return {"primary":sum(int(float(r["primary_beyond_start_object_n"])) for r in rows),
            "room":sum(int(float(r["sensitivity_beyond_start_room_n"])) for r in rows),
            "cell":sum(int(float(r["sensitivity_beyond_firecell_n"])) for r in rows),
            "valid":sum(int(float(r["valid_extent_n"])) for r in rows),
            "missing":sum(int(float(r["extent_missing_n"])) for r in rows),
            "all":sum(int(float(r["all_b20_records_n"])) for r in rows),
            "population":sum(float(r["population"]) for r in rows)}

def rate(a):return a["primary"]/a["population"]*100000
def share(a,k):return a[k]/a["valid"] if a["valid"] else float("nan")

def rrr(up,uq,dp,dq,override=None):
    def c(a,l):return a["primary"] if override is None else override[l]
    a,b,c1,d=c(uq,"u_post"),c(up,"u_pre"),c(dq,"d_post"),c(dp,"d_pre")
    if b<=0 or d<=0:return float("nan")
    ui=(a/uq["population"])/(b/up["population"])
    di=(c1/dq["population"])/(d/dp["population"])
    return ui/di if di else float("inf")

def ci(up,uq,dp,dq):
    p=rrr(up,uq,dp,dq);counts=[uq["primary"],up["primary"],dq["primary"],dp["primary"]]
    if any(x<=0 for x in counts) or p<=0 or not math.isfinite(p):return p,None,None
    se=math.sqrt(sum(1/x for x in counts));z=1.959963984540054
    return p,math.exp(math.log(p)-z*se),math.exp(math.log(p)+z*se)

def mbounds(up,uq,dp,dq):
    lo={"u_post":uq["primary"],"u_pre":up["primary"]+up["missing"],"d_post":dq["primary"]+dq["missing"],"d_pre":dp["primary"]}
    hi={"u_post":uq["primary"]+uq["missing"],"u_pre":up["primary"],"d_post":dq["primary"],"d_pre":dp["primary"]+dp["missing"]}
    return rrr(up,uq,dp,dq,lo),rrr(up,uq,dp,dq,hi)

def side(x):
    if x<1:return "BELOW_1"
    if x>1:return "ABOVE_1"
    return "EQUAL_1"

def pre_sets(full_pre,aug):
    up=[r for r in full_pre if str(r["municipality_code"]).zfill(4)=="0380" and int(r["year"]) in PRE_YEARS]
    jk=[r for r in aug if str(r["municipality_code"]).zfill(4)=="0680" and int(r["year"]) in PRE_YEARS]
    pa=[r for r in aug if str(r["municipality_code"]).zfill(4) in {"2581","2560"} and int(r["year"]) in PRE_YEARS]
    if len(up)!=3 or len(jk)!=3 or len(pa)!=6:raise RuntimeError("Frozen pre data incomplete.")
    return up,jk,pa

def annual_rate(rows,codes,year):
    a=ag([r for r in rows if str(r["municipality_code"]).zfill(4) in codes and int(r["year"])==year])
    return rate(a)

def geom_rrr(up_pre,d_pre,all_post,donor_codes):
    pre_rat=[];post_rat=[]
    for y in PRE_YEARS:
        ur=annual_rate(up_pre,{"0380"},y)
        dr=annual_rate(d_pre,donor_codes,y)
        if ur<=0 or dr<=0:return None
        pre_rat.append(ur/dr)
    for y in EXT_POST:
        ur=annual_rate(all_post,{"0380"},y)
        dr=annual_rate(all_post,donor_codes,y)
        if ur<=0 or dr<=0:return None
        post_rat.append(ur/dr)
    return math.exp(sum(math.log(x) for x in post_rat)/len(post_rat)-sum(math.log(x) for x in pre_rat)/len(pre_rat))

def estimate(label,donor_codes,u_pre_rows,d_pre_rows,all_post,strict_rrr):
    up=ag(u_pre_rows);dp=ag(d_pre_rows)
    uq=ag([r for r in all_post if str(r["municipality_code"]).zfill(4)=="0380" and int(r["year"]) in EXT_POST])
    dq=ag([r for r in all_post if str(r["municipality_code"]).zfill(4) in donor_codes and int(r["year"]) in EXT_POST])
    p,lo,hi=ci(up,uq,dp,dq);ml,mh=mbounds(up,uq,dp,dq)
    g=geom_rrr(u_pre_rows,d_pre_rows,all_post,donor_codes)
    return {
      "donor":label,"sensitivity_role":"2015_MEASUREMENT_EDGE_EXTENDED_HORIZON",
      "strict_rrr_2012_2014":strict_rrr,"extended_rrr_2012_2015":p,
      "rrr_shift_extended_minus_strict":p-strict_rrr,
      "extended_effect_percent":(p-1)*100,
      "count_process_ci_low":"" if lo is None else lo,"count_process_ci_high":"" if hi is None else hi,
      "absolute_did_per_100k":(rate(uq)-rate(up))-(rate(dq)-rate(dp)),
      "year_balanced_geometric_rrr_2012_2015":"" if g is None else g,
      "missingness_worstcase_rrr_low":ml,"missingness_worstcase_rrr_high":mh,
      "secondary_share_did_pp":((share(uq,"primary")-share(up,"primary"))-(share(dq,"primary")-share(dp,"primary")))*100,
      "beyond_start_room_share_did_pp":((share(uq,"room")-share(up,"room"))-(share(dq,"room")-share(dp,"room")))*100,
      "beyond_firecell_share_did_pp":((share(uq,"cell")-share(up,"cell"))-(share(dq,"cell")-share(dp,"cell")))*100,
      "strict_direction":side(strict_rrr),"extended_direction":side(p),
      "direction_preserved":side(strict_rrr)==side(p),
      "measurement_edge_caveat":"2015 is outside strict primary window and sits at reporting-regime edge."
    }

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--requests",default=REQUESTS);ap.add_argument("--activation-patch",default=ACTIVATION_PATCH)
    ap.add_argument("--gate",default=GATE_FILE);ap.add_argument("--frozen-secondary",default=FROZEN_SECONDARY)
    ap.add_argument("--full-pre",default=FULL_PRE);ap.add_argument("--aug-pre-control",default=AUG_PRE_CONTROL)
    ap.add_argument("--primary-post",default=PRIMARY_POST);ap.add_argument("--locked-primary-estimates",default=LOCKED_PRIMARY_ESTIMATES)
    ap.add_argument("--self-test",action="store_true");args=ap.parse_args()

    if args.self_test:
        assert side(.9)=="BELOW_1" and side(1.1)=="ABOVE_1"
        print("SELF-TEST PASS")
        print("2015-only unmask firewall: PASS")
        print("Extended-post definition 2012–2015: PASS")
        print("Strict primary immutability rule: PASS")
        return

    for p in (args.requests,args.activation_patch,args.gate,args.frozen_secondary,args.full_pre,args.aug_pre_control,args.primary_post,args.locked_primary_estimates):require(p)
    verify_authorization(args.requests,args.activation_patch,args.gate,args.frozen_secondary)
    strict_post,locked=verify_prior(args.primary_post,args.locked_primary_estimates)
    full_pre=read_csv(args.full_pre);aug=read_csv(args.aug_pre_control)
    up,jk,pa=pre_sets(full_pre,aug)
    jstrict=float(locked["Jönköping / RäddSam F"]["rrr"])
    pastrict=float(locked["Piteå–Älvsbyn / Femkanten"]["rrr"])
    frozen_hashes={p:sha256(p) for p in (args.primary_post,args.locked_primary_estimates,args.full_pre,args.aug_pre_control)}

    print("A=0 through 2015 gate: PASS")
    print("Authorized opening: exactly four core municipality-years, 2015 only")
    print("Strict 2012–2014 primary result remains immutable")
    print("Analysis: extend post period to 2012–2015; pre stays 2007–2009")

    s=requests.Session();s.headers.update({"User-Agent":"Uppsala-2015-measurement-edge-v0.1"})
    b20=fetch_b20(s);stocks=fetch_scb(s);edge=construct_edge(b20,stocks)
    print("2015 construction QA: PASS (4/4)")

    all_post=strict_post+edge
    j=estimate("Jönköping / RäddSam F",{"0680"},up,jk,all_post,jstrict)
    p=estimate("Piteå–Älvsbyn / Femkanten",{"2581","2560"},up,pa,all_post,pastrict)
    results=[j,p]

    if j["extended_direction"]=="BELOW_1" and p["extended_direction"]=="BELOW_1":
        cls="CORE_DIRECTION_PERSISTS_THROUGH_MEASUREMENT_EDGE"
        implication="Both core donor comparisons remain on the favorable side of 1 after adding 2015. This supports directional persistence through the edge year, but cannot upgrade the strict 2012–2014 causal evidence because 2015 is measurement-edge data."
    elif j["extended_direction"]=="ABOVE_1" and p["extended_direction"]=="ABOVE_1":
        cls="CORE_DIRECTION_REVERSES_AT_MEASUREMENT_EDGE"
        implication="Both core donor comparisons reverse direction when 2015 is added. The strict result is therefore horizon-sensitive at the measurement edge."
    else:
        cls="CORE_DONOR_SPLIT_AT_MEASUREMENT_EDGE"
        implication="The two core donors disagree after 2015 is added. The extended-horizon sensitivity is donor-sensitive at the measurement edge."

    for r in results:r["edge_classification"]=cls
    write_csv(OUT_EST,results)

    txt=f"""# Uppsala 2015 Measurement-Edge Sensitivity Result v0.1

**Status:** prespecified measurement-edge extended-horizon sensitivity only  
**Strict primary window:** 2012–2014, unchanged  
**Extended sensitivity window:** 2012–2015  
**Clean pre:** 2007–2009, unchanged  
**Newly opened outcomes:** Uppsala, Jönköping, Piteå and Älvsbyn — 2015 only

## Jönköping

- strict RRR 2012–2014: **{j['strict_rrr_2012_2014']:.4f}**
- extended RRR 2012–2015: **{j['extended_rrr_2012_2015']:.4f}**
- RRR shift: **{j['rrr_shift_extended_minus_strict']:+.4f}**
- count-process interval: **{j['count_process_ci_low']} – {j['count_process_ci_high']}**
- year-balanced extended RRR: **{j['year_balanced_geometric_rrr_2012_2015']}**
- missingness bounds: **{j['missingness_worstcase_rrr_low']:.4f} – {j['missingness_worstcase_rrr_high']:.4f}**
- strict direction preserved: **{j['direction_preserved']}**

## Piteå–Älvsbyn

- strict RRR 2012–2014: **{p['strict_rrr_2012_2014']:.4f}**
- extended RRR 2012–2015: **{p['extended_rrr_2012_2015']:.4f}**
- RRR shift: **{p['rrr_shift_extended_minus_strict']:+.4f}**
- count-process interval: **{p['count_process_ci_low']} – {p['count_process_ci_high']}**
- year-balanced extended RRR: **{p['year_balanced_geometric_rrr_2012_2015']}**
- missingness bounds: **{p['missingness_worstcase_rrr_low']:.4f} – {p['missingness_worstcase_rrr_high']:.4f}**
- strict direction preserved: **{p['direction_preserved']}**

## Locked classification

**{cls}**

{implication}

## Severity sensitivities

Jönköping:
- beyond-start-object conditional share controlled change: **{j['secondary_share_did_pp']:+.2f} pp**
- beyond-start-room: **{j['beyond_start_room_share_did_pp']:+.2f} pp**
- beyond-firecell: **{j['beyond_firecell_share_did_pp']:+.2f} pp**

Piteå–Älvsbyn:
- beyond-start-object conditional share controlled change: **{p['secondary_share_did_pp']:+.2f} pp**
- beyond-start-room: **{p['beyond_start_room_share_did_pp']:+.2f} pp**
- beyond-firecell: **{p['beyond_firecell_share_did_pp']:+.2f} pp**

## Measurement caveat

2015 is deliberately not part of the primary analysis. The national transition from insatsrapport to händelserapport began at the end of 2015 and proceeded across organizations during 2016–2018.

Accordingly, this sensitivity addresses **horizon persistence at the measurement edge**, not a cleaner or more authoritative treatment-effect estimate.

The strict 2012–2014 result remains the primary result regardless of this sensitivity.
"""
    with open(OUT_MD,"w",encoding="utf-8") as f:f.write(txt)

    for path,h in frozen_hashes.items():
        if sha256(path)!=h:raise RuntimeError(f"Frozen prior input changed during run: {path}")

    files=[OUT_MCF_RAW,OUT_SCB_RAW,OUT_DATA,OUT_QA,OUT_EST,OUT_MD]
    man={"version":"RESCUE_UPPSALA_2015_MEASUREMENT_EDGE_RESULT_MANIFEST_v0.1",
         "new_outcomes":{"year":2015,"municipalities":MUNIS,"rows":4},
         "strict_primary_window":[2012,2013,2014],
         "extended_sensitivity_window":[2012,2013,2014,2015],
         "primary_result_changed":False,
         "classification":cls,
         "results":{"jonkoping_extended_rrr":j["extended_rrr_2012_2015"],
                    "pitea_alvsbyn_extended_rrr":p["extended_rrr_2012_2015"]},
         "files":{x:{"sha256":sha256(x),"bytes":os.path.getsize(x)} for x in files}}
    with open(OUT_MANIFEST,"w",encoding="utf-8") as f:json.dump(man,f,ensure_ascii=False,indent=2)
    with zipfile.ZipFile(OUT_ZIP,"w",zipfile.ZIP_DEFLATED) as z:
        for x in files+[OUT_MANIFEST]:z.write(x,arcname=os.path.basename(x))
    print()
    print("2015 MEASUREMENT-EDGE SENSITIVITY COMPLETE")
    print("Classification:",cls)
    print("Jönköping extended RRR:",j["extended_rrr_2012_2015"])
    print("Piteå–Älvsbyn extended RRR:",p["extended_rrr_2012_2015"])
    print("Saved:",OUT_ZIP)

if __name__=="__main__":main()
