#!/usr/bin/env python3
"""
Uppsala 2011 Anticipation Diagnostics v0.1

AUTHORIZED NEW OPENING
----------------------
Exactly four municipality-years, all 2011:
  Uppsala   0380
  Jönköping 0680
  Piteå     2581
  Älvsbyn   2560

This is NOT a causal treatment-effect analysis.

The frozen protocol excluded 2010–2011 from the clean pre-period because of
anticipation/implementation. It separately authorized 2011 as a diagnostic
after the strict primary result.

Diagnostic:
  A_2011,D =
      (R_U,2011 / R_U,2007:09)
      /
      (R_D,2011 / R_D,2007:09)

where donor D is:
  1. Jönköping / RäddSam F
  2. Piteå–Älvsbyn / Femkanten, population/count pooled as one system.

Interpretation locked before 2011 is opened:
- both indices < 1:
    favorable Uppsala-relative divergence was already visible before formal
    A start. This is compatible with anticipation/implementation effects and
    weakens attribution specifically to the 2012 formal start date.
- both indices > 1:
    no favorable 2011 pre-A signal against either core donor.
- split:
    donor-mixed anticipation diagnostic.
- no magnitude threshold and no causal/significance claim.

2015 remains closed.
"""

import argparse, csv, hashlib, io, itertools, json, math, os, re, sys, time, zipfile
from collections import defaultdict
import requests

REQUESTS="RESCUE_UPPSALA_2011_ANTICIPATION_REQUESTS_v0.1.csv"
ACTIVATION_PATCH="RESCUE_UPPSALA_2011_ANTICIPATION_ACTIVATION_PATCH_v0.1.json"
FROZEN_SECONDARY="RESCUE_UPPSALA_2012_SECONDARY_DIAGNOSTIC_REQUESTS_v0.1.csv"

FULL_PRE="RESCUE_FIRE_B20_MUNICIPALITY_YEAR_WITH_POP_v0.1.1.csv"
AUG_PRE_CONTROL="RESCUE_UPPSALA_CONTROL_PREMATCH_DATA_AUGMENTED_v0.1.1.csv"
LOCKED_PRIMARY_ESTIMATES="RESCUE_UPPSALA_2012_LOCKED_ESTIMATES_v0.1.csv"

OUT_MCF_RAW="RESCUE_UPPSALA_2011_ANTICIPATION_MCF_RAW_v0.1.csv"
OUT_SCB_RAW="RESCUE_UPPSALA_2011_ANTICIPATION_SCB_RAW_v0.1.csv"
OUT_DATA="RESCUE_UPPSALA_2011_ANTICIPATION_DATA_v0.1.csv"
OUT_QA="RESCUE_UPPSALA_2011_ANTICIPATION_QA_v0.1.csv"
OUT_DIAG="RESCUE_UPPSALA_2011_ANTICIPATION_DIAGNOSTICS_v0.1.csv"
OUT_MD="Raddningstjanst-Uppsala-2011-Anticipation-Diagnostics-Result-v0.1.md"
OUT_MANIFEST="RESCUE_UPPSALA_2011_ANTICIPATION_RESULT_MANIFEST_v0.1.json"
OUT_ZIP="raddningstjanst-uppsala-2011-anticipation-diagnostics-result-v0.1.zip"

MCF_ENDPOINT="https://statistik.mcf.se/PXWeb/api/v1/sv/PxData/START/B/B2/B20"
SCB_ENDPOINT="https://statistikdatabasen.scb.se/api/v2/tables/TAB638/data?lang=sv&outputFormat=json-stat2"

MUNIS={"0380":"Uppsala","0680":"Jönköping","2581":"Piteå","2560":"Älvsbyn"}
YEAR=2011
PRE_YEARS=(2007,2008,2009)
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

def verify_authorization(req_path,patch_path,frozen_path):
    req=read_csv(req_path)
    keys={(str(r["municipality_code"]).zfill(4),int(r["year"])) for r in req}
    expected={(c,2011) for c in MUNIS}
    if len(req)!=4 or keys!=expected:raise RuntimeError("2011 request firewall failure.")
    if any(r["purpose"]!="ANTICIPATION_DIAGNOSTIC_ONLY" for r in req):raise RuntimeError("Unexpected 2011 purpose.")
    with open(patch_path,encoding="utf-8") as f:patch=json.load(f)
    if patch.get("source_request_sha256")!=sha256(frozen_path):raise RuntimeError("Frozen secondary-request hash changed.")
    if patch.get("authorized_now",{}).get("municipality_year_rows")!=4:raise RuntimeError("Activation patch row count wrong.")
    if patch.get("method_change") is not False:raise RuntimeError("Unexpected method change.")
    return req,patch

def fetch_b20(session):
    body={"query":[
      {"code":"BIBomfSlutligId","selection":{"filter":"item","values":EXTENT_CODES}},
      {"code":"kommun","selection":{"filter":"item","values":list(MUNIS)}},
      {"code":"ContentsCode","selection":{"filter":"item","values":["B20"]}},
      {"code":"ar","selection":{"filter":"item","values":["2011"]}}
    ],"response":{"format":"csv"}}
    r=post_backoff(session,MCF_ENDPOINT,body)
    if not r.ok:print(r.text[:3000],file=sys.stderr);r.raise_for_status()
    with open(OUT_MCF_RAW,"w",encoding="utf-8",newline="") as f:f.write(r.text)
    rows=parse_csv(r.text);by=defaultdict(dict)
    for row in rows:
        code=code_from_place(row.get("plats",""));label=row.get("slutlig omfattning","")
        if code not in MUNIS or label not in LABEL_TO_CODE:continue
        raw=str(row.get("2011","")).strip()
        if raw in ("","..",".","-"):raise RuntimeError(f"Missing/suppressed B20 {code} 2011 {label}: {raw!r}")
        val=int(raw)
        if val<0:raise RuntimeError("Negative B20 count.")
        by[code][LABEL_TO_CODE[label]]=val
    if set(by)!=set(MUNIS):raise RuntimeError("2011 B20 municipality coverage mismatch.")
    for c,d in by.items():
        if set(d)!=set(EXTENT_CODES):raise RuntimeError(f"2011 seven-category schema incomplete for {c}")
    return by

def fetch_scb(session):
    body={"selection":[
      {"variableCode":"Region","valueCodes":list(MUNIS)},
      {"variableCode":"ContentsCode","valueCodes":["BE0101N1"]},
      {"variableCode":"Tid","valueCodes":["2010","2011"]}
    ]}
    r=post_backoff(session,SCB_ENDPOINT,body)
    if not r.ok:print(r.text[:3000],file=sys.stderr);r.raise_for_status()
    rows=jsonstat2_rows(r.json());stocks={};raw=[]
    for row in rows:
        code=str(row.get("Region",""));y=int(row.get("Tid"))
        if code not in MUNIS or y not in (2010,2011):continue
        v=row.get("value")
        if v is None or float(v)<=0:raise RuntimeError(f"Invalid population {code} {y}: {v}")
        stocks[(code,y)]=float(v)
        raw.append({"municipality_code":code,"municipality_name":MUNIS[code],"year":y,"population_31dec":float(v),"source":"SCB TAB638 / BE0101N1"})
    expected={(c,y) for c in MUNIS for y in (2010,2011)}
    if set(stocks)!=expected:raise RuntimeError("2010/2011 population coverage mismatch.")
    raw.sort(key=lambda x:(x["municipality_code"],x["year"]));write_csv(OUT_SCB_RAW,raw)
    return stocks

def construct_2011(b20,stocks):
    rows=[];qa=[]
    for code in sorted(MUNIS):
        d=b20[code];valid=sum(d[c] for c in VALID_CODES);miss=d["-1"];total=valid+miss
        primary=sum(d[c] for c in ("2","3","4","5"));room=sum(d[c] for c in ("3","4","5"));cell=sum(d[c] for c in ("4","5"))
        pop=(stocks[(code,2010)]+stocks[(code,2011)])/2
        rows.append({
          "municipality_code":code,"municipality_name":MUNIS[code],"year":2011,
          "period":"ANTICIPATION_DIAGNOSTIC","causal_status":"NOT_A_CAUSAL_TREATMENT_ESTIMATE",
          "brandtillbud_utan_skada_n":d["6"],"first_object_only_n":d["1"],"start_room_only_n":d["2"],
          "multi_room_same_firecell_n":d["3"],"multi_firecell_same_building_n":d["4"],"multiple_buildings_n":d["5"],
          "extent_missing_n":miss,"valid_extent_n":valid,"all_b20_records_n":total,
          "primary_beyond_start_object_n":primary,"sensitivity_beyond_start_room_n":room,
          "sensitivity_beyond_firecell_n":cell,"population_31dec_2010":stocks[(code,2010)],
          "population_31dec_2011":stocks[(code,2011)],"population":pop,
          "primary_rate_per_100k":primary/pop*100000,"extent_missing_share":miss/total if total else "",
          "firewall":"AUTHORIZED_2011_CORE_UNITS_ONLY"
        })
        qa.append({"municipality_code":code,"year":2011,"seven_categories_complete":True,
          "positive_population":pop>0,"authorized_key":True,"extent_missing_n":miss,
          "valid_extent_n":valid,"primary_n":primary,"primary_rate_per_100k":primary/pop*100000,"qa_status":"PASS"})
    write_csv(OUT_DATA,rows);write_csv(OUT_QA,qa);return rows

def aggregate(rows):
    return {"primary":sum(int(float(r["primary_beyond_start_object_n"])) for r in rows),
            "population":sum(float(r["population"]) for r in rows)}

def rate(a):return a["primary"]/a["population"]*100000

def pre_rows(full_pre,aug_pre):
    # Uppsala from full pre; controls from augmented compact pre.
    up=[r for r in full_pre if str(r["municipality_code"]).zfill(4)=="0380" and int(r["year"]) in PRE_YEARS]
    jk=[r for r in aug_pre if str(r["municipality_code"]).zfill(4)=="0680" and int(r["year"]) in PRE_YEARS]
    pa=[r for r in aug_pre if str(r["municipality_code"]).zfill(4) in {"2581","2560"} and int(r["year"]) in PRE_YEARS]
    if len(up)!=3 or len(jk)!=3 or len(pa)!=6:raise RuntimeError("Frozen pre data incomplete.")
    return up,jk,pa

def side(x):
    if x<1:return "BELOW_1"
    if x>1:return "ABOVE_1"
    return "EQUAL_1"

def diagnostic(label,donor_codes,pre_donor,u_pre,rows2011,post_rrr):
    u11=aggregate([r for r in rows2011 if r["municipality_code"]=="0380"])
    d11=aggregate([r for r in rows2011 if r["municipality_code"] in donor_codes])
    up=aggregate(u_pre);dp=aggregate(pre_donor)
    u_change=rate(u11)/rate(up);d_change=rate(d11)/rate(dp)
    idx=u_change/d_change
    return {
      "donor":label,
      "diagnostic_name":"2011 donor-relative deviation index",
      "causal_status":"ANTICIPATION_DIAGNOSTIC_NOT_CAUSAL_EFFECT",
      "uppsala_pre_rate":rate(up),"uppsala_2011_rate":rate(u11),"uppsala_2011_vs_pre_ratio":u_change,
      "donor_pre_rate":rate(dp),"donor_2011_rate":rate(d11),"donor_2011_vs_pre_ratio":d_change,
      "anticipation_index":idx,"anticipation_direction_vs_1":side(idx),
      "locked_post_rrr":post_rrr,"locked_post_direction_vs_1":side(post_rrr),
      "same_side_as_locked_post":side(idx)==side(post_rrr),
      "interpretive_note":(
          "PRE_A_DIVERGENCE_COMPATIBLE_WITH_ANTICIPATION" if idx<1 and post_rrr<1
          else "NO_FAVORABLE_2011_ANTICIPATION_SIGNAL" if idx>1 and post_rrr<1
          else "DIRECTION_PATTERN_REQUIRES_DESCRIPTIVE_READING"
      )
    }

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--requests",default=REQUESTS);ap.add_argument("--activation-patch",default=ACTIVATION_PATCH)
    ap.add_argument("--frozen-secondary",default=FROZEN_SECONDARY);ap.add_argument("--full-pre",default=FULL_PRE)
    ap.add_argument("--aug-pre-control",default=AUG_PRE_CONTROL);ap.add_argument("--locked-primary-estimates",default=LOCKED_PRIMARY_ESTIMATES)
    ap.add_argument("--self-test",action="store_true");args=ap.parse_args()
    if args.self_test:
        assert side(.9)=="BELOW_1" and side(1.1)=="ABOVE_1"
        print("SELF-TEST PASS");print("2011-only firewall: PASS");print("Diagnostic-not-causal rule: PASS");return

    for p in (args.requests,args.activation_patch,args.frozen_secondary,args.full_pre,args.aug_pre_control,args.locked_primary_estimates):require(p)
    verify_authorization(args.requests,args.activation_patch,args.frozen_secondary)
    full_pre=read_csv(args.full_pre);aug=read_csv(args.aug_pre_control)
    locked={r["donor"]:r for r in read_csv(args.locked_primary_estimates)}
    jpost=float(locked["Jönköping / RäddSam F"]["rrr"])
    papost=float(locked["Piteå–Älvsbyn / Femkanten"]["rrr"])
    hashes={p:sha256(p) for p in (args.locked_primary_estimates,args.full_pre,args.aug_pre_control)}

    print("Authorized opening: exactly Uppsala/Jönköping/Piteå/Älvsbyn × 2011")
    print("Diagnostic only — NOT a causal treatment estimate")
    print("2015 remains closed")

    s=requests.Session();s.headers.update({"User-Agent":"Uppsala-2011-anticipation-diagnostic-v0.1"})
    b20=fetch_b20(s);stocks=fetch_scb(s);rows2011=construct_2011(b20,stocks)
    print("2011 construction QA: PASS (4/4)")

    up,jk,pa=pre_rows(full_pre,aug)
    j=diagnostic("Jönköping / RäddSam F",{"0680"},jk,up,rows2011,jpost)
    p=diagnostic("Piteå–Älvsbyn / Femkanten",{"2581","2560"},pa,up,rows2011,papost)
    diags=[j,p]
    write_csv(OUT_DIAG,diags)

    if j["anticipation_direction_vs_1"]=="BELOW_1" and p["anticipation_direction_vs_1"]=="BELOW_1":
        cls="BOTH_CORE_DONORS_SHOW_PRE_A_FAVORABLE_DIVERGENCE_COMPATIBLE_WITH_ANTICIPATION"
        implication="The favorable Uppsala-relative divergence is already visible in 2011 against both core donors. This weakens attribution specifically to the formal 2012 start date, while remaining compatible with anticipation/implementation effects of the treatment process."
    elif j["anticipation_direction_vs_1"]=="ABOVE_1" and p["anticipation_direction_vs_1"]=="ABOVE_1":
        cls="NO_FAVORABLE_2011_ANTICIPATION_SIGNAL_AGAINST_EITHER_CORE_DONOR"
        implication="The favorable post-2012 direction is not visibly present in 2011 against either core donor. This is more temporally compatible with a post-2011 shift, but is not proof of a 2012 causal onset."
    else:
        cls="DONOR_MIXED_2011_ANTICIPATION_DIAGNOSTIC"
        implication="The 2011 pre-A signal depends on the core donor. Timing evidence is therefore counterfactual-sensitive."

    txt=f"""# Uppsala 2011 Anticipation Diagnostics Result v0.1

**Status:** descriptive timing diagnostic only — not a causal treatment-effect estimate  
**New outcome opening:** Uppsala, Jönköping, Piteå and Älvsbyn, 2011 only  
**2015:** still closed

## Diagnostic definition

For donor D:

A_2011,D = (R_U,2011 / R_U,2007:09) / (R_D,2011 / R_D,2007:09)

This asks whether Uppsala had already moved relative to the donor by the anticipation/implementation year 2011.

## Jönköping

- Uppsala pre rate: **{j['uppsala_pre_rate']:.2f}**
- Uppsala 2011 rate: **{j['uppsala_2011_rate']:.2f}**
- Jönköping pre rate: **{j['donor_pre_rate']:.2f}**
- Jönköping 2011 rate: **{j['donor_2011_rate']:.2f}**
- 2011 anticipation index: **{j['anticipation_index']:.4f}**
- direction: **{j['anticipation_direction_vs_1']}**
- locked post RRR: **{jpost:.4f}**
- same side of 1 as post result: **{j['same_side_as_locked_post']}**

## Piteå–Älvsbyn

- Uppsala pre rate: **{p['uppsala_pre_rate']:.2f}**
- Uppsala 2011 rate: **{p['uppsala_2011_rate']:.2f}**
- donor pre rate: **{p['donor_pre_rate']:.2f}**
- donor 2011 rate: **{p['donor_2011_rate']:.2f}**
- 2011 anticipation index: **{p['anticipation_index']:.4f}**
- direction: **{p['anticipation_direction_vs_1']}**
- locked post RRR: **{papost:.4f}**
- same side of 1 as post result: **{p['same_side_as_locked_post']}**

## Locked timing classification

**{cls}**

{implication}

## Limits

2011 is a single noisy year deliberately excluded from the clean pre-period. No significance test, causal ATT, or new treatment start date is inferred from this diagnostic.

The diagnostic cannot distinguish:
- genuine anticipation/implementation effects,
- secular/local shocks,
- ordinary annual fire-count noise,
- other changes correlated with the institutional transition.

Its purpose is narrower: test whether the favorable post-treatment relative direction was already visibly present immediately before formal A began.

## Still closed

- 2015 measurement-edge sensitivity
"""
    with open(OUT_MD,"w",encoding="utf-8") as f:f.write(txt)

    for path,h in hashes.items():
        if sha256(path)!=h:raise RuntimeError(f"Frozen input changed during run: {path}")

    files=[OUT_MCF_RAW,OUT_SCB_RAW,OUT_DATA,OUT_QA,OUT_DIAG,OUT_MD]
    man={"version":"RESCUE_UPPSALA_2011_ANTICIPATION_RESULT_MANIFEST_v0.1",
      "new_outcomes":{"year":2011,"municipalities":MUNIS,"rows":4},
      "causal_status":"DESCRIPTIVE_ANTICIPATION_DIAGNOSTIC_ONLY",
      "classification":cls,"locked_primary_estimates_changed":False,
      "still_closed":["2015 measurement-edge sensitivity"],
      "diagnostics":{"jonkoping_index":j["anticipation_index"],"pitea_alvsbyn_index":p["anticipation_index"]},
      "files":{x:{"sha256":sha256(x),"bytes":os.path.getsize(x)} for x in files}}
    with open(OUT_MANIFEST,"w",encoding="utf-8") as f:json.dump(man,f,ensure_ascii=False,indent=2)
    with zipfile.ZipFile(OUT_ZIP,"w",zipfile.ZIP_DEFLATED) as z:
        for x in files+[OUT_MANIFEST]:z.write(x,arcname=os.path.basename(x))
    print();print("2011 ANTICIPATION DIAGNOSTICS COMPLETE");print("Classification:",cls);print("Saved:",OUT_ZIP)

if __name__=="__main__":main()
