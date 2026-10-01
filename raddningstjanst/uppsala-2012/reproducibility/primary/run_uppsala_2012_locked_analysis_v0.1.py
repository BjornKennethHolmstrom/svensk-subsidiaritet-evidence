#!/usr/bin/env python3
import argparse, csv, math

PRE_CONTROL = "RESCUE_UPPSALA_CONTROL_PREMATCH_DATA_v0.1.csv"
UPP_PRE = "RESCUE_FIRE_B20_MUNICIPALITY_YEAR_WITH_POP_v0.1.1.csv"
EXPECTED_POST = {(code, year) for code in ("0380","0680","2581","2560") for year in (2012,2013,2014)}

def read_csv(path):
    with open(path, encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))

def write_csv(path, rows):
    with open(path, "w", encoding="utf-8", newline="") as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)

def inum(r,k): return int(float(r[k]))
def fnum(r,k): return float(r[k])

def aggregate(rows):
    return {
        "primary":sum(inum(r,"primary_beyond_start_object_n") for r in rows),
        "room":sum(inum(r,"sensitivity_beyond_start_room_n") for r in rows),
        "cell":sum(inum(r,"sensitivity_beyond_firecell_n") for r in rows),
        "valid":sum(inum(r,"valid_extent_n") for r in rows),
        "missing":sum(inum(r,"extent_missing_n") for r in rows),
        "all":sum(inum(r,"all_b20_records_n") for r in rows),
        "population":sum(fnum(r,"population") for r in rows),
    }

def rate(a): return a["primary"]/a["population"]*100000.0
def share(a,k): return a[k]/a["valid"] if a["valid"] else float("nan")

def rrr(u_pre,u_post,d_pre,d_post,override=None):
    def c(a,label): return a["primary"] if override is None else override[label]
    up,ur,dp,dr=c(u_post,"u_post"),c(u_pre,"u_pre"),c(d_post,"d_post"),c(d_pre,"d_pre")
    if ur==0 or dr==0: return float("nan")
    u_irr=(up/u_post["population"])/(ur/u_pre["population"])
    d_irr=(dp/d_post["population"])/(dr/d_pre["population"])
    if d_irr==0: return float("inf")
    return u_irr/d_irr

def ci95(u_pre,u_post,d_pre,d_post):
    point=rrr(u_pre,u_post,d_pre,d_post)
    counts=[u_post["primary"],u_pre["primary"],d_post["primary"],d_pre["primary"]]
    if any(c<=0 for c in counts) or not math.isfinite(point) or point<=0: return point,None,None
    se=math.sqrt(sum(1/c for c in counts)); z=1.959963984540054
    return point, math.exp(math.log(point)-z*se), math.exp(math.log(point)+z*se)

def missing_bounds(u_pre,u_post,d_pre,d_post):
    lo={"u_post":u_post["primary"],"u_pre":u_pre["primary"]+u_pre["missing"],"d_post":d_post["primary"]+d_post["missing"],"d_pre":d_pre["primary"]}
    hi={"u_post":u_post["primary"]+u_post["missing"],"u_pre":u_pre["primary"],"d_post":d_post["primary"],"d_pre":d_pre["primary"]+d_pre["missing"]}
    return rrr(u_pre,u_post,d_pre,d_post,lo), rrr(u_pre,u_post,d_pre,d_post,hi)

def period_rows(rows,codes,years):
    return [r for r in rows if str(r["municipality_code"]).zfill(4) in codes and int(r["year"]) in years]

def annual_rates(rows,codes,years):
    out={}
    for y in years:
        a=aggregate(period_rows(rows,codes,{y}))
        out[y]=a["primary"]/a["population"]*100000
    return out

def geom_rrr(pre,post,donor_codes):
    up=annual_rates(pre,{"0380"},{2007,2008,2009})
    dp=annual_rates(pre,donor_codes,{2007,2008,2009})
    uq=annual_rates(post,{"0380"},{2012,2013,2014})
    dq=annual_rates(post,donor_codes,{2012,2013,2014})
    pre_rat=[up[y]/dp[y] for y in (2007,2008,2009)]
    post_rat=[uq[y]/dq[y] for y in (2012,2013,2014)]
    if any(x<=0 for x in pre_rat+post_rat): return None
    return math.exp(sum(math.log(x) for x in post_rat)/3 - sum(math.log(x) for x in pre_rat)/3)

def estimate(label,donor_codes,pre,post):
    u_pre=aggregate(period_rows(pre,{"0380"},{2007,2008,2009}))
    u_post=aggregate(period_rows(post,{"0380"},{2012,2013,2014}))
    d_pre=aggregate(period_rows(pre,donor_codes,{2007,2008,2009}))
    d_post=aggregate(period_rows(post,donor_codes,{2012,2013,2014}))
    point,lo,hi=ci95(u_pre,u_post,d_pre,d_post)
    mlo,mhi=missing_bounds(u_pre,u_post,d_pre,d_post)
    geom=geom_rrr(pre,post,donor_codes)
    return {
        "donor":label,
        "rrr":point,
        "effect_percent":(point-1)*100 if math.isfinite(point) else "",
        "count_process_ci_low":"" if lo is None else lo,
        "count_process_ci_high":"" if hi is None else hi,
        "absolute_did_per_100k":(rate(u_post)-rate(u_pre))-(rate(d_post)-rate(d_pre)),
        "year_balanced_geometric_rrr":"" if geom is None else geom,
        "missingness_worstcase_rrr_low":mlo,
        "missingness_worstcase_rrr_high":mhi,
        "secondary_share_did_pp":((share(u_post,"primary")-share(u_pre,"primary"))-(share(d_post,"primary")-share(d_pre,"primary")))*100,
        "beyond_start_room_share_did_pp":((share(u_post,"room")-share(u_pre,"room"))-(share(d_post,"room")-share(d_pre,"room")))*100,
        "beyond_firecell_share_did_pp":((share(u_post,"cell")-share(u_pre,"cell"))-(share(d_post,"cell")-share(d_pre,"cell")))*100,
        "upp_pre_count":u_pre["primary"],"upp_post_count":u_post["primary"],
        "donor_pre_count":d_pre["primary"],"donor_post_count":d_post["primary"],
    }

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--post",required=True)
    ap.add_argument("--pre-control",default=PRE_CONTROL)
    ap.add_argument("--uppsala-pre",default=UPP_PRE)
    ap.add_argument("--jonkoping-a0-pass",action="store_true")
    ap.add_argument("--out-estimates",default="RESCUE_UPPSALA_2012_LOCKED_ESTIMATES_v0.1.csv")
    ap.add_argument("--out-report",default="Raddningstjanst-Uppsala-2012-Locked-Analysis-Result-v0.1.md")
    args=ap.parse_args()

    if not args.jonkoping_a0_pass:
        raise SystemExit("PRIMARY ANALYSIS BLOCKED: --jonkoping-a0-pass is required after documented pre-outcome structural verification.")

    post=read_csv(args.post)
    keys={(str(r["municipality_code"]).zfill(4),int(r["year"])) for r in post}
    if keys!=EXPECTED_POST or len(post)!=12:
        raise RuntimeError(f"Strict post file must contain exactly 12 rows. Missing={sorted(EXPECTED_POST-keys)} extra={sorted(keys-EXPECTED_POST)} rows={len(post)}")

    required={"municipality_code","year","primary_beyond_start_object_n","sensitivity_beyond_start_room_n","sensitivity_beyond_firecell_n","valid_extent_n","extent_missing_n","all_b20_records_n","population"}
    absent=required-set(post[0])
    if absent: raise RuntimeError(f"Post file missing required columns: {sorted(absent)}")
    if any(float(r["population"])<=0 for r in post): raise RuntimeError("Non-positive population denominator.")

    controls=read_csv(args.pre_control)
    upp=read_csv(args.uppsala_pre)
    pre=[r for r in upp if str(r["municipality_code"]).zfill(4)=="0380" and int(r["year"]) in (2007,2008,2009)]
    pre += [r for r in controls if str(r["municipality_code"]).zfill(4) in {"0680","2581","2560"} and int(r["year"]) in (2007,2008,2009)]
    expected_pre={(code,year) for code in ("0380","0680","2581","2560") for year in (2007,2008,2009)}
    pre_keys={(str(r["municipality_code"]).zfill(4),int(r["year"])) for r in pre}
    if pre_keys!=expected_pre or len(pre)!=12: raise RuntimeError("Frozen pre data mismatch.")

    estimates=[
        estimate("Jönköping / RäddSam F",{"0680"},pre,post),
        estimate("Piteå–Älvsbyn / Femkanten",{"2581","2560"},pre,post),
    ]
    primary,secondary=estimates
    def side(x):
        if not math.isfinite(float(x)): return "BOUNDARY"
        if float(x)<1:return "BELOW_1"
        if float(x)>1:return "ABOVE_1"
        return "EQUAL_1"
    consistent=side(primary["rrr"])==side(secondary["rrr"])
    for i,r in enumerate(estimates):
        r["direction_vs_1"]=side(r["rrr"])
        r["primary_secondary_sign_consistent"]=consistent
        r["interpretive_role"]="PRIMARY" if i==0 else "PRESPECIFIED_SECONDARY"
    write_csv(args.out_estimates,estimates)

    count_cross=(primary["count_process_ci_low"]=="" or primary["count_process_ci_low"]<=1<=primary["count_process_ci_high"])
    miss_cross=primary["missingness_worstcase_rrr_low"]<=1<=primary["missingness_worstcase_rrr_high"]
    report=f"""# Uppsala 2012 Locked Analysis Result v0.1

Primary Jönköping RRR: **{primary['rrr']:.4f}**
Differential percent change: **{primary['effect_percent']:+.1f}%**
Absolute controlled difference: **{primary['absolute_did_per_100k']:+.2f} per 100,000**
Count-process interval: **{primary['count_process_ci_low']} – {primary['count_process_ci_high']}**
Missingness RRR bounds: **{primary['missingness_worstcase_rrr_low']:.4f} – {primary['missingness_worstcase_rrr_high']:.4f}**

Prespecified Piteå–Älvsbyn RRR: **{secondary['rrr']:.4f}**

Flags:
- primary direction: **{side(primary['rrr'])}**
- count-process interval crosses 1: **{count_cross}**
- primary/secondary donor sign consistent: **{consistent}**
- missingness bounds cross 1: **{miss_cross}**
- donor-sensitive/inconclusive by protocol: **{not consistent}**

The count-process interval is not a full causal-confidence interval. No conventional few-cluster p-value is reported.
"""
    with open(args.out_report,"w",encoding="utf-8") as f: f.write(report)
    print("Locked primary analysis complete.")
    print("Saved:",args.out_estimates)
    print("Saved:",args.out_report)

if __name__=="__main__":
    main()
