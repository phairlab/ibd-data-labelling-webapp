"""
Run with:  python test_rmt23345_events.py
Tests rmt23345_events.py using synthetic data that matches the column
structure produced by the IBDdataprep R scripts.
"""
import os
import sys
import tempfile
import pandas as pd

sys.path.insert(0, os.path.dirname(__file__))
from rmt23345_events import (
    load_amb_events, load_dad_events, load_lab_events, load_pin_events,
    load_clm_events, load_di_events, load_all_events,
)

# ---------------------------------------------------------------------------
# Dummy data — mirrors cleaned RMT23345 column structure after R scripts run
# ---------------------------------------------------------------------------

def make_amb():
    return pd.DataFrame({
        "PATID":       ["P001", "P001", "P001", "P002", "P002"],
        "ArriveDt":    ["2021-01-15T09:00:00+00:00", "2021-03-10T14:00:00+00:00",
                        "2021-06-20T11:00:00+00:00", "2021-02-01T10:00:00+00:00",
                        "2021-07-15T08:00:00+00:00"],
        "DepartDt":    ["2021-01-15T10:30:00+00:00", "2021-03-10T15:00:00+00:00",
                        "2021-06-20T12:00:00+00:00", "2021-02-01T11:00:00+00:00",
                        "2021-07-15T09:00:00+00:00"],
        "DispDt":      [None] * 5,
        "INST":        ["Royal Alex Hospital", "University of Alberta Hospital",
                        "Royal Alex Hospital", "Grey Nuns Hospital", "Misericordia Hospital"],
        "DXCODE":      ["Crohn's disease of small intestine",
                        "Ulcerative (chronic) enterocolitis",
                        "Acute upper respiratory infection, unspecified",
                        "Crohn's disease of large intestine",
                        "General medical examination"],
        "PROCCODE":    ["Colonoscopy", None, "Blood test", "Colonoscopy", None],
        "MIS_CODE":    [None] * 5,
        "CACS_CODE":   [None] * 5,
        "DOCSVC_LIST": ["Gastroenterology"] * 5,
    })


def make_dad():
    return pd.DataFrame({
        "PATID":     ["P001", "P001", "P002"],
        "ADMITDATE": ["2021-02-01T00:00:00+00:00", "2021-08-15T00:00:00+00:00",
                      "2021-05-10T00:00:00+00:00"],
        "DISDATE":   ["2021-02-05T00:00:00+00:00", "2021-08-20T00:00:00+00:00",
                      "2021-05-14T00:00:00+00:00"],
        "INST":      ["Royal Alex Hospital", "Royal Alex Hospital", "Grey Nuns Hospital"],
        "DXCODE":    ["Crohn's disease of small intestine|Intestinal obstruction",
                      "Ulcerative (chronic) pancolitis",
                      "Felty's syndrome"],
        "CMG":       ["IBD - Small Bowel", "IBD - Large Bowel", "Rheumatology"],
        "PROCCODE":  ["Colonoscopy|IV fluids", "Colonoscopy", "Joint injection"],
        "DOCSVC_LIST": ["Gastroenterology", "Gastroenterology", "Rheumatology"],
    })


def make_pin():
    return pd.DataFrame({
        "PATID":               ["P001", "P001", "P001", "P001", "P002", "P002"],
        "DSPN_DATE":           ["2021-01-20", "2021-03-15", "2021-05-01", "2021-09-01",
                                "2021-02-10", "2021-06-01"],
        "DRUG_DIN":            [2243197, 2243197, 2243197, 2243197, 2356789, 2356789],
        "SUPP_DRUG_ATC_CODE":  ["L04AB02", "L04AB02", "L04AB02", "L04AB02",
                                "H02AB06", "H02AB06"],
        "INGREDIENT":          ["infliximab", "infliximab", "infliximab", "infliximab",
                                "prednisone", "prednisone"],
        "STRENGTH":            [100.0, 100.0, 100.0, 100.0, 50.0, 50.0],
        "STRENGTH_UNIT":       ["mg"] * 6,
        "DOSAGE_UNIT":         ["vial"] * 4 + ["tab"] * 2,
        "DOSAGE_VALUE":        [None] * 6,
        "DSPN_DAY_SUPPLY_QTY": [56, 56, 56, 56, 14, 14],
        "DSPN_AMT_QTY":        [1, 1, 1, 1, 14, 14],
        "DSPN_AMT_UNT_MSR_CD": ["EA"] * 6,
        "BRAND_NAME":          ["REMICADE"] * 4 + ["APO-PREDNISONE"] * 2,
        "DAILY_QTY":           [0.018] * 4 + [1.0, 1.0],
        "DAILY_DOSE":          [1.8] * 4 + [50.0, 50.0],
        "INGR_REL_DAILY_DOSE": [0.9] * 4 + [1.0, 1.0],
        "MAINTENANCE":         [0, 0, 0, 1, None, None],
        "STRD_FLARE_DOSE":     [None, None, None, None, 1, 0],
    })


def make_clm():
    return pd.DataFrame({
        "PATID":               ["P001", "P001", "P002", "P002"],
        "SE_START_DATE":       ["2021-01-10", "2021-04-05", "2021-03-01", "2021-07-20"],
        "SE_END_DATE":         ["2021-01-10", "2021-04-05", "2021-03-01", "2021-07-20"],
        "HLTH_SRVC_CCPX_CODE": ["Colonoscopy", "Office visit - gastroenterology",
                                "Office visit - general practice", "Sigmoidoscopy"],
        "DXCODE":              ["Crohn's disease of small intestine",
                                "Ulcerative (chronic) pancolitis",
                                "General medical examination",
                                "Ulcerative (chronic) pancolitis"],
    })


def make_lab():
    return pd.DataFrame({
        "PATID":     ["P001", "P001", "P001", "P002", "P002"],
        "verifyDt":  ["2021-01-16T08:00:00+00:00", "2021-03-11T07:30:00+00:00",
                      "2021-08-16T08:00:00+00:00", "2021-02-02T07:00:00+00:00",
                      "2021-05-11T08:00:00+00:00"],
        "TEST_CD":   ["HGB", "CRP", "WBC", "HGB", "CRP"],
        "TEST_NM":   ["HEMOGLOBIN", "C REACTIVE PROTEIN", "WHITE BLOOD COUNT",
                      "HEMOGLOBIN", "C REACTIVE PROTEIN"],
        "TEST_RSLT": ["102", "45.2", "11.3", "118", "8.1"],
        "TEST_UOFM": ["g/L", "mg/L", "x10e9/L", "g/L", "mg/L"],
    })


def make_di():
    return pd.DataFrame({
        "PATID":           ["P001", "P001", "P002"],
        "SVC_DT":          ["2021-02-10T09:00:00+00:00", "2021-09-10T14:00:00+00:00",
                            "2021-06-05T11:00:00+00:00"],
        "CPEL_CATLG_CD":   ["XR001", "CT002", "US003"],
        "CPEL_CATLG_DESC": ["X-Ray Abdomen", "CT Abdomen with contrast",
                            "Abdominal Ultrasound"],
    })


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

EXPECTED_COLS = {
    "patient_id", "start_date", "end_date",
    "event_type", "ibd_related", "event_info", "source_dataset",
}


def check_columns(df, name):
    assert set(df.columns) == EXPECTED_COLS, f"{name}: unexpected columns {df.columns.tolist()}"


def test_loader(name, maker, loader):
    print(f"\n--- {name} ---")
    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
        maker().to_csv(f, index=False)
        tmp = f.name
    try:
        result = loader(tmp)
        check_columns(result, name)
        print(result[["patient_id", "start_date", "event_type", "ibd_related", "event_info"]].to_string())
        print(f"  PASS ({len(result)} rows)")
    finally:
        os.unlink(tmp)


def test_ibd_flags():
    print("\n--- IBD flag detection ---")
    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
        make_amb().to_csv(f, index=False)
        tmp = f.name
    try:
        result = load_amb_events(tmp)
        ibd_rows = result[result["ibd_related"] == True]
        non_ibd  = result[result["ibd_related"] == False]
        assert len(ibd_rows) == 3, f"Expected 3 IBD rows, got {len(ibd_rows)}"
        assert len(non_ibd) == 2,  f"Expected 2 non-IBD rows, got {len(non_ibd)}"
        print(f"  IBD rows: {len(ibd_rows)}, Non-IBD rows: {len(non_ibd)}  PASS")
    finally:
        os.unlink(tmp)


def test_pin_event_types():
    print("\n--- PIN event type classification ---")
    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
        make_pin().to_csv(f, index=False)
        tmp = f.name
    try:
        result = load_pin_events(tmp)
        types = result["event_type"].value_counts().to_dict()
        print(f"  Event types: {types}")
        assert "Biologic (Induction)" in types
        assert "Biologic (Maintenance)" in types
        assert "Corticosteroid (Flare)" in types
        assert result["ibd_related"].sum() == 5, "Expected 5 IBD-related PIN rows"
        print("  PASS")
    finally:
        os.unlink(tmp)


def test_patient_filter():
    print("\n--- load_all_events patient filter ---")
    with tempfile.TemporaryDirectory() as tmpdir:
        make_amb().to_csv(f"{tmpdir}/RMT23345_AMB.csv", index=False)
        make_dad().to_csv(f"{tmpdir}/RMT23345_DAD.csv", index=False)
        make_lab().to_csv(f"{tmpdir}/RMT23345_LAB.csv", index=False)
        make_pin().to_csv(f"{tmpdir}/RMT23345_PIN.csv", index=False)
        make_clm().to_csv(f"{tmpdir}/RMT23345_CLM.csv", index=False)
        make_di().to_csv(f"{tmpdir}/RMT23345_DI.csv",  index=False)

        all_events = load_all_events(tmpdir)
        p1_events  = load_all_events(tmpdir, patient_id="P001")
        p2_events  = load_all_events(tmpdir, patient_id="P002")

        print(f"  All patients: {len(all_events)} events")
        print(f"  P001: {len(p1_events)} events")
        print(f"  P002: {len(p2_events)} events")
        print(f"  Sources present: {sorted(all_events['source_dataset'].unique())}")

        assert all(p1_events["patient_id"] == "P001")
        assert all(p2_events["patient_id"] == "P002")
        assert len(all_events) == len(p1_events) + len(p2_events)
        assert list(all_events["start_date"]) == sorted(all_events["start_date"].tolist())
        print("  PASS")


if __name__ == "__main__":
    test_loader("AMB", make_amb, load_amb_events)
    test_loader("DAD", make_dad, load_dad_events)
    test_loader("LAB", make_lab, load_lab_events)
    test_loader("PIN", make_pin, load_pin_events)
    test_loader("CLM", make_clm, load_clm_events)
    test_loader("DI",  make_di,  load_di_events)
    test_ibd_flags()
    test_pin_event_types()
    test_patient_filter()
    print("\nAll tests passed.")
