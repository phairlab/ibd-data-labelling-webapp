import pandas as pd
from pathlib import Path
from typing import Optional

PATIENT_ID_COL = "PATID"

# ── Fallback defaults (used when study_config.yaml has no disease_detection section) ──
# These are IBD-specific. Override via study_config.yaml for other diseases.
_DEFAULT_KEYWORDS       = r"crohn|ulcerative|inflammatory bowel|ileitis|proctocolitis"
_DEFAULT_BIOLOGICS      = frozenset({
    "L04AB04",  # adalimumab
    "L04AB02",  # infliximab
    "L04AB06",  # golimumab
    "L04AB05",  # certolizumab pegol
    "L04AA33",  # vedolizumab
    "L04AC05",  # ustekinumab
    "L04AC18",  # risankizumab
    "L04AC24",  # mirikizumab
    "L04AF01",  # tofacitinib
    "L04AF03",  # upadacitinib
})
_DEFAULT_STEROIDS       = frozenset({"H02AB04", "H02AB06", "H02AB07"})


def _check_config_columns(df: pd.DataFrame, fields: list, source: str) -> None:
    """Print a warning for any display columns in study_config.yaml missing from the CSV."""
    if not fields:
        return
    missing = [
        (f["column"] if isinstance(f, dict) else f)
        for f in fields
        if (f["column"] if isinstance(f, dict) else f) not in df.columns
    ]
    if missing:
        print(f"[study_config] {source}: missing columns (will be blank in tooltip): {missing}")
    else:
        print(f"[study_config] {source}: all {len(fields)} display columns found OK")


def _build_event_info(df: pd.DataFrame, fields: list) -> pd.Series:
    """Build 'Label: value | Label: value' event_info from a list of {column, label} dicts."""
    parts = []
    for f in fields:
        col   = f["column"] if isinstance(f, dict) else f
        label = f.get("label", col) if isinstance(f, dict) else col
        vals  = _safe_col(df, col).fillna("").astype(str)
        parts.append(vals.apply(lambda v: f"{label}: {v}" if v and v not in ("", "nan") else ""))
    if not parts:
        return pd.Series("", index=df.index, dtype=str)
    result = parts[0]
    for p in parts[1:]:
        result = result + p.apply(lambda v: f" | {v}" if v else "")
    return result.str.strip(" |")


def _has_ibd_dx(dxcode_series: pd.Series, keywords: str = None) -> pd.Series:
    kw = keywords if keywords else _DEFAULT_KEYWORDS
    return dxcode_series.fillna("").str.lower().str.contains(kw, regex=True, na=False)


def _has_disease_icd(dxcode_series: pd.Series, prefixes: list) -> pd.Series:
    """Flag rows where any pipe-separated ICD code starts with one of the given prefixes.

    Works for any disease — prefixes come from study_config.yaml, e.g. ["K50","K51"]
    for IBD, ["E10","E11"] for diabetes, etc.
    """
    if not prefixes:
        return pd.Series(False, index=dxcode_series.index)
    upper = tuple(p.upper() for p in prefixes)
    def _row_match(val: str) -> bool:
        return any(
            code.strip().upper().startswith(upper)
            for code in str(val).replace("|", ",").split(",")
        )
    return dxcode_series.fillna("").apply(_row_match)


def _load_icd_dict(path: str) -> dict:
    """Load an ICD dictionary CSV (col1=code/prefix, col2=description) into a lookup dict.

    Mirrors the R map_codes function: longest-prefix-first so the most specific
    match always wins (e.g. K500 beats K50 for code K500).
    """
    try:
        df = pd.read_csv(path, usecols=[0, 1], header=0, dtype=str)
        df.columns = ["prefix", "desc"]
        df = df.dropna(subset=["prefix", "desc"])
        df["prefix"] = df["prefix"].str.strip().str.replace(".", "", regex=False).str.upper()
        # Sort longest-first so most specific match is tried first during lookup
        df = df.sort_values("prefix", key=lambda s: s.str.len(), ascending=False)
        return dict(zip(df["prefix"], df["desc"]))
    except Exception as e:
        print(f"[study_config] Warning: could not load ICD dictionary {path}: {e}")
        return {}


def _normalize_icd(code: str) -> str:
    """Strip dots and whitespace: 'K50.0' → 'K500', '555.0' → '5550'."""
    return code.strip().replace(".", "").upper()


def _lookup_icd_desc(code: str, icd9_dict: dict, icd10_dict: dict) -> str:
    """Return 'CODE - Description', or just CODE if not found in either dictionary.

    Tries both ICD-10 and ICD-9 dictionaries — does NOT guess the version from the
    code format, because ICD-9 V-codes and E-codes also start with letters.
    Uses longest-prefix matching so K500 beats K50 for a more specific description.
    """
    norm = _normalize_icd(code)
    if not norm:
        return code
    for lookup in (icd10_dict, icd9_dict):
        for length in range(len(norm), 0, -1):
            desc = lookup.get(norm[:length])
            if desc:
                return f"{norm} - {desc}"
    return norm


def enrich_icd_codes(series: pd.Series, icd9_dict: dict, icd10_dict: dict) -> pd.Series:
    """Replace raw ICD codes with 'CODE - Description' format.

    Handles pipe-separated multi-code values (e.g. 'K500|K510').
    If no dictionaries are loaded, returns the series unchanged.
    """
    if not icd9_dict and not icd10_dict:
        return series

    def _enrich_val(val: str) -> str:
        codes = [c.strip() for c in str(val).replace("|", ",").split(",") if c.strip()]
        return " | ".join(_lookup_icd_desc(c, icd9_dict, icd10_dict) for c in codes)

    return series.fillna("").apply(_enrich_val)


def _safe_col(df: pd.DataFrame, col: str) -> pd.Series:
    return df[col] if col in df.columns else pd.Series("", index=df.index, dtype=str)


def _coalesce(a: pd.Series, b: pd.Series) -> pd.Series:
    return a.where(a.notna(), b)


def _parse_col(series: pd.Series) -> pd.Series:
    """Parse a date series, handling SAS formats automatically.

    Detects two SAS formats:
      22APR2018            → %d%b%Y
      07NOV2017:00:00:00   → %d%b%Y:%H:%M:%S
    Falls back to standard pd.to_datetime for all other formats.
    """
    if series.empty:
        return pd.to_datetime(series, utc=True, errors="coerce")
    sample = series.dropna().astype(str)
    if not sample.empty:
        s = sample.iloc[0]
        if len(s) >= 7 and s[2:5].isalpha():
            if ":" in s:
                fmt = "%d%b%Y:%H:%M:%S"
            else:
                fmt = "%d%b%Y"
            return pd.to_datetime(series, format=fmt, errors="coerce").dt.tz_localize("UTC")
    return pd.to_datetime(series, utc=True, errors="coerce")


def _resolve_dates(df: pd.DataFrame, start_col: str, end_cols) -> tuple:
    """Parse start/end datetimes from df, both assumed UTC.

    end_cols can be:
      - str  : single column; end stays NaT if the column is missing/null
      - list : try each column in order; if all missing → start + 23:59
    """
    start_dt = _parse_col(
        df[start_col] if start_col in df.columns else pd.Series(pd.NaT, index=df.index),
    )

    if isinstance(end_cols, list):
        end_dt = None
        for col in end_cols:
            if col in df.columns:
                candidate = _parse_col(df[col])
                end_dt = candidate if end_dt is None else _coalesce(end_dt, candidate)
        if end_dt is None:
            end_dt = start_dt.copy()
            end_dt[:] = pd.NaT
        missing = end_dt.isna()
        if missing.any():
            end_dt = end_dt.copy()
            end_dt[missing] = start_dt[missing] + pd.Timedelta(hours=23, minutes=59)
    else:
        col = end_cols if end_cols and end_cols in df.columns else start_col
        end_dt = _parse_col(df[col])

    return start_dt, end_dt


def load_amb_events(path: str, fields: list = None, start_col: str = None, end_cols=None,
                    dx_format: str = "text", icd_prefixes: list = None,
                    keywords: str = None, icd9_dict: dict = None, icd10_dict: dict = None,
                    biologic_atc_codes=None, steroid_atc_codes=None) -> pd.DataFrame:
    df = pd.read_csv(path, low_memory=False)
    _check_config_columns(df, fields, "AMB")
    dxcode = _safe_col(df, "DXCODE1").fillna("")
    if dx_format == "icd_code" and (icd9_dict or icd10_dict):
        df = df.copy()
        df["DXCODE1"] = enrich_icd_codes(dxcode, icd9_dict or {}, icd10_dict or {})
    if fields is not None:
        info = _build_event_info(df, fields)
    else:
        inst  = _safe_col(df, "INST").fillna("")
        proc  = _safe_col(df, "PROCCODE").fillna("")
        info  = inst.apply(lambda x: f"At: {x}" if x else "")
        info += dxcode.apply(lambda x: f" | Dx: {x}" if x else "")
        info += proc.apply(lambda x: f" | Proc: {x}" if x else "")

    if start_col or end_cols:
        start_dt, end_dt = _resolve_dates(df, start_col or "ArriveDt", end_cols or ["DepartDt", "DispDt"])
    else:
        end_raw  = _coalesce(_safe_col(df, "DepartDt"), _safe_col(df, "DispDt"))
        start_dt = pd.to_datetime(df["ArriveDt"], utc=True, errors="coerce")
        end_dt   = pd.to_datetime(end_raw, utc=True, errors="coerce")
        missing_end = end_dt.isna()
        end_dt[missing_end] = start_dt[missing_end] + pd.Timedelta(hours=23, minutes=59)

    return pd.DataFrame({
        "patient_id":     df[PATIENT_ID_COL],
        "start_date":     start_dt,
        "end_date":       end_dt,
        "event_type":     "ambulatory_visit",
        "ibd_related":    (_has_disease_icd(dxcode, icd_prefixes) if dx_format == "icd_code"
                          else _has_ibd_dx(dxcode, keywords)),
        "event_info":     info.str.strip(" |"),
        "source_dataset": "AMB",
    })


def load_dad_events(path: str, fields: list = None, start_col: str = None, end_cols=None,
                    dx_format: str = "text", icd_prefixes: list = None,
                    keywords: str = None, icd9_dict: dict = None, icd10_dict: dict = None,
                    biologic_atc_codes=None, steroid_atc_codes=None) -> pd.DataFrame:
    df = pd.read_csv(path, low_memory=False)
    _check_config_columns(df, fields, "DAD")
    dxcode = _safe_col(df, "DXCODE1").fillna("")
    if dx_format == "icd_code" and (icd9_dict or icd10_dict):
        df = df.copy()
        df["DXCODE1"] = enrich_icd_codes(dxcode, icd9_dict or {}, icd10_dict or {})
    if fields is not None:
        info = _build_event_info(df, fields)
    else:
        inst = _safe_col(df, "INST").fillna("")
        cmg  = _safe_col(df, "CMG").fillna("")
        info  = inst.apply(lambda x: f"At: {x}" if x else "")
        info += dxcode.apply(lambda x: f" | Dx: {x}" if x else "")
        info += cmg.apply(lambda x: f" | CMG: {x}" if x else "")

    start_dt, end_dt = _resolve_dates(df, start_col or "ADMITDATE", end_cols or "DISDATE")
    return pd.DataFrame({
        "patient_id":     df[PATIENT_ID_COL],
        "start_date":     start_dt,
        "end_date":       end_dt,
        "event_type":     "hospital_admission",
        "ibd_related":    (_has_disease_icd(dxcode, icd_prefixes) if dx_format == "icd_code"
                          else _has_ibd_dx(dxcode, keywords)),
        "event_info":     info.str.strip(" |"),
        "source_dataset": "DAD",
    })


def load_lab_events(path: str, fields: list = None, start_col: str = None, end_cols=None,
                    dx_format: str = "text", icd_prefixes: list = None,
                    keywords: str = None, icd9_dict: dict = None, icd10_dict: dict = None,
                    biologic_atc_codes=None, steroid_atc_codes=None) -> pd.DataFrame:
    df = pd.read_csv(path, low_memory=False)
    _check_config_columns(df, fields, "LAB")
    if fields is not None:
        info = _build_event_info(df, fields)
    else:
        name   = df["TEST_NM"].fillna("Unknown Test").astype(str)
        result = df["TEST_RSLT"].fillna("").astype(str)
        unit   = df["TEST_UOFM"].fillna("").astype(str)
        info   = name + ": " + result + unit.apply(lambda u: f" {u}" if u else "")

    start_dt, end_dt = _resolve_dates(df, start_col or "verifyDt", end_cols or "verifyDt")
    return pd.DataFrame({
        "patient_id":     df[PATIENT_ID_COL],
        "start_date":     start_dt,
        "end_date":       end_dt,
        "event_type":     "lab_test",
        "ibd_related":    False,
        "event_info":     info.str.strip(),
        "source_dataset": "LAB",
    })


def load_pin_events(path: str, fields: list = None, start_col: str = None, end_cols=None,
                    dx_format: str = "text", icd_prefixes: list = None,
                    keywords: str = None, icd9_dict: dict = None, icd10_dict: dict = None,
                    biologic_atc_codes: frozenset = None, steroid_atc_codes: frozenset = None) -> pd.DataFrame:
    df = pd.read_csv(path, low_memory=False)
    _check_config_columns(df, fields, "PIN")
    atc         = _safe_col(df, "SUPP_DRUG_ATC_CODE").fillna("")
    maintenance = pd.to_numeric(_safe_col(df, "MAINTENANCE"), errors="coerce").fillna(-1)
    strd_flare  = pd.to_numeric(_safe_col(df, "STRD_FLARE_DOSE"), errors="coerce").fillna(0)

    biologics     = biologic_atc_codes if biologic_atc_codes is not None else _DEFAULT_BIOLOGICS
    steroids      = steroid_atc_codes  if steroid_atc_codes  is not None else _DEFAULT_STEROIDS
    is_biologic   = atc.isin(biologics)
    is_strd_flare = atc.isin(steroids) & strd_flare.eq(1)

    specific_type = pd.Series("Prescription", index=df.index)
    specific_type[is_biologic & maintenance.eq(0)] = "Biologic (Induction)"
    specific_type[is_biologic & maintenance.eq(1)] = "Biologic (Maintenance)"
    specific_type[is_strd_flare] = "Corticosteroid (Flare)"

    if fields is not None:
        info = specific_type + ": " + _build_event_info(df, fields)
    else:
        ingredient = _safe_col(df, "INGREDIENT").fillna("")
        strength   = _safe_col(df, "STRENGTH").fillna("").astype(str)
        unit       = _safe_col(df, "STRENGTH_UNIT").fillna("")
        brand      = _safe_col(df, "BRAND_NAME").fillna("")
        info = specific_type + ": " + ingredient + " " + strength + unit + " (" + brand + ")"

    start_dt, end_dt = _resolve_dates(df, start_col or "DSPN_DATE", end_cols or "DSPN_DATE")
    return pd.DataFrame({
        "patient_id":     df[PATIENT_ID_COL],
        "start_date":     start_dt,
        "end_date":       end_dt,
        "event_type":     "prescription",
        "ibd_related":    is_biologic | is_strd_flare,
        "event_info":     info.str.strip(),
        "source_dataset": "PIN",
    })


def load_clm_events(path: str, fields: list = None, start_col: str = None, end_cols=None,
                    dx_format: str = "text", icd_prefixes: list = None,
                    keywords: str = None, icd9_dict: dict = None, icd10_dict: dict = None,
                    biologic_atc_codes=None, steroid_atc_codes=None) -> pd.DataFrame:
    df = pd.read_csv(path, low_memory=False)
    _check_config_columns(df, fields, "CLM")
    dxcode = _safe_col(df, "HLTH_DX_ICD9X_CODE_1").fillna("")
    if dx_format == "icd_code" and (icd9_dict or icd10_dict):
        df = df.copy()
        df["HLTH_DX_ICD9X_CODE_1"] = enrich_icd_codes(dxcode, icd9_dict or {}, icd10_dict or {})
    if fields is not None:
        info = _build_event_info(df, fields)
    else:
        svc  = _safe_col(df, "HLTH_SRVC_CCPX_CODE").fillna("")
        info = svc + dxcode.apply(lambda x: f" | Dx: {x}" if x else "")

    start_dt, end_dt = _resolve_dates(df, start_col or "SE_START_DATE", end_cols or "SE_END_DATE")
    return pd.DataFrame({
        "patient_id":     df[PATIENT_ID_COL],
        "start_date":     start_dt,
        "end_date":       end_dt,
        "event_type":     "physician_claim",
        "ibd_related":    (_has_disease_icd(dxcode, icd_prefixes) if dx_format == "icd_code"
                          else _has_ibd_dx(dxcode, keywords)),
        "event_info":     info.str.strip(" |"),
        "source_dataset": "CLM",
    })


def load_di_events(path: str, fields: list = None, start_col: str = None, end_cols=None,
                   dx_format: str = "text", icd_prefixes: list = None,
                   keywords: str = None, icd9_dict: dict = None, icd10_dict: dict = None,
                   biologic_atc_codes=None, steroid_atc_codes=None) -> pd.DataFrame:
    df = pd.read_csv(path, low_memory=False)
    df.columns = df.columns.str.upper()
    _check_config_columns(df, fields, "DI")
    if fields is not None:
        info = _build_event_info(df, fields)
    else:
        info = _coalesce(
            _safe_col(df, "CPEL_CATLG_DESC"),
            _safe_col(df, "CPEL_CATLG_CD"),
        ).fillna("Imaging")

    start_dt, end_dt = _resolve_dates(df, start_col or "SVC_DT", end_cols or "SVC_DT")
    return pd.DataFrame({
        "patient_id":     df[PATIENT_ID_COL],
        "start_date":     start_dt,
        "end_date":       end_dt,
        "event_type":     "imaging",
        "ibd_related":    False,
        "event_info":     info,
        "source_dataset": "DI",
    })


_LOADERS = {
    "AMB": load_amb_events,
    "DAD": load_dad_events,
    "LAB": load_lab_events,
    "PIN": load_pin_events,
    "CLM": load_clm_events,
    "DI":  load_di_events,
}

_EMPTY = pd.DataFrame(columns=[
    "patient_id", "start_date", "end_date",
    "event_type", "ibd_related", "event_info", "source_dataset",
])


def load_all_events(
    data_dir: Optional[str] = None,
    patient_id: Optional[str] = None,
    sources: Optional[list] = None,
    config: Optional[dict] = None,
) -> pd.DataFrame:
    """Load available cleaned RMT23345 CSVs and return combined events.

    Args:
        data_dir:   Directory containing RMT23345_*.csv files. Used only when a
                    source's `file:` key is a relative filename. Pass None when all
                    paths in the config are absolute.
        patient_id: If given, return only events for this patient.
        sources:    Subset of ["AMB","DAD","LAB","PIN","CLM","DI"]. Overrides config.
        config:     Dict loaded from study_config.yaml. Controls which sources load
                    and which fields appear in hover tooltips.
    """
    cfg_sources      = {}
    cfg_display      = {}
    icd_prefixes     = None
    keywords         = None
    icd9_dict        = {}
    icd10_dict       = {}
    biologic_atc     = None
    steroid_atc      = None

    if config:
        raw = config.get("sources", {})
        if isinstance(raw, dict) and "enabled" not in raw:
            cfg_sources = raw
        else:
            enabled = raw.get("enabled") if isinstance(raw, dict) else None
            cfg_sources = {s: {} for s in (enabled or list(_LOADERS.keys()))}
        cfg_display = config.get("display", {})

        dd = config.get("disease_detection") or {}
        icd_prefixes = dd.get("icd_prefixes") or None
        keywords     = dd.get("keywords")     or None

        # Load ICD dictionaries if paths are provided
        if dd.get("icd9_dictionary"):
            icd9_dict = _load_icd_dict(dd["icd9_dictionary"])
        if dd.get("icd10_dictionary"):
            icd10_dict = _load_icd_dict(dd["icd10_dictionary"])

        # ATC code lists (from YAML, else None → loaders use hardcoded defaults)
        if dd.get("biologic_atc_codes"):
            biologic_atc = frozenset(str(c).upper() for c in dd["biologic_atc_codes"])
        if dd.get("steroid_atc_codes"):
            steroid_atc  = frozenset(str(c).upper() for c in dd["steroid_atc_codes"])

    to_load = sources or list(cfg_sources.keys()) or list(_LOADERS.keys())
    parts = []

    for source in to_load:
        src_cfg   = cfg_sources.get(source, {})
        filename = src_cfg.get("file", f"RMT23345_{source}.csv")
        p = Path(filename)
        if p.is_absolute():
            path = p
        elif data_dir:
            path = Path(data_dir) / filename
        else:
            print(f"[rmt23345_events] {source}: relative path but no data_dir — skipping")
            continue
        if not path.exists():
            continue
        fields    = cfg_display.get(source)
        start_col = src_cfg.get("start_date") or None
        end_cols  = src_cfg.get("end_date")   or None
        dx_format = src_cfg.get("diagnosis_format", "text")
        try:
            parts.append(_LOADERS[source](
                str(path), fields=fields,
                start_col=start_col, end_cols=end_cols,
                dx_format=dx_format, icd_prefixes=icd_prefixes,
                keywords=keywords, icd9_dict=icd9_dict, icd10_dict=icd10_dict,
                biologic_atc_codes=biologic_atc, steroid_atc_codes=steroid_atc,
            ))
        except Exception as e:
            print(f"[rmt23345_events] Warning: could not load {source}: {e}")

    if not parts:
        return _EMPTY.copy()

    combined = pd.concat(parts, ignore_index=True).sort_values("start_date")

    #section added to apply filters so that user can chose patients from and to a particular date,
    #and also specific patient IDs
    # Apply filters from study_config.yaml
    if config:
        f = config.get("filters", {}) or {}
        if f.get("date_from"):
            combined = combined[
                combined["start_date"] >= pd.Timestamp(f["date_from"], tz="UTC")
            ]
        if f.get("date_to"):
            combined = combined[
                combined["start_date"] <= pd.Timestamp(f["date_to"], tz="UTC")
            ]
        if f.get("patients"):
            allowed = {str(p) for p in f["patients"]}
            combined = combined[combined["patient_id"].astype(str).isin(allowed)]

    if patient_id is not None:
        combined = combined[combined["patient_id"].astype(str) == str(patient_id)]

    return combined.reset_index(drop=True)
