"""
Run with:  python generate_dummy_data.py [--n 75] [--out dummy_data] [--seed 42]

Generates synthetic RMT23345 CSVs matching the raw column structure of the
real data files, so they are compatible with normalize_RMT23345_datetimes.R.

Date fields use YYYY-MM-DD (date-only) and time fields use HH:MM so the
R normalization script will convert them to ISO 8601 UTC.

PIN is generated in post-prepare format (after DPD join by
prepare_RMT23345_PIN.R), since that join requires the real DPD database.

CLM and LAB column structures are approximate — update once real headers
are confirmed.
"""
import argparse
import os
import random
from datetime import datetime, timedelta

import pandas as pd
import numpy as np

# ---------------------------------------------------------------------------
# Lookup tables
# ---------------------------------------------------------------------------

HOSPITALS = [
    "Royal Alexandra Hospital", "University of Alberta Hospital",
    "Grey Nuns Community Hospital", "Misericordia Community Hospital",
    "Foothills Medical Centre", "Peter Lougheed Centre",
    "Rockyview General Hospital", "Red Deer Regional Hospital",
    "Grande Prairie Regional Hospital", "Medicine Hat Regional Hospital",
]

IBD_DX = [
    "Crohn's disease of small intestine",
    "Crohn's disease of large intestine",
    "Crohn's disease of small intestine and large intestine",
    "Ulcerative (chronic) pancolitis",
    "Ulcerative (chronic) proctosigmoiditis",
    "Ulcerative (chronic) enterocolitis",
    "Ulcerative (chronic) proctitis",
    "Indeterminate colitis",
    "Ileitis",
    "Proctocolitis",
]

NON_IBD_DX = [
    "General medical examination",
    "Acute upper respiratory infection, unspecified",
    "Essential (primary) hypertension",
    "Type 2 diabetes mellitus without complications",
    "Anaemia, unspecified",
    "Gastro-oesophageal reflux disease without oesophagitis",
    "Migraine, unspecified",
    "Low back pain",
    "Anxiety disorder, unspecified",
    "Iron deficiency anaemia",
]

PROC_CODES = [
    "Colonoscopy", "Flexible sigmoidoscopy", "Upper endoscopy",
    "Small bowel capsule endoscopy", "Blood test", "IV fluids",
    "Bowel resection", None, None, None,
]

DOCSVC = ["Gastroenterology", "Internal Medicine", "General Surgery", "Colorectal Surgery"]

CMG_IBD   = ["IBD - Small Bowel", "IBD - Large Bowel", "IBD - Unspecified", "Gastroenterology - Medical"]
CMG_OTHER = ["Rheumatology", "General Medicine", "Respiratory Medicine"]

# PIN — biologics (ATC → ingredient, brand, strength, unit, DIN)
BIOLOGICS = [
    dict(atc="L04AB02", ingredient="infliximab",    brand="REMICADE",  strength=100.0, unit="mg", dosage_unit="vial", din=2243197),
    dict(atc="L04AB04", ingredient="adalimumab",    brand="HUMIRA",    strength=40.0,  unit="mg", dosage_unit="syr",  din=2269090),
    dict(atc="L04AA33", ingredient="vedolizumab",   brand="ENTYVIO",   strength=300.0, unit="mg", dosage_unit="vial", din=2433060),
    dict(atc="L04AC05", ingredient="ustekinumab",   brand="STELARA",   strength=90.0,  unit="mg", dosage_unit="syr",  din=2443007),
    dict(atc="L04AB06", ingredient="golimumab",     brand="SIMPONI",   strength=50.0,  unit="mg", dosage_unit="syr",  din=2361469),
    dict(atc="L04AC18", ingredient="risankizumab",  brand="SKYRIZI",   strength=600.0, unit="mg", dosage_unit="vial", din=2504774),
    dict(atc="L04AF03", ingredient="upadacitinib",  brand="RINVOQ",    strength=45.0,  unit="mg", dosage_unit="tab",  din=2488868),
]

STEROIDS = [
    dict(atc="H02AB06", ingredient="prednisone",         brand="APO-PREDNISONE", strength=50.0,  unit="mg", dosage_unit="tab",  din=2356789, flare_dose=1),
    dict(atc="H02AB07", ingredient="prednisolone",        brand="PEDIAPRED",      strength=50.0,  unit="mg", dosage_unit="tab",  din=2014785, flare_dose=1),
    dict(atc="H02AB04", ingredient="methylprednisolone",  brand="SOLU-MEDROL",    strength=500.0, unit="mg", dosage_unit="vial", din=232378,  flare_dose=1),
]

OTHER_DRUGS = [
    dict(atc="A07EC02", ingredient="mesalazine",    brand="PENTASA",     strength=500.0, unit="mg", dosage_unit="tab", din=2083434),
    dict(atc="L04AX01", ingredient="azathioprine",  brand="IMURAN",      strength=50.0,  unit="mg", dosage_unit="tab", din=236942),
    dict(atc="A07EC01", ingredient="sulfasalazine", brand="SALAZOPYRIN", strength=500.0, unit="mg", dosage_unit="tab", din=585467),
]

LAB_TESTS = [
    dict(cd="HGB",  nm="HEMOGLOBIN",                     uom="g/L",     mu=120, sd=15,  lo=70,  hi=175),
    dict(cd="CRP",  nm="C REACTIVE PROTEIN",             uom="mg/L",    mu=12,  sd=20,  lo=0,   hi=150),
    dict(cd="WBC",  nm="WHITE BLOOD COUNT",              uom="x10e9/L", mu=8,   sd=2,   lo=3,   hi=20),
    dict(cd="ALB",  nm="ALBUMIN",                        uom="g/L",     mu=38,  sd=6,   lo=15,  hi=50),
    dict(cd="PLT",  nm="PLATELETS",                      uom="x10e9/L", mu=280, sd=80,  lo=80,  hi=600),
    dict(cd="ESR",  nm="ERYTHROCYTE SEDIMENTATION RATE", uom="mm/hr",   mu=20,  sd=15,  lo=1,   hi=100),
    dict(cd="FCAL", nm="FECAL CALPROTECTIN",             uom="ug/g",    mu=200, sd=300, lo=20,  hi=2000),
    dict(cd="FE",   nm="SERUM IRON",                     uom="umol/L",  mu=14,  sd=5,   lo=5,   hi=30),
    dict(cd="FERR", nm="FERRITIN",                       uom="ug/L",    mu=30,  sd=30,  lo=5,   hi=300),
    dict(cd="VB12", nm="VITAMIN B12",                    uom="pmol/L",  mu=280, sd=100, lo=80,  hi=700),
]

CLM_SERVICES = [
    "Colonoscopy", "Office visit - gastroenterology", "Office visit - general practice",
    "Sigmoidoscopy", "Upper endoscopy", "Infusion therapy",
    "Follow-up visit - internal medicine", "Emergency visit",
]

CLM_SPECIALTIES = [
    "GASTROENTEROLOGY", "INTERNAL MEDICINE", "GENERAL PRACTICE", "GENERAL SURGERY",
    "COLORECTAL SURGERY", "RHEUMATOLOGY", "RADIOLOGY", "EMERGENCY MEDICINE",
    "ANESTHESIOLOGY", "PATHOLOGY", "PSYCHIATRY", "DERMATOLOGY",
    "CARDIOLOGY", "RESPIROLOGY", "NEPHROLOGY", "HEMATOLOGY",
    "ONCOLOGY", "INFECTIOUS DISEASE", "ENDOCRINOLOGY", "UROLOGY",
]

DI_PROCEDURES = [
    dict(cd="XR001", desc="X-Ray Abdomen",                      modality="XR"),
    dict(cd="CT002", desc="CT Abdomen and Pelvis with contrast", modality="CT"),
    dict(cd="MR003", desc="MRI Small Bowel Enterography",        modality="MR"),
    dict(cd="US004", desc="Abdominal Ultrasound",                modality="US"),
    dict(cd="CT005", desc="CT Chest",                            modality="CT"),
    dict(cd="MR006", desc="MRI Pelvis",                          modality="MR"),
    dict(cd="XR007", desc="X-Ray Chest",                         modality="XR"),
    dict(cd="US008", desc="Pelvic Ultrasound",                   modality="US"),
]

# AMB-specific
TRIAGE_CODES = [1, 2, 3, 4, 5]
DISPOSITIONS = [
    ("01", "Discharged - routine"),
    ("02", "Discharged - home with referral"),
    ("04", "Admit - same institution"),
    ("05", "Transfer to acute care"),
    ("06", "Left without being seen"),
]
ABSTRACT_TYPES = ["A", "E", "O", "U"]

# DAD-specific
ADMIT_CATS = ["E", "U", "L", "C", "N"]
DAD_DISPS  = ["04", "06", "07", "09", "12"]

# REG-specific
ZONES = ["EDMONTON", "CALGARY", "CENTRAL", "NORTH", "SOUTH"]

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def rand_date(start: datetime, end: datetime) -> datetime:
    delta = (end - start).days
    return start + timedelta(days=random.randint(0, max(delta, 0)))

def iso_date(dt: datetime) -> str:
    """Date-only string — normalize_RMT23345_datetimes.R will convert to ISO UTC."""
    return dt.strftime("%Y-%m-%d")

def hhmm(dt: datetime) -> str:
    return dt.strftime("%H:%M")

def clamp(v, lo, hi):
    return max(lo, min(hi, v))

def lab_result(test: dict, flare: bool) -> str:
    mu = test["mu"] * (1.3 if flare and test["cd"] in ("CRP", "WBC", "PLT", "ESR", "FCAL") else 1.0)
    mu = mu * (0.8 if flare and test["cd"] in ("HGB", "ALB", "FE", "FERR") else 1.0)
    val = random.gauss(mu, test["sd"])
    return f"{round(clamp(val, test['lo'], test['hi']), 1)}"

# Normal ranges for abnormal flag generation
_NORMAL_RANGES = {
    "HGB":  (120, 160), "CRP": (0, 10),   "WBC": (4, 11),  "ALB": (35, 50),
    "PLT":  (150, 400), "ESR": (0, 20),   "FCAL": (0, 250), "FE": (9, 27),
    "FERR": (12, 150),  "VB12": (150, 700),
}

def _is_abnormal(test: dict, value: float, flare: bool) -> bool:
    lo, hi = _NORMAL_RANGES.get(test["cd"], (test["lo"], test["hi"]))
    return value < lo or value > hi

# ---------------------------------------------------------------------------
# Per-patient event generators
# ---------------------------------------------------------------------------

def gen_amb(patid, start, end, ibd_dx):
    rows = []
    for _ in range(random.randint(4, 12)):
        arrive = rand_date(start, end)
        depart = arrive + timedelta(hours=random.randint(1, 3))
        ibd    = random.random() < 0.65
        disp_code, disp_nm = random.choice(DISPOSITIONS)

        dx = {f"DXCODE{i}": None for i in range(1, 11)}
        dx["DXCODE1"] = random.choice(ibd_dx if ibd else NON_IBD_DX)
        if random.random() < 0.4:
            dx["DXCODE2"] = random.choice(NON_IBD_DX)

        proc = {f"PROCCODE{i}": None for i in range(1, 11)}
        p = random.choice(PROC_CODES)
        if p:
            proc["PROCCODE1"] = p

        prov = {f"PROVIDER_SVC{i}": None for i in range(1, 9)}
        prov["PROVIDER_SVC1"] = random.choice(DOCSVC)

        docsvc = {f"DOCSVC{i}": None for i in range(1, 6)}
        docsvc["DOCSVC1"] = random.choice(DOCSVC)

        row = dict(
            PATID=patid,
            TRIAGECODE=random.choice(TRIAGE_CODES),
            INST=random.choice(HOSPITALS),
            INSTFROM=None,
            INSTTO=None,
            ADMITBYAMB=random.choice([0, 1]),
            ArriveDt=iso_date(arrive),
            DispDt=iso_date(arrive) if random.random() > 0.2 else None,
            DepartDt=iso_date(depart) if random.random() > 0.2 else None,
            DISPOSITION=disp_code,
            DISP_NM=disp_nm,
            ABSTRACT_TYPE=random.choice(ABSTRACT_TYPES),
            MIS_CODE=random.choice(CLM_SERVICES + [None, None]),
            VISIT_TIME=hhmm(arrive),
            TriageDt=iso_date(arrive),
            TRIAGE_TIME=hhmm(arrive - timedelta(minutes=random.randint(5, 30))),
            CACS_CODE=random.choice(["01", "02", "03", None, None]),
            CACS_RIW=round(random.uniform(0.5, 3.0), 2) if random.random() < 0.5 else None,
        )
        row.update(dx)
        row.update(proc)
        row.update(prov)
        row.update(docsvc)
        rows.append(row)
    return rows


def gen_dad(patid, start, end, ibd_dx, flare_dates):
    rows = []
    dates_used = list(flare_dates)
    for _ in range(random.randint(0, 3)):
        if dates_used:
            admit = dates_used.pop(0) + timedelta(days=random.randint(0, 5))
        else:
            admit = rand_date(start, end)
        stay = random.randint(2, 8)
        dis  = admit + timedelta(days=stay)
        ibd  = random.random() < 0.8

        dx     = {f"DXCODE{i}": None for i in range(1, 26)}
        dxtype = {f"DXTYPE{i}": None for i in range(1, 26)}
        dx["DXCODE1"]     = random.choice(ibd_dx if ibd else NON_IBD_DX)
        dxtype["DXTYPE1"] = "M"
        if random.random() < 0.4:
            dx["DXCODE2"]     = random.choice(NON_IBD_DX)
            dxtype["DXTYPE2"] = "1"

        proc = {f"PROCCODE{i}": None for i in range(1, 21)}
        proc["PROCCODE1"] = random.choice([p for p in PROC_CODES if p])

        docsvc = {f"DOCSVC{i}": None for i in range(1, 9)}
        docsvc["DOCSVC1"] = random.choice(DOCSVC)

        scu    = {f"SCU{i}": None for i in range(1, 7)}
        scuadm = {f"SCUADMDT{i}": None for i in range(1, 7)}
        scudis = {f"SCUDISDT{i}": None for i in range(1, 7)}

        row = dict(
            PATID=patid,
            INST=random.choice(HOSPITALS),
            INSTFROM=None,
            INSTTO=None,
            ADMITCAT=random.choice(ADMIT_CATS),
            ADMITDATE=iso_date(admit),
            ADMITTIME=hhmm(admit),
            DISDATE=iso_date(dis),
            DISTIME=hhmm(dis),
            DISP=random.choice(DAD_DISPS),
            ACUTE_DAYS=stay,
            CMG=random.choice(CMG_IBD if ibd else CMG_OTHER),
            RIW=round(random.uniform(0.5, 5.0), 2),
        )
        row.update(dx)
        row.update(dxtype)
        row.update(proc)
        row.update(docsvc)
        row.update(scu)
        row.update(scuadm)
        row.update(scudis)
        rows.append(row)
    return rows


def gen_lab(patid, start, end, flare_dates):
    rows = []
    for _ in range(random.randint(8, 25)):
        dt    = rand_date(start, end)
        flare = any(abs((dt - fd).days) < 30 for fd in flare_dates)
        for test in random.sample(LAB_TESTS, random.randint(1, 4)):
            result = lab_result(test, flare)
            abnormal = _is_abnormal(test, float(result), flare)
            rows.append(dict(
                PATID=patid,
                SRC=random.choice(["AHS", "DynaLIFE", "Covenant"]),
                ORDR_TEST_CODE_CD=test["cd"],
                ORDR_TEST_CODE_NM=test["nm"],
                TEST_CD=test["cd"],
                TEST_NM=test["nm"],
                TEST_RSLT=result,
                TEST_UOFM=test["uom"],
                TEST_ABNRML_FLAG="Y" if abnormal else "N",
                verifyDt=iso_date(dt),
            ))
    return rows


def gen_pin(patid, start, end, biologic, flare_dates):
    rows = []
    biol_date = start + timedelta(days=random.randint(30, 120))
    dose_num  = 0
    while biol_date < end:
        dose_num += 1
        maintenance = 0 if dose_num <= 3 else 1
        qty    = 1
        supply = 56
        dq     = round(qty / supply, 4)
        dd     = round(biologic["strength"] * dq, 4)
        rows.append(dict(
            PATID=patid,
            DSPN_DATE=iso_date(biol_date),
            DRUG_DIN=biologic["din"],
            SUPP_DRUG_ATC_CODE=biologic["atc"],
            INGREDIENT=biologic["ingredient"],
            STRENGTH=biologic["strength"],
            STRENGTH_UNIT=biologic["unit"],
            DOSAGE_UNIT=biologic["dosage_unit"],
            DOSAGE_VALUE=None,
            DSPN_DAY_SUPPLY_QTY=supply,
            DSPN_AMT_QTY=qty,
            DSPN_AMT_UNT_MSR_CD="EA",
            BRAND_NAME=biologic["brand"],
            DAILY_QTY=dq,
            DAILY_DOSE=dd,
            INGR_REL_DAILY_DOSE=round(random.uniform(0.7, 1.0), 3),
            MAINTENANCE=maintenance,
            STRD_FLARE_DOSE=None,
        ))
        biol_date += timedelta(weeks=8)

    for fd in flare_dates:
        if random.random() < 0.7:
            strd   = random.choice(STEROIDS)
            qty    = 14
            supply = 14
            dq     = round(qty / supply, 4)
            dd     = round(strd["strength"] * dq, 4)
            rows.append(dict(
                PATID=patid,
                DSPN_DATE=iso_date(fd),
                DRUG_DIN=strd["din"],
                SUPP_DRUG_ATC_CODE=strd["atc"],
                INGREDIENT=strd["ingredient"],
                STRENGTH=strd["strength"],
                STRENGTH_UNIT=strd["unit"],
                DOSAGE_UNIT=strd["dosage_unit"],
                DOSAGE_VALUE=None,
                DSPN_DAY_SUPPLY_QTY=supply,
                DSPN_AMT_QTY=qty,
                DSPN_AMT_UNT_MSR_CD="EA",
                BRAND_NAME=strd["brand"],
                DAILY_QTY=dq,
                DAILY_DOSE=dd,
                INGR_REL_DAILY_DOSE=1.0,
                MAINTENANCE=None,
                STRD_FLARE_DOSE=strd["flare_dose"],
            ))

    if random.random() < 0.5:
        drug   = random.choice(OTHER_DRUGS)
        d      = start + timedelta(days=random.randint(0, 180))
        qty    = 90
        supply = 90
        dq     = round(qty / supply, 4)
        dd     = round(drug["strength"] * dq, 4)
        rows.append(dict(
            PATID=patid,
            DSPN_DATE=iso_date(d),
            DRUG_DIN=drug["din"],
            SUPP_DRUG_ATC_CODE=drug["atc"],
            INGREDIENT=drug["ingredient"],
            STRENGTH=drug["strength"],
            STRENGTH_UNIT=drug["unit"],
            DOSAGE_UNIT=drug["dosage_unit"],
            DOSAGE_VALUE=None,
            DSPN_DAY_SUPPLY_QTY=supply,
            DSPN_AMT_QTY=qty,
            DSPN_AMT_UNT_MSR_CD="EA",
            BRAND_NAME=drug["brand"],
            DAILY_QTY=dq,
            DAILY_DOSE=dd,
            INGR_REL_DAILY_DOSE=round(random.uniform(0.5, 1.0), 3),
            MAINTENANCE=None,
            STRD_FLARE_DOSE=None,
        ))
    return rows


def gen_clm(patid, start, end, ibd_dx):
    # TODO: update column names once full real CLM headers are confirmed
    rows = []
    for _ in range(random.randint(5, 15)):
        d   = rand_date(start, end)
        ibd = random.random() < 0.6
        rows.append(dict(
            PATID=patid,
            SE_START_DATE=iso_date(d),
            SE_END_DATE=iso_date(d),
            HLTH_SRVC_CCPX_CODE=random.choice(CLM_SERVICES),
            DXCODE=random.choice(ibd_dx if ibd else NON_IBD_DX),
            SECTOR=random.choice(["CLINICAL SUPPORT", "COMMUNITY HEALTH", "CONTINUING CARE", "HOSPITAL", "OTHER"]),
            DOCTOR_CLASS=random.choice(["ALLIED", "GP", "SPECIALIST"]),
            PERS_CAPB_PRVD_SPEC_AD=random.choice(CLM_SPECIALTIES),
        ))
    return rows


def gen_di(patid, start, end, birth_year, sex):
    rows = []
    for _ in range(random.randint(1, 5)):
        d    = rand_date(start, end)
        proc = random.choice(DI_PROCEDURES)
        rows.append(dict(
            PATID=patid,
            accession_deid=f"ACC{random.randint(100000, 999999)}",
            PT_SVC_AGE_YR=d.year - birth_year,
            GNDR=sex,
            ENCTR_TYPE=random.choice(["IP", "OP", "ER"]),
            SVC_DT=iso_date(d),
            CPEL_CATLG_CD=proc["cd"],
            CPEL_CATLG_DESC=proc["desc"],
            CPEL_MDLTY_CD=proc["modality"],
            CPEL_CATLG_EXAM_CNT=random.randint(1, 3),
        ))
    return rows


def gen_reg(patid, obs_start, obs_end, birth_year, sex):
    return [dict(
        PATID=patid,
        FYE=obs_end.year,
        SEX=sex,
        ACTIVE_COVERAGE=1,
        IN_MIGRATION_IND=random.choice([0, 0, 0, 1]),
        OUT_MIGRATION_IND=random.choice([0, 0, 0, 1]),
        DEATH_IND=0,
        Rural=random.choice([0, 0, 1]),
        PERS_REAP_END_DT=iso_date(obs_end),
        PERS_REAP_END_RSN_CODE_GRP=random.choice(["STILL_ACTIVE", "STILL_ACTIVE", "STILL_ACTIVE", "OUT_MIGRATION"]),
        BIRTH_YEAR=birth_year,
        ZONE_NAME=random.choice(ZONES),
        QUINTMAT=random.randint(1, 5),
        QUINTSOC=random.randint(1, 5),
    )]


# ---------------------------------------------------------------------------
# Main generator
# ---------------------------------------------------------------------------

AMB_COLS = (
    ["PATID", "TRIAGECODE", "INST", "INSTFROM", "INSTTO", "ADMITBYAMB",
     "ArriveDt", "DispDt", "DepartDt"] +
    [f"DXCODE{i}" for i in range(1, 11)] +
    ["DISPOSITION", "DISP_NM", "ABSTRACT_TYPE", "MIS_CODE"] +
    [f"PROVIDER_SVC{i}" for i in range(1, 9)] +
    ["VISIT_TIME", "TriageDt", "TRIAGE_TIME", "CACS_CODE", "CACS_RIW"] +
    [f"PROCCODE{i}" for i in range(1, 11)] +
    [f"DOCSVC{i}" for i in range(1, 6)]
)

DAD_COLS = (
    ["PATID", "INST", "INSTFROM", "INSTTO"] +
    [f"DXCODE{i}" for i in range(1, 26)] +
    [f"DXTYPE{i}" for i in range(1, 26)] +
    ["ADMITCAT", "ADMITDATE", "ADMITTIME", "DISDATE", "DISTIME", "DISP",
     "ACUTE_DAYS", "CMG", "RIW"] +
    [f"DOCSVC{i}" for i in range(1, 9)] +
    [f"SCU{i}" for i in range(1, 7)] +
    [f"PROCCODE{i}" for i in range(1, 21)] +
    [f"SCUADMDT{i}" for i in range(1, 7)] +
    [f"SCUDISDT{i}" for i in range(1, 7)]
)

LAB_COLS = ["PATID", "SRC", "ORDR_TEST_CODE_CD", "ORDR_TEST_CODE_NM",
            "TEST_CD", "TEST_NM", "TEST_RSLT", "TEST_UOFM", "TEST_ABNRML_FLAG", "verifyDt"]

PIN_COLS = [
    "PATID", "DSPN_DATE", "DRUG_DIN", "SUPP_DRUG_ATC_CODE", "INGREDIENT",
    "STRENGTH", "STRENGTH_UNIT", "DOSAGE_UNIT", "DOSAGE_VALUE",
    "DSPN_DAY_SUPPLY_QTY", "DSPN_AMT_QTY", "DSPN_AMT_UNT_MSR_CD", "BRAND_NAME",
    "DAILY_QTY", "DAILY_DOSE", "INGR_REL_DAILY_DOSE", "MAINTENANCE", "STRD_FLARE_DOSE",
]

CLM_COLS = [
    "PATID", "SE_START_DATE", "SE_END_DATE", "HLTH_SRVC_CCPX_CODE", "DXCODE",
    "SECTOR", "DOCTOR_CLASS", "PERS_CAPB_PRVD_SPEC_AD",
]

DI_COLS = [
    "PATID", "accession_deid", "PT_SVC_AGE_YR", "GNDR", "ENCTR_TYPE",
    "SVC_DT", "CPEL_CATLG_CD", "CPEL_CATLG_DESC", "CPEL_MDLTY_CD", "CPEL_CATLG_EXAM_CNT",
]

REG_COLS = [
    "PATID", "FYE", "SEX", "ACTIVE_COVERAGE", "IN_MIGRATION_IND", "OUT_MIGRATION_IND",
    "DEATH_IND", "Rural", "PERS_REAP_END_DT", "PERS_REAP_END_RSN_CODE_GRP",
    "BIRTH_YEAR", "ZONE_NAME", "QUINTMAT", "QUINTSOC",
]


def generate(n_patients: int, out_dir: str, seed: int):
    random.seed(seed)
    np.random.seed(seed)
    os.makedirs(out_dir, exist_ok=True)

    all_amb, all_dad, all_lab = [], [], []
    all_pin, all_clm, all_di, all_reg = [], [], [], []

    cohort_start = datetime(2018, 1, 1)
    cohort_end   = datetime(2024, 1, 1)

    for i in range(1, n_patients + 1):
        patid      = f"P{i:03d}"
        obs_start  = rand_date(cohort_start, datetime(2020, 6, 1))
        obs_end    = min(obs_start + timedelta(days=random.randint(365, 1825)), cohort_end)
        ibd_dx     = random.sample(IBD_DX, random.randint(1, 3))
        biologic   = random.choice(BIOLOGICS)
        birth_year = random.randint(1950, 2000)
        sex        = random.choice(["M", "F"])
        n_flares   = random.randint(0, 3)
        flare_dates = sorted([rand_date(obs_start, obs_end) for _ in range(n_flares)])

        all_amb.extend(gen_amb(patid, obs_start, obs_end, ibd_dx))
        all_dad.extend(gen_dad(patid, obs_start, obs_end, ibd_dx, flare_dates))
        all_lab.extend(gen_lab(patid, obs_start, obs_end, flare_dates))
        all_pin.extend(gen_pin(patid, obs_start, obs_end, biologic, flare_dates))
        all_clm.extend(gen_clm(patid, obs_start, obs_end, ibd_dx))
        all_di.extend(gen_di(patid, obs_start, obs_end, birth_year, sex))
        all_reg.extend(gen_reg(patid, obs_start, obs_end, birth_year, sex))

    datasets = {
        "AMB": (all_amb, AMB_COLS),
        "DAD": (all_dad, DAD_COLS),
        "LAB": (all_lab, LAB_COLS),
        "PIN": (all_pin, PIN_COLS),
        "CLM": (all_clm, CLM_COLS),
        "DI":  (all_di,  DI_COLS),
        "REG": (all_reg, REG_COLS),
    }

    total_rows = 0
    for source, (rows, cols) in datasets.items():
        df   = pd.DataFrame(rows, columns=cols)
        path = os.path.join(out_dir, f"RMT23345_{source}.csv")
        df.to_csv(path, index=False)
        total_rows += len(df)
        print(f"  {source}: {len(df):>5} rows → {path}")

    print(f"\nDone. {n_patients} patients, {total_rows} total rows across 7 files.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--n",    type=int, default=75,           help="Number of patients")
    parser.add_argument("--out",  type=str, default="dummy_data",  help="Output directory")
    parser.add_argument("--seed", type=int, default=42,            help="Random seed")
    args = parser.parse_args()

    print(f"Generating {args.n} patients into '{args.out}/'...")
    generate(args.n, args.out, args.seed)
