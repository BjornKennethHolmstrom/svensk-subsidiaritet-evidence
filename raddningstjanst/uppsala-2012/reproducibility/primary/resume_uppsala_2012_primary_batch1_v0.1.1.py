#!/usr/bin/env python3
"""
Resume Primary Batch 1 after pre-control schema bug — implementation patch v0.1.1.

WHY THIS EXISTS
---------------
The frozen analysis runner v0.1 expects the pre-control input to contain:
  sensitivity_beyond_start_room_n
  sensitivity_beyond_firecell_n

But RESCUE_UPPSALA_CONTROL_PREMATCH_DATA_v0.1.csv was intentionally compact
and only retained the primary numerator, valid total, missing total, population
and primary rate.

This patch DOES NOT change the estimator or any analysis rule.

It:
1. requires the already-constructed strict 12-row post file;
2. verifies its exact authorized scope and hashes it;
3. verifies the original frozen analysis runner against the protocol manifest;
4. augments Piteå/Älvsbyn pre-2009 threshold counts from the already-existing
   full pre-treatment B20 panel;
5. fetches ONLY Jönköping 2007–2009 B20 categories to recover the two missing
   threshold counts;
6. verifies Jönköping's primary/valid/missing counts exactly match the already
   locked pre-match data before accepting the augmentation;
7. invokes the ORIGINAL HASH-FROZEN analysis runner v0.1 with the augmented
   pre-control file;
8. verifies the post file was not modified;
9. writes an implementation-patch manifest and result package.

NO POST-TREATMENT OUTCOME IS FETCHED.
"""

import argparse
import csv
import hashlib
import io
import json
import os
import re
import subprocess
import sys
import time
import zipfile
from collections import defaultdict

import requests

PROTOCOL_MANIFEST = "RESCUE_UPPSALA_2012_PROTOCOL_MANIFEST_v0.1.json"
ACTIVATION_PATCH = "RESCUE_UPPSALA_2012_PROTOCOL_ACTIVATION_PATCH_v0.1.json"
LOCKED_RUNNER = "run_uppsala_2012_locked_analysis_v0.1.py"

PRE_CONTROL = "RESCUE_UPPSALA_CONTROL_PREMATCH_DATA_v0.1.csv"
FULL_PRE_PANEL = "RESCUE_FIRE_B20_MUNICIPALITY_YEAR_WITH_POP_v0.1.1.csv"
POST_FILE = "RESCUE_UPPSALA_2012_PRIMARY_POST_DATA_v0.1.csv"
POST_QA = "RESCUE_UPPSALA_2012_PRIMARY_POST_QA_v0.1.csv"

AUGMENTED_PRE = "RESCUE_UPPSALA_CONTROL_PREMATCH_DATA_AUGMENTED_v0.1.1.csv"
JKPG_PRE_RAW = "RESCUE_JONKOPING_PREMATCH_THRESHOLD_RAW_v0.1.1.csv"
ESTIMATES = "RESCUE_UPPSALA_2012_LOCKED_ESTIMATES_v0.1.csv"
RESULT_MD = "Raddningstjanst-Uppsala-2012-Locked-Analysis-Result-v0.1.md"
PATCH_MANIFEST = "RESCUE_UPPSALA_2012_IMPLEMENTATION_PATCH_v0.1.1.json"
RESULT_ZIP = "raddningstjanst-uppsala-2012-primary-batch1-locked-result-v0.1.1.zip"

MCF_ENDPOINT = "https://statistik.mcf.se/PXWeb/api/v1/sv/PxData/START/B/B2/B20"
EXTENT_CODES = ["6","1","2","3","4","5","-1"]
LABEL_TO_CODE = {
    "Brandtillbud utan skada": "6",
    "I det objekt som först antändes": "1",
    "I utrymmet där branden startade": "2",
    "I flera utrymmen i samma brandcell": "3",
    "I flera brandceller i samma byggnad": "4",
    "I flera byggnader": "5",
    "Uppgift saknas": "-1",
}
EXPECTED_POST = {
    (code, year)
    for code in ("0380","0680","2581","2560")
    for year in (2012,2013,2014)
}


def sha256(path):
    h=hashlib.sha256()
    with open(path,"rb") as f:
        for chunk in iter(lambda:f.read(1024*1024),b""):
            h.update(chunk)
    return h.hexdigest()


def read_csv(path):
    with open(path,encoding="utf-8-sig",newline="") as f:
        return list(csv.DictReader(f))


def write_csv(path,rows):
    if not rows:
        raise RuntimeError(f"Refusing to write empty CSV: {path}")
    with open(path,"w",encoding="utf-8",newline="") as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)


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


def require(path):
    if not os.path.exists(path):
        raise RuntimeError(f"Required file missing: {path}")


def verify_frozen_runner(protocol_manifest, runner):
    with open(protocol_manifest,encoding="utf-8") as f:
        manifest=json.load(f)
    expected=manifest.get("files",{}).get(os.path.basename(runner),{}).get("sha256")
    actual=sha256(runner)
    if not expected or expected!=actual:
        raise RuntimeError(
            "Frozen analysis-runner hash mismatch.\n"
            f"expected={expected}\nactual={actual}"
        )
    return actual


def verify_activation(protocol_manifest, activation_patch):
    with open(activation_patch,encoding="utf-8") as f:
        activation=json.load(f)
    if activation.get("base_protocol_manifest_sha256")!=sha256(protocol_manifest):
        raise RuntimeError("Activation patch does not match the frozen protocol manifest.")
    if activation.get("primary_unmask_authorized") is not True:
        raise RuntimeError("Primary Batch 1 is not authorized.")
    gate=activation.get("activation_gate_update",{})
    if gate.get("gate")!="jonkoping_A0_through_2014" or gate.get("new_status")!="PASS":
        raise RuntimeError("Jönköping A=0 gate is not PASS.")


def verify_post(path):
    rows=read_csv(path)
    keys={(str(r["municipality_code"]).zfill(4),int(r["year"])) for r in rows}
    if len(rows)!=12 or keys!=EXPECTED_POST:
        raise RuntimeError(
            f"Existing post file is not the authorized 12-row Batch 1. "
            f"rows={len(rows)} missing={sorted(EXPECTED_POST-keys)} "
            f"extra={sorted(keys-EXPECTED_POST)}"
        )
    required={
        "municipality_code","year","primary_beyond_start_object_n",
        "sensitivity_beyond_start_room_n","sensitivity_beyond_firecell_n",
        "valid_extent_n","extent_missing_n","all_b20_records_n","population"
    }
    absent=required-set(rows[0].keys())
    if absent:
        raise RuntimeError(f"Existing post file missing required columns: {sorted(absent)}")
    return rows


def verify_post_qa(path):
    if not os.path.exists(path):
        print("NOTE: post-QA CSV not found; exact 12-row post schema will still be verified.")
        return
    rows=read_csv(path)
    bad=[r for r in rows if str(r.get("qa_status","")).upper()!="PASS"]
    if bad:
        raise RuntimeError(f"Post QA contains non-PASS rows: {bad[:3]}")
    if len(rows)!=12:
        raise RuntimeError(f"Expected 12 post-QA rows; got {len(rows)}")


def full_panel_lookup(path):
    rows=read_csv(path)
    return {
        (str(r["municipality_code"]).zfill(4),int(r["year"])):r
        for r in rows
    }


def fetch_jkpg_thresholds(session):
    body={
        "query":[
            {"code":"BIBomfSlutligId","selection":{"filter":"item","values":EXTENT_CODES}},
            {"code":"kommun","selection":{"filter":"item","values":["0680"]}},
            {"code":"ContentsCode","selection":{"filter":"item","values":["B20"]}},
            {"code":"ar","selection":{"filter":"item","values":["2007","2008","2009"]}},
        ],
        "response":{"format":"csv"}
    }

    print("Fetching ONLY Jönköping pre-treatment B20 2007–2009 for missing threshold counts...")
    r=post_backoff(session,MCF_ENDPOINT,body)
    r.raise_for_status()

    with open(JKPG_PRE_RAW,"w",encoding="utf-8",newline="") as f:
        f.write(r.text)

    rows=parse_csv(r.text)
    by=defaultdict(dict)

    for row in rows:
        code=code_from_place(row.get("plats",""))
        label=row.get("slutlig omfattning","")
        if code!="0680" or label not in LABEL_TO_CODE:
            continue
        cat=LABEL_TO_CODE[label]
        for year in (2007,2008,2009):
            s=str(row.get(str(year),"")).strip()
            if s in ("","..",".","-"):
                raise RuntimeError(f"Missing/suppressed Jönköping pre value: {year} {label}: {s!r}")
            value=int(s)
            if value<0:
                raise RuntimeError("Negative B20 count.")
            by[year][cat]=value

    for year in (2007,2008,2009):
        if set(by[year])!=set(EXTENT_CODES):
            raise RuntimeError(
                f"Jönköping {year}: expected 7 extent categories; got {sorted(by[year])}"
            )

    return by


def augment_pre(pre_control_path,full_pre_panel_path,jkpg):
    pre=read_csv(pre_control_path)
    full=full_panel_lookup(full_pre_panel_path)

    augmented=[]
    needed_codes={"0680","2581","2560"}

    for row in pre:
        out=dict(row)
        code=str(row["municipality_code"]).zfill(4)
        year=int(row["year"])

        out["sensitivity_beyond_start_room_n"]=""
        out["sensitivity_beyond_firecell_n"]=""
        out["threshold_component_source"]="NOT_REQUIRED_FOR_PRIMARY_RUNNER"

        if code=="0680" and year in (2007,2008,2009):
            d=jkpg[year]
            primary=sum(d[c] for c in ("2","3","4","5"))
            valid=sum(d[c] for c in ("6","1","2","3","4","5"))
            missing=d["-1"]

            # Critical consistency check: this must be the SAME pre-match dataset.
            if primary!=int(row["primary_beyond_start_object_n"]):
                raise RuntimeError(
                    f"Jönköping {year} primary numerator changed: "
                    f"locked={row['primary_beyond_start_object_n']} fetched={primary}"
                )
            if valid!=int(row["valid_extent_n"]):
                raise RuntimeError(
                    f"Jönköping {year} valid total changed: "
                    f"locked={row['valid_extent_n']} fetched={valid}"
                )
            if missing!=int(row["extent_missing_n"]):
                raise RuntimeError(
                    f"Jönköping {year} missing count changed: "
                    f"locked={row['extent_missing_n']} fetched={missing}"
                )

            out["sensitivity_beyond_start_room_n"]=sum(d[c] for c in ("3","4","5"))
            out["sensitivity_beyond_firecell_n"]=sum(d[c] for c in ("4","5"))
            out["threshold_component_source"]="MCF_B20_PRE_2007_2009_SCHEMA_COMPLETION_v0.1.1"

        elif code in {"2581","2560"} and year in (2007,2008,2009):
            key=(code,year)
            if key not in full:
                raise RuntimeError(f"Full pre-treatment panel missing {key}")
            src=full[key]

            # Verify primary fields against the locked compact pre-match row.
            for field in ("primary_beyond_start_object_n","valid_extent_n","extent_missing_n"):
                if int(float(src[field]))!=int(float(row[field])):
                    raise RuntimeError(
                        f"{code} {year} {field} differs between locked pre-match "
                        f"and full pre panel: {row[field]} vs {src[field]}"
                    )

            out["sensitivity_beyond_start_room_n"]=int(float(src["sensitivity_beyond_start_room_n"]))
            out["sensitivity_beyond_firecell_n"]=int(float(src["sensitivity_beyond_firecell_n"]))
            out["threshold_component_source"]="EXISTING_FULL_PRETREATMENT_B20_PANEL"

        augmented.append(out)

    # Ensure all rows the frozen runner will use have the two fields.
    missing=[]
    for r in augmented:
        code=str(r["municipality_code"]).zfill(4)
        year=int(r["year"])
        if code in needed_codes and year in (2007,2008,2009):
            if str(r["sensitivity_beyond_start_room_n"]).strip()=="" or str(r["sensitivity_beyond_firecell_n"]).strip()=="":
                missing.append((code,year))

    if missing:
        raise RuntimeError(f"Threshold augmentation incomplete: {missing}")

    write_csv(AUGMENTED_PRE,augmented)
    return augmented


def run_original_runner(args):
    cmd=[
        sys.executable,args.locked_runner,
        "--post",args.post,
        "--pre-control",AUGMENTED_PRE,
        "--uppsala-pre",args.uppsala_pre,
        "--jonkoping-a0-pass",
        "--out-estimates",ESTIMATES,
        "--out-report",RESULT_MD,
    ]
    print("Running ORIGINAL hash-frozen estimator runner:")
    print("  "+" ".join(cmd))
    subprocess.run(cmd,check=True)


def package_result(post_hash_before,runner_hash):
    files=[
        POST_FILE,
        POST_QA,
        AUGMENTED_PRE,
        JKPG_PRE_RAW,
        ESTIMATES,
        RESULT_MD,
    ]
    files=[f for f in files if os.path.exists(f)]

    patch={
        "version":"RESCUE_UPPSALA_2012_IMPLEMENTATION_PATCH_v0.1.1",
        "patch_type":"IMPLEMENTATION_DATA_SCHEMA_COMPLETION",
        "method_change":False,
        "outcome_scope_change":False,
        "donor_change":False,
        "time_window_change":False,
        "estimator_change":False,
        "reason":"Frozen runner expected two preregistered secondary threshold count columns that the compact pre-control export omitted.",
        "fix":"Append those pre-treatment threshold columns; Jönköping recovered from MCF B20 2007–2009 only; Piteå/Älvsbyn recovered from the existing full pre-treatment B20 panel.",
        "locked_runner_modified":False,
        "locked_runner_sha256":runner_hash,
        "post_file_refetched":False,
        "post_file_sha256_before_resume":post_hash_before,
        "post_file_sha256_after_resume":sha256(POST_FILE),
        "post_file_unchanged":post_hash_before==sha256(POST_FILE),
        "new_post_outcomes_opened_by_patch":False,
        "files":{
            os.path.basename(f):{"sha256":sha256(f),"bytes":os.path.getsize(f)}
            for f in files
        }
    }
    with open(PATCH_MANIFEST,"w",encoding="utf-8") as f:
        json.dump(patch,f,ensure_ascii=False,indent=2)

    with zipfile.ZipFile(RESULT_ZIP,"w",zipfile.ZIP_DEFLATED) as z:
        for f in files+[PATCH_MANIFEST]:
            z.write(f,arcname=os.path.basename(f))

    return patch


def self_test(args):
    # Offline checks that do not touch post outcomes.
    require(args.pre_control)
    require(args.full_pre_panel)
    require(args.locked_runner)
    runner_hash=verify_frozen_runner(args.protocol_manifest,args.locked_runner)

    full=full_panel_lookup(args.full_pre_panel)
    for code in ("2581","2560"):
        for year in (2007,2008,2009):
            r=full[(code,year)]
            assert "sensitivity_beyond_start_room_n" in r
            assert "sensitivity_beyond_firecell_n" in r

    print("SELF-TEST PASS")
    print("Frozen runner hash: PASS")
    print("Piteå/Älvsbyn pre threshold source: PASS")
    print("Jönköping live pre-only fetch not executed in self-test.")


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--protocol-manifest",default=PROTOCOL_MANIFEST)
    ap.add_argument("--activation-patch",default=ACTIVATION_PATCH)
    ap.add_argument("--locked-runner",default=LOCKED_RUNNER)
    ap.add_argument("--pre-control",default=PRE_CONTROL)
    ap.add_argument("--full-pre-panel",default=FULL_PRE_PANEL)
    ap.add_argument("--uppsala-pre",default=FULL_PRE_PANEL)
    ap.add_argument("--post",default=POST_FILE)
    ap.add_argument("--post-qa",default=POST_QA)
    ap.add_argument("--self-test",action="store_true")
    args=ap.parse_args()

    for path in (
        args.protocol_manifest,args.activation_patch,args.locked_runner,
        args.pre_control,args.full_pre_panel
    ):
        require(path)

    if args.self_test:
        self_test(args)
        return

    require(args.post)
    verify_activation(args.protocol_manifest,args.activation_patch)
    runner_hash=verify_frozen_runner(args.protocol_manifest,args.locked_runner)
    verify_post(args.post)
    verify_post_qa(args.post_qa)

    post_hash_before=sha256(args.post)

    print("Implementation patch v0.1.1 verification: PASS")
    print("Existing Primary Batch 1 post file: PASS, exactly 12 authorized rows")
    print("Existing post file SHA256:",post_hash_before)
    print("Original frozen analysis runner SHA256:",runner_hash)
    print("No post-treatment data will be fetched.")

    session=requests.Session()
    session.headers.update({"User-Agent":"Uppsala-2012-schema-completion-v0.1.1"})

    jkpg=fetch_jkpg_thresholds(session)
    augment_pre(args.pre_control,args.full_pre_panel,jkpg)

    print("Pre-control schema completion: PASS")
    print("Jönköping primary/valid/missing consistency against locked pre-match data: PASS")
    print("Running frozen estimator now...")

    run_original_runner(args)

    if sha256(args.post)!=post_hash_before:
        raise RuntimeError("Existing post file changed during resume — refusing result.")

    patch=package_result(post_hash_before,runner_hash)
    if not patch["post_file_unchanged"]:
        raise RuntimeError("Post hash changed unexpectedly.")

    print()
    print("PRIMARY BATCH 1 LOCKED ANALYSIS COMPLETE")
    print("No post-treatment refetch occurred.")
    print("Saved:",ESTIMATES)
    print("Saved:",RESULT_MD)
    print("Saved:",PATCH_MANIFEST)
    print("Saved:",RESULT_ZIP)


if __name__=="__main__":
    main()
