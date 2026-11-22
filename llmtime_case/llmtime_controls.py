"""LLMTime case (2026-11-13): LLMTime (Gruver et al., NeurIPS 2023) public forecasts vs controls the paper did not report.

Zero LLM calls, CPU only, no network.

One file with two subcommands (one file because `python -I` does not put the script folder on sys.path):

  stats    Fit statistical baselines (statsforecast AutoETS / AutoARIMA / AutoTheta, plus statsforecast's own
           SeasonalNaive / Naive as a cross-check of the numpy implementation below) on the 8 Darts training segments.
           Needs the separate venv that has statsforecast. Reads ONLY the public Darts CSV files, never a pickle.

  compare  Load LLMTime's precomputed pickles with a restricted unpickler, run the validity gates, compute seasonal
           naive / naive (numpy only), merge the stats forecasts if given, write per-series CSVs and summary.txt.
           Runs in a Python environment with numpy and pandas.

Test split = LLMTime's own (data/small_context.py, read as text, not imported): GasRateCO2 uses its 2nd column (CO2%),
Sunspots is subsampled every 4th point, HeartRate every 2nd point, split = int(len * (1 - 0.2)); the whole test segment
is forecast in one shot from the end of the training segment (horizon 24-180).
Monash (optional): ground truth = last H points of each series in the public .tsf files (Zenodo), series order =
LLMTime's np.random.seed(0) permutation (data/monash.py), verified against the per-series MAEs stored in the pickles.

Security: the restricted Unpickler of an earlier pickle-inspection script (allowlist unchanged), plus ONE reviewed addition:
`data.serialize.SerializerSettings` (LLMTime's own dataclass of serialization options, referenced by some Monash pickles)
is mapped to InertSerializerSettings, an empty class defined in this file. Unpickling it creates an empty object and
pickle's BUILD step only fills its __dict__; no LLMTime code is imported or executed. Every other non-allowlisted class
is still refused and reported by name (never widened automatically).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import pickle
import re
import sys
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd

# ----------------------------------------------------------------------------------------------------------------------
# Fixed in advance (criteria written in advance). Do not change after seeing results.
# ----------------------------------------------------------------------------------------------------------------------
TESTFRAC = 0.2                 # LLMTime get_datasets(testfrac=0.2)
N_CONTROL_SAMPLES = 20         # Gaussian samples drawn for each control, = GPT-3 sample count in the Darts pickles
SEED = 0
TOL_REPORTED = 0.02            # relative tolerance when reproducing numbers in darts_results_agg.csv
MONASH_RTOL = 1e-5             # relative tolerance when reproducing the per-series MAEs stored in Monash pickles
Z975 = 1.959963984540054
MAX_BYTES = 300 * 1024 * 1024

# Darts: file names and md5 from darts/datasets/datasets.py (unit8co/darts master, checked 2026-11-13).
# m = seasonal period used by the seasonal naive, fixed from the sampling frequency BEFORE looking at any result:
#   monthly 12, quarterly 4; GasRateCO2 (gas furnace, 9 s steps) and HeartRate (1 s after LLMTime's ::2) have no
#   calendar season -> m = 1 (seasonal naive = naive); Sunspots after LLMTime's ::4 is one point per 4 months, and the
#   ~11-year solar cycle is 132 months = 33 steps -> m = 33 (quasi-periodic; flagged in the notes).
DARTS = {
    "AirPassengersDataset": dict(file="AirPassengers.csv", md5="167ffa96204a2b47339c21eea25baf32", time="Month",
                                 fmt=None, col=0, step=1, m=12, agg="AirPassengers"),
    "AusBeerDataset": dict(file="ausbeer.csv", md5="1f4028a570a20939411cc04de7364bbd", time="date",
                           fmt="%Y-%m-%d", col=0, step=1, m=4, agg="AusBeer"),
    "GasRateCO2Dataset": dict(file="gasrate_co2.csv", md5="77bf383715a9cf81459f81fe17baf3b0", time=None,
                              fmt=None, col=1, step=1, m=1, agg="GasRateCO2"),
    "MonthlyMilkDataset": dict(file="monthly-milk.csv", md5="4784443e696da45d7082e76a67687b93", time="Month",
                               fmt="%Y-%m", col=0, step=1, m=12, agg="MonthlyMilk"),
    "SunspotsDataset": dict(file="monthly-sunspots.csv", md5="4d27019c43d9c256d528f1bd6c5f40e0", time="Month",
                            fmt="%Y-%m", col=0, step=4, m=33, agg="Sunspots"),
    "WineDataset": dict(file="wineind.csv", md5="b68971d7e709ad0b7e6300cab977e3cd", time="date",
                        fmt="%Y-%m-%d", col=0, step=1, m=12, agg="Wine"),
    "WoolyDataset": dict(file="woolyrnq.csv", md5="4be8b12314db94c8fd76f5c674454bf0", time="date",
                         fmt="%Y-%m-%d", col=0, step=1, m=4, agg="Wooly"),
    "HeartRateDataset": dict(file="heart_rate.csv", md5="3c4a108e1116867cf056dc5be2c95386", time=None,
                             fmt=None, col=0, step=2, m=1, agg="HeartRate"),
}
DARTS_ORDER = ["AirPassengersDataset", "AusBeerDataset", "GasRateCO2Dataset", "MonthlyMilkDataset",
               "SunspotsDataset", "WineDataset", "WoolyDataset", "HeartRateDataset"]

# pickle key -> label used in outputs, family
MAIN_KEYS = {
    "gp": ("SM-GP", "author_baseline"), "arima": ("ARIMA(authors)", "author_baseline"),
    "TCN": ("TCN", "author_baseline"), "N-BEATS": ("N-BEATS", "author_baseline"), "N-HiTS": ("N-HiTS", "author_baseline"),
    "ada": ("ada", "LLM"), "babbage": ("babbage", "LLM"), "curie": ("curie", "LLM"),
    "text-davinci-003": ("GPT-3", "LLM"), "promptcast": ("PromptCast(GPT-3)", "LLM"),
}
GPT4_KEYS = {"gpt-4": ("GPT-4", "LLM"), "text-davinci-003": ("GPT-3(gpt4file)", "LLM")}
GATE_LABELS = {"SM-GP": "SM-GP", "ARIMA(authors)": "ARIMA", "TCN": "TCN", "N-BEATS": "N-BEATS", "N-HiTS": "N-HiTS",
               "GPT-3": "GPT-3"}  # our label -> 'Type' in darts_results_agg.csv
AUTHOR_SET = ["SM-GP", "ARIMA(authors)", "TCN", "N-BEATS", "N-HiTS"]
PICKLE_LLMS = ["GPT-3", "GPT-4", "GPT-3(gpt4file)", "ada", "babbage", "curie", "PromptCast(GPT-3)"]
LLAMA_AGG_TYPE = "LLaMA-2 70B"
STAT_METHODS = ["AutoETS", "AutoARIMA", "AutoTheta"]
CROSSCHECK_METHODS = ["SeasonalNaive_sf", "Naive_sf"]
PRIMARY_STAT = "AutoETS"
MAE_NORMS = ["mean_abs_test", "range_full", "range_train", "std_test", "mean_abs_train"]
MAE_CANDIDATES = [f"{kind}/{norm}" for kind in ("median", "samples") for norm in MAE_NORMS]

# Monash: pickle name -> (candidate zip files in priority order, m, m_alt or None, expected @frequency)
# zip names from the HF monash_tsf loader (Monash-University/monash_tsf) plus the 'without missing values' variants.
# m follows the Monash archive's MASE seasonality per frequency (daily 7, weekly 52, monthly 12, quarterly 4, yearly 1,
# hourly 24, half-hourly 48, 10-minutes 144); m_alt is a sensitivity value written in advance.
MONASH = {
    "weather": (["weather_dataset.zip"], 7, None, "daily"),
    "covid_deaths": (["covid_deaths_dataset.zip"], 7, None, "daily"),
    "solar_weekly": (["solar_weekly_dataset.zip"], 52, None, "weekly"),
    "tourism_monthly": (["tourism_monthly_dataset.zip"], 12, None, "monthly"),
    "tourism_quarterly": (["tourism_quarterly_dataset.zip"], 4, None, "quarterly"),
    "tourism_yearly": (["tourism_yearly_dataset.zip"], 1, None, "yearly"),
    "australian_electricity_demand": (["australian_electricity_demand_dataset.zip"], 48, 336, "half_hourly"),
    "pedestrian_counts": (["pedestrian_counts_dataset.zip"], 24, 168, "hourly"),
    "traffic_hourly": (["traffic_hourly_dataset.zip"], 24, 168, "hourly"),
    "traffic_weekly": (["traffic_weekly_dataset.zip"], 52, None, "weekly"),
    "hospital": (["hospital_dataset.zip"], 12, None, "monthly"),
    "fred_md": (["fred_md_dataset.zip"], 12, None, "monthly"),
    "us_births": (["us_births_dataset.zip"], 7, 365, "daily"),
    "nn5_weekly": (["nn5_weekly_dataset.zip"], 52, None, "weekly"),
    "nn5_daily": (["nn5_daily_dataset_without_missing_values.zip", "nn5_daily_dataset_with_missing_values.zip"],
                  7, None, "daily"),
    "saugeenday": (["saugeenday_dataset.zip"], 7, 365, "daily"),
    "cif_2016": (["cif_2016_dataset.zip"], 12, None, "monthly"),
    "bitcoin": (["bitcoin_dataset_without_missing_values.zip", "bitcoin_dataset_with_missing_values.zip"],
                7, None, "daily"),
    "sunspot": (["sunspot_dataset_without_missing_values.zip", "sunspot_dataset_with_missing_values.zip"],
                7, 1, "daily"),
    "solar_10_minutes": (["solar_10_minutes_dataset.zip"], 144, 1008, "10_minutes"),
}
MONASH_BASELINES = ["SES", "Theta", "TBATS", "ETS", "(DHR-)ARIMA", "PR", "CatBoost", "FFNN", "DeepAR", "N-BEATS",
                    "WaveNet", "Transformer"]


# ----------------------------------------------------------------------------------------------------------------------
# Restricted unpickler (from an earlier pickle-inspection script, allowlist unchanged) + one inert shell class
# ----------------------------------------------------------------------------------------------------------------------
SAFE_BUILTINS = {"dict", "list", "tuple", "set", "frozenset", "slice", "complex", "float", "int", "str", "bytes",
                 "bytearray", "bool", "range", "object"}
ALLOWED_MODULE_PREFIXES = (
    "numpy.core.multiarray", "numpy._core.multiarray", "numpy.core.numeric", "numpy._core.numeric", "numpy.dtypes",
    "pandas.core.frame", "pandas.core.series", "pandas.core.indexes", "pandas.core.internals", "pandas.core.arrays",
    "pandas.core.dtypes", "pandas._libs.internals", "pandas._libs.tslibs", "pandas._libs.arrays",
)
ALLOWED_EXACT = {("numpy", "ndarray"), ("numpy", "dtype"), ("collections", "OrderedDict"), ("collections", "defaultdict"),
                 ("copyreg", "_reconstructor"), ("_codecs", "encode"), ("datetime", "datetime"), ("datetime", "date"),
                 ("datetime", "timedelta"), ("numpy", "float64"), ("numpy", "int64"), ("types", "SimpleNamespace")}
OLD_NUMERIC_INDEX = {"Int64Index", "UInt64Index", "Float64Index", "NumericIndex"}
# Classes whose constructors touch the file system; never allowed even if reachable through an allowed module.
DENY_NAMES = {"memmap", "HDFStore", "ExcelWriter", "ExcelFile", "HDFStore", "StataWriter", "ZipFile", "open"}
# Functions (not classes) that numpy/pandas pickles legitimately call during reconstruction.
SAFE_FUNCS = {"_reconstruct", "scalar", "new_block", "new_block_2d"}
# Added 2026-11-14: pandas' own Darts pickles reference this Cython reconstruction helper for
# NDArrayBacked arrays (DatetimeArray etc.). Exact (module, name) only -- not a prefix family.
ALLOWED_FUNC_EXACT = {("pandas._libs.arrays", "__pyx_unpickle_NDArrayBacked")}
# Extra modules an allowed object may be *defined* in (e.g. numpy.ndarray reports "numpy"; Index helpers live here).
OBJ_MODULE_EXTRA = ("numpy.core", "numpy._core", "pandas.core.indexes", "pandas._libs")


class InertSerializerSettings:
    """Inert stand-in for LLMTime's data.serialize.SerializerSettings. Defines no behaviour: unpickling creates an
    empty instance and pickle's BUILD step only fills its __dict__ with the stored option values."""

    def __repr__(self):
        return f"InertSerializerSettings({vars(self)!r})"


SHELLS = {("data.serialize", "SerializerSettings"): InertSerializerSettings}


class SafeUnpickler(pickle.Unpickler):
    refused: list = []
    shelled: list = []

    # Hardened 2026-11-13 after a code review: the prefix rule alone let any attribute of an allowed
    # module through (and dotted names are resolved as attribute chains under protocol >= 4). Now: no dotted names;
    # objects from prefixed modules must themselves be defined in numpy/pandas core modules, and must be either a
    # class or a known reconstruction function.
    def find_class(self, module, name):
        if (module, name) in SHELLS:
            SafeUnpickler.shelled.append(f"{module}.{name}")
            return SHELLS[(module, name)]
        if "." in name or name in DENY_NAMES:
            SafeUnpickler.refused.append(f"{module}.{name}")
            raise pickle.UnpicklingError(f"refused dotted name {module}.{name}")
        if module == "pandas.core.indexes.numeric" and name in OLD_NUMERIC_INDEX:
            return pd.Index
        if module == "builtins" and name in SAFE_BUILTINS:
            return super().find_class(module, name)
        if (module, name) in ALLOWED_EXACT:
            return super().find_class(module, name)
        if (module, name) in ALLOWED_FUNC_EXACT:
            obj = super().find_class(module, name)
            obj_mod = getattr(obj, "__module__", "") or ""
            if callable(obj) and obj_mod.startswith(ALLOWED_MODULE_PREFIXES + OBJ_MODULE_EXTRA):
                return obj
        if module.startswith(ALLOWED_MODULE_PREFIXES):
            obj = super().find_class(module, name)
            obj_mod = getattr(obj, "__module__", "") or ""
            mod_ok = obj_mod == "numpy" or obj_mod.startswith(ALLOWED_MODULE_PREFIXES + OBJ_MODULE_EXTRA)
            fn_ok = name in SAFE_FUNCS or name.startswith(("_unpickle", "_new_"))
            if mod_ok and (isinstance(obj, type) or (callable(obj) and fn_ok)):
                return obj
        SafeUnpickler.refused.append(f"{module}.{name}")
        raise pickle.UnpicklingError(f"refused class {module}.{name}")


def load_pickle(path: Path):
    if not path.exists():
        return None, "missing file"
    if path.stat().st_size > MAX_BYTES:
        return None, "skipped: larger than 300 MB"
    try:
        with path.open("rb") as fh:
            return SafeUnpickler(fh).load(), ""
    except Exception as exc:  # noqa: BLE001
        return None, f"NOT LOADED: {type(exc).__name__}: {exc}"


# ----------------------------------------------------------------------------------------------------------------------
# Data
# ----------------------------------------------------------------------------------------------------------------------
def load_darts_series(csv_dir: Path, name: str):
    """Reproduce darts' loader + LLMTime's get_dataset/get_datasets. Returns train Series, test Series, md5, note."""
    spec = DARTS[name]
    path = csv_dir / spec["file"]
    raw = path.read_bytes()
    md5 = hashlib.md5(raw).hexdigest()
    df = pd.read_csv(path)
    note = ""
    if spec["time"] is not None:
        try:
            idx = pd.DatetimeIndex(pd.to_datetime(df[spec["time"]], format=spec["fmt"]))
        except Exception as exc:  # noqa: BLE001
            idx = pd.DatetimeIndex(pd.to_datetime(df[spec["time"]]))
            note = f"time format {spec['fmt']} failed ({type(exc).__name__}); parsed without format"
        vals = df.drop(columns=[spec["time"]])
    else:
        idx = pd.RangeIndex(len(df))
        vals = df
    if spec["col"] == 0 and vals.shape[1] != 1:
        raise ValueError(f"{name}: expected 1 value column, got {list(vals.columns)}")
    col = vals.columns[spec["col"]]
    series = pd.Series(vals[col].to_numpy(dtype=float), index=idx)
    series = series.iloc[::spec["step"]]
    split = int(len(series) * (1 - TESTFRAC))
    return series.iloc[:split], series.iloc[split:], md5, note


def read_tsf_zip(path: Path):
    """Minimal reader for the Monash .tsf format, reading the single .tsf member of the zip in memory (no extraction)."""
    with zipfile.ZipFile(path) as zf:
        names = [n for n in zf.namelist() if n.lower().endswith(".tsf")]
        if len(names) != 1:
            raise ValueError(f"expected exactly one .tsf member, got {names}")
        raw = zf.read(names[0])
    text = raw.decode("utf-8", errors="replace")
    meta, series, in_data = {}, [], False
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if not in_data:
            low = line.lower()
            if low.startswith("@data"):
                in_data = True
            elif low.startswith("@") and not low.startswith("@attribute"):
                parts = line.split(None, 1)
                meta[parts[0][1:].lower()] = parts[1].strip() if len(parts) > 1 else ""
            continue
        values = line.split(":")[-1].replace("?", "nan").split(",")
        series.append(np.array(values, dtype=float))
    return series, meta


# ----------------------------------------------------------------------------------------------------------------------
# Forecasts and metrics
# ----------------------------------------------------------------------------------------------------------------------
def seasonal_naive(hist, horizon: int, m: int):
    """Point forecast and h-step sigma of the seasonal naive (Hyndman & Athanasopoulos, fpp3 5.5):
    yhat_{T+h} = y_{T+h-m(k+1)}, sigma_h = sigma * sqrt(k+1), k = floor((h-1)/m), sigma = RMS of in-sample seasonal
    differences. m = 1 gives the naive (random walk). If the history is shorter than m + 2, m falls back to 1.
    Missing values in the history are forward-filled first."""
    hist = pd.Series(np.asarray(hist, dtype=float)).ffill().to_numpy()
    m_eff = m if (m > 1 and len(hist) >= m + 2) else 1
    last = hist[-m_eff:]
    point = np.array([last[h % m_eff] for h in range(horizon)], dtype=float)
    diffs = hist[m_eff:] - hist[:-m_eff]
    diffs = diffs[np.isfinite(diffs)]
    sigma = float(np.sqrt(np.mean(diffs ** 2))) if diffs.size else float("nan")
    k = np.arange(horizon) // m_eff
    return point, sigma * np.sqrt(k + 1.0), m_eff


def gaussian_samples(point, sigma_h, seed_parts):
    rng = np.random.default_rng(seed_parts)
    z = rng.standard_normal((N_CONTROL_SAMPLES, len(point)))
    return point[None, :] + np.asarray(sigma_h, dtype=float)[None, :] * z


def crps_llmtime(y, samples):
    """LLMTime data/metrics.py calculate_crps (num_quantiles=20), re-implemented in numpy (jax there)."""
    qs = np.linspace(0, 1.0, 21)[1:]
    total = 0.0
    for q in qs:
        qp = np.quantile(samples, q, axis=0)
        total += 2 * np.sum(np.abs((qp - y) * ((y <= qp) * 1.0 - q)))
    return float(total / (np.sum(np.abs(y)) * len(qs)))


def mae_candidates(y, ytr, point, samples):
    full = np.concatenate([ytr, y])
    norms = {"mean_abs_test": np.mean(np.abs(y)), "range_full": np.max(full) - np.min(full),
             "range_train": np.max(ytr) - np.min(ytr), "std_test": np.std(y), "mean_abs_train": np.mean(np.abs(ytr))}
    raw = {"median": float(np.mean(np.abs(point - y))), "samples": float(np.mean(np.abs(samples - y[None, :])))}
    return {f"{k}/{n}": raw[k] / norms[n] for k in ("median", "samples") for n in MAE_NORMS}


def rel_err(ours, reported):
    if ours is None or reported is None:
        return float("nan")
    if not (np.isfinite(ours) and np.isfinite(reported)) or reported == 0:
        return float("nan")
    return abs(ours - reported) / abs(reported)


def as_1d(x):
    if isinstance(x, (pd.Series, pd.DataFrame)):
        x = x.to_numpy()
    return np.asarray(x, dtype=float).ravel()


def as_2d(x):
    if isinstance(x, pd.DataFrame):
        x = x.to_numpy()
    arr = np.asarray(x, dtype=float)
    return arr[None, :] if arr.ndim == 1 else arr


def entry_to_method(entry):
    med, smp = entry.get("median"), entry.get("samples")
    if med is None or smp is None:  # added after a code review: as_2d(None) would give a 0-d array and crash later
        raise ValueError(f"missing {'median' if med is None else 'samples'}")
    index = med.index if isinstance(med, pd.Series) else (smp.columns if isinstance(smp, pd.DataFrame) else None)
    nll = entry.get("NLL/D")
    try:
        nll = float(nll) if nll is not None else float("nan")
    except (TypeError, ValueError):
        nll = float("nan")
    return dict(point=as_1d(med), samples=as_2d(smp), index=index, nll=nll)


def same_index(a, b) -> bool:
    a, b = pd.Index(a), pd.Index(b)
    if len(a) != len(b):
        return False
    if a.equals(b):
        return True
    return bool((a.astype(str) == b.astype(str)).all())


def fmt(x, nd=4):
    if x is None or (isinstance(x, float) and not np.isfinite(x)):
        return "nan"
    if abs(x) >= 1e5 or (abs(x) < 1e-3 and x != 0):
        return f"{x:.{nd}g}"
    return f"{x:.{nd}f}"


def geomean(vals):
    vals = [v for v in vals if v is not None and np.isfinite(v) and v > 0]
    return float(np.exp(np.mean(np.log(vals)))) if vals else float("nan")


# ----------------------------------------------------------------------------------------------------------------------
# stats subcommand (separate venv with statsforecast; reads CSV only)
# ----------------------------------------------------------------------------------------------------------------------
def describe_stat_model(label, mdl):
    try:
        if label == "AutoETS":
            return str(mdl.model_["method"])
        if label == "AutoARIMA":
            from statsforecast.arima import arima_string
            return str(arima_string(mdl.model_))
        if label == "AutoTheta":
            return str(mdl.model_.get("modeltype", ""))
    except Exception:  # noqa: BLE001
        return ""
    return ""


def cmd_stats(a) -> int:
    import statsforecast
    from statsforecast.models import AutoARIMA, AutoETS, AutoTheta, Naive, SeasonalNaive

    rows, info = [], {"statsforecast": getattr(statsforecast, "__version__", "?"), "python": sys.version,
                      "numpy": np.__version__, "pandas": pd.__version__, "datasets": {}}
    for name in DARTS_ORDER:
        tr, te, md5, note = load_darts_series(a.darts_csv_dir, name)
        y, horizon, m = tr.to_numpy(dtype=float), len(te), DARTS[name]["m"]
        info["datasets"][name] = dict(n_train=len(y), horizon=horizon, m=m, md5=md5, note=note)
        ctors = {"AutoETS": lambda: AutoETS(season_length=m), "AutoARIMA": lambda: AutoARIMA(season_length=m),
                 "AutoTheta": lambda: AutoTheta(season_length=m),
                 "SeasonalNaive_sf": lambda: SeasonalNaive(season_length=m), "Naive_sf": lambda: Naive()}
        for label, ctor in ctors.items():
            try:
                mdl = ctor()
                mdl.fit(y)
                out = mdl.predict(h=horizon, level=[95])
                mean = np.asarray(out["mean"], dtype=float)
                lo = np.asarray(out["lo-95"], dtype=float)
                hi = np.asarray(out["hi-95"], dtype=float)
                status, desc = "ok", describe_stat_model(label, mdl)
            except Exception as exc:  # noqa: BLE001
                mean = lo = hi = np.full(horizon, np.nan)
                status, desc = f"error: {type(exc).__name__}: {exc}", ""
            print(f"{name} {label}: {status} {desc}")
            for h in range(horizon):
                rows.append(dict(dataset=name, method=label, h=h + 1, mean=mean[h], lo95=lo[h], hi95=hi[h],
                                 status=status, desc=desc))
    a.out.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(a.out, index=False)
    a.out.with_suffix(".info.json").write_text(json.dumps(info, indent=2), encoding="utf-8")
    print(f"wrote {a.out}")
    return 0


# ----------------------------------------------------------------------------------------------------------------------
# compare subcommand: Darts
# ----------------------------------------------------------------------------------------------------------------------
def read_stat_csv(path):
    if path is None:
        return None, "no --stat-csv given"
    if not path.exists():
        return None, f"--stat-csv not found: {path}"
    return pd.read_csv(path), ""


def darts_block(a, root: Path, out: Path, lines: list, info: dict):
    agg = pd.read_csv(root / "precomputed_outputs" / "deterministic_csvs" / "darts_results_agg.csv")
    stat_df, stat_note = read_stat_csv(a.stat_csv)
    lines.append("== DARTS ==")
    if stat_note:
        lines.append(f"stats forecasts: {stat_note} -> AutoETS/AutoARIMA/AutoTheta endpoints are not available")

    gate_rows, metric_rows, point_rows, gate_entries = [], [], [], []
    ds = {}  # dataset -> dict(methods=..., y, ytr, g1, ...)
    for di, name in enumerate(DARTS_ORDER):
        spec = DARTS[name]
        rec = dict(ok_csv=False, g1=False, methods={})
        ds[name] = rec
        try:
            tr, te, md5, note = load_darts_series(a.darts_csv_dir, name)
        except Exception as exc:  # noqa: BLE001
            gate_rows.append(dict(dataset=name, check="G0_csv_load", ok=False, detail=f"{type(exc).__name__}: {exc}"))
            continue
        rec.update(ok_csv=True, ytr=tr.to_numpy(dtype=float), y=te.to_numpy(dtype=float), H=len(te), m=spec["m"])
        y, ytr, horizon = rec["y"], rec["ytr"], rec["H"]
        gate_rows.append(dict(dataset=name, check="G0_md5", ok=md5 == spec["md5"], detail=f"{md5} vs darts {spec['md5']}"
                              + (f"; {note}" if note else "")))
        main, err_main = load_pickle(root / "precomputed_outputs" / "darts" / f"{name}.pkl")
        gpt4, err_gpt4 = load_pickle(root / "precomputed_outputs" / "darts" / "gpt4" / f"{name}.pkl")
        for obj, err, keys, src in ((main, err_main, MAIN_KEYS, "darts/"), (gpt4, err_gpt4, GPT4_KEYS, "darts/gpt4/")):
            if not isinstance(obj, dict):
                gate_rows.append(dict(dataset=name, check=f"pickle {src}", ok=False, detail=err or type(obj).__name__))
                continue
            for key, (label, family) in keys.items():
                if key in obj:
                    try:
                        mth = entry_to_method(obj[key])
                    except Exception as exc:  # noqa: BLE001
                        gate_rows.append(dict(dataset=name, check=f"extract {src}{key}", ok=False,
                                              detail=f"{type(exc).__name__}: {exc}"))
                        continue
                    mth.update(family=family, source=f"pickle {src}{key}")
                    rec["methods"][label] = mth
        # G1: every loaded method has horizon H and (where an index is stored) the same labels as the rebuilt test
        # (changed after a code review) a misaligned method is dropped instead of crashing later; the dataset passes G1
        # iff GPT-3 (the method the main judgment P1 uses) is present and aligned. Other methods' failures are reported.
        for label in list(rec["methods"].keys()):
            mth = rec["methods"][label]
            ok_len = (mth["samples"].ndim == 2 and len(mth["point"]) == horizon
                      and mth["samples"].shape[1] == horizon)
            ok_idx = True if mth["index"] is None else same_index(mth["index"], te.index)
            gate_rows.append(dict(dataset=name, check=f"G1_align {label}", ok=ok_len and ok_idx,
                                  detail=f"len {len(mth['point'])}/{mth['samples'].shape} vs H={horizon}; index_ok={ok_idx}"))
            if not (ok_len and ok_idx):
                del rec["methods"][label]
        rec["g1"] = "GPT-3" in rec["methods"]
        # G1b (diagnostic): PromptCast's prompt text lists the training history (prec 0) -> compare with CSV
        if isinstance(main, dict) and "promptcast" in main:
            try:
                txt = str(main["promptcast"]["input_strs"][0])
                mt = re.search(r"past (\d+) time steps are ([-\d,\s]+)", txt)
                if mt:
                    nums = np.array([float(v) for v in mt.group(2).replace(" ", "").strip(",").split(",") if v != ""])
                    tail = ytr[-len(nums):] if len(nums) <= len(ytr) else ytr
                    close = float(np.mean(np.abs(nums[-len(tail):] - np.round(tail)) <= 1.0)) if len(tail) else float("nan")
                    gate_rows.append(dict(dataset=name, check="G1b_promptcast_history (diagnostic)", ok=close >= 0.99,
                                          detail=f"stated {mt.group(1)} steps, parsed {len(nums)}, n_train {len(ytr)}, "
                                                 f"share within 1 of round(train) = {fmt(close)}"))
            except Exception as exc:  # noqa: BLE001
                gate_rows.append(dict(dataset=name, check="G1b_promptcast_history (diagnostic)", ok=False,
                                      detail=f"{type(exc).__name__}: {exc}"))
        # metrics for pickle methods + entries for G2
        for label, mth in rec["methods"].items():
            mth["crps"] = crps_llmtime(y, mth["samples"])
            mth["cands"] = mae_candidates(y, ytr, mth["point"], mth["samples"])
            mth["mae_raw"] = float(np.mean(np.abs(mth["point"] - y)))
            if label in GATE_LABELS:
                row = agg[(agg["Dataset"] == spec["agg"]) & (agg["Type"] == GATE_LABELS[label])]
                if len(row) == 1:
                    r = row.iloc[0]
                    gate_entries.append(dict(dataset=name, label=label, rep_mae=float(r["MAE"]), rep_crps=float(r["CRPS"]),
                                             rep_nll=float(r["NLL/D"]), crps=mth["crps"], cands=mth["cands"],
                                             nll=mth["nll"]))
        # controls: numpy seasonal naive and naive
        for ci, (label, m_use) in enumerate((("SNaive", spec["m"]), ("Naive", 1))):
            point, sig, m_eff = seasonal_naive(ytr, horizon, m_use)
            rec["methods"][label] = dict(point=point, samples=gaussian_samples(point, sig, [SEED, di, ci]), index=None,
                                         nll=float("nan"), family="control", source=f"numpy m={m_eff}")
        # controls: statsforecast
        if stat_df is not None:
            for ci, label in enumerate(STAT_METHODS + CROSSCHECK_METHODS, start=10):
                sub = stat_df[(stat_df["dataset"] == name) & (stat_df["method"] == label)].sort_values("h")
                if len(sub) != horizon or not (sub["status"] == "ok").all():
                    gate_rows.append(dict(dataset=name, check=f"stats {label}", ok=False,
                                          detail=f"rows {len(sub)} vs H={horizon}; status "
                                                 f"{sub['status'].iloc[0] if len(sub) else 'none'}"))
                    continue
                point = sub["mean"].to_numpy(dtype=float)
                sig = (sub["hi95"].to_numpy(dtype=float) - sub["lo95"].to_numpy(dtype=float)) / (2 * Z975)
                fam = "control" if label in STAT_METHODS else "crosscheck"
                rec["methods"][label] = dict(point=point, samples=gaussian_samples(point, sig, [SEED, di, ci]),
                                             index=None, nll=float("nan"), family=fam,
                                             source=f"statsforecast {sub['desc'].iloc[0]}")
        for label, mth in rec["methods"].items():
            if "crps" not in mth:
                mth["crps"] = crps_llmtime(y, mth["samples"])
                mth["cands"] = mae_candidates(y, ytr, mth["point"], mth["samples"])
                mth["mae_raw"] = float(np.mean(np.abs(mth["point"] - y)))
            for h in range(horizon):
                point_rows.append(dict(dataset=name, method=label, h=h + 1, y=y[h], point=mth["point"][h]))
        if "SNaive" in rec["methods"] and "SeasonalNaive_sf" in rec["methods"]:
            dmax = float(np.max(np.abs(rec["methods"]["SNaive"]["point"] - rec["methods"]["SeasonalNaive_sf"]["point"])))
            gate_rows.append(dict(dataset=name, check="X_crosscheck SNaive numpy vs statsforecast (diagnostic)",
                                  ok=dmax <= 1e-8 * max(1.0, float(np.max(np.abs(y)))), detail=f"max abs diff {dmax:.3g}"))

    # identify the MAE definition behind darts_results_agg.csv; check the CRPS formula
    total = len(gate_entries)
    hits = {c: sum(rel_err(e["cands"][c], e["rep_mae"]) <= TOL_REPORTED for e in gate_entries) for c in MAE_CANDIDATES}
    best = max(MAE_CANDIDATES, key=lambda c: (hits[c], -MAE_CANDIDATES.index(c))) if total else None
    ident = best if (total and hits[best] >= 0.75 * total) else None
    crps_hits = sum(rel_err(e["crps"], e["rep_crps"]) <= TOL_REPORTED for e in gate_entries)
    crps_ok = bool(total) and crps_hits >= 0.75 * total
    nll_hits = sum(rel_err(e["nll"], e["rep_nll"]) <= 1e-6 for e in gate_entries)
    info["darts_mae_definition"] = dict(hits=hits, total=total, identified=ident, crps_hits=crps_hits, crps_ok=crps_ok)
    for e in gate_entries:
        e_crps = rel_err(e["crps"], e["rep_crps"])
        e_mae = rel_err(e["cands"][ident], e["rep_mae"]) if ident else float("nan")
        e["match"] = (e_crps <= TOL_REPORTED) or (ident is not None and e_mae <= TOL_REPORTED)
        gate_rows.append(dict(dataset=e["dataset"], check=f"G2_reproduce {e['label']}", ok=bool(e["match"]),
                              detail=f"CRPS ours {fmt(e['crps'])} vs rep {fmt(e['rep_crps'])} (rel {fmt(e_crps)}); "
                                     f"MAE[{ident}] rel {fmt(e_mae)}; NLL/D pickle {fmt(e['nll'])} vs rep {fmt(e['rep_nll'])}"))
    valid = []
    for name in DARTS_ORDER:
        rec = ds[name]
        n_match = sum(1 for e in gate_entries if e["dataset"] == name and e["match"])
        rec["g2"] = n_match >= 4
        rec["valid"] = bool(rec["ok_csv"] and rec["g1"] and rec["g2"])
        if rec["valid"]:
            valid.append(name)
        # LLaMA-2 70B: only the aggregate numbers exist
        row = agg[(agg["Dataset"] == DARTS[name]["agg"]) & (agg["Type"] == LLAMA_AGG_TYPE)]
        rec["llama"] = (float(row.iloc[0]["MAE"]), float(row.iloc[0]["CRPS"])) if len(row) == 1 else (np.nan, np.nan)

    # ---- write per-dataset/method metrics
    for name in DARTS_ORDER:
        rec = ds[name]
        for label, mth in rec.get("methods", {}).items():
            row = dict(dataset=name, valid_dataset=rec.get("valid", False), method=label, family=mth["family"],
                       source=mth["source"], n_samples=mth["samples"].shape[0], H=rec.get("H"), m=rec.get("m"),
                       mae_raw=mth["mae_raw"], crps=mth["crps"], nll_pickle=mth["nll"])
            for c in MAE_CANDIDATES:
                row[f"mae_{c}"] = mth["cands"][c]
            gpt3 = rec["methods"].get("GPT-3")
            row["mae_ratio_vs_GPT3"] = mth["mae_raw"] / gpt3["mae_raw"] if gpt3 else np.nan
            metric_rows.append(row)
        if rec.get("ok_csv"):
            metric_rows.append(dict(dataset=name, valid_dataset=rec.get("valid", False), method=LLAMA_AGG_TYPE + "(agg)",
                                    family="LLM_agg_only", source="darts_results_agg.csv", n_samples=np.nan,
                                    H=rec.get("H"), m=rec.get("m"), mae_raw=np.nan, crps=rec["llama"][1],
                                    nll_pickle=np.nan, **({f"mae_{ident}": rec["llama"][0]} if ident else {})))
    pd.DataFrame(metric_rows).to_csv(out / "darts_metrics.csv", index=False)
    pd.DataFrame(point_rows).to_csv(out / "darts_pointwise.csv", index=False)
    pd.DataFrame(gate_rows).to_csv(out / "darts_gates.csv", index=False)

    # ---- summary: gates
    lines.append(f"MAE definition behind darts_results_agg.csv: identified={ident}; best={best} "
                 f"({hits.get(best, 0) if best else 0}/{total} within {TOL_REPORTED:.0%}); all hits: {hits}")
    lines.append(f"CRPS formula reproduces reported CRPS: {crps_hits}/{total} -> crps_ok={crps_ok}; "
                 f"pickle NLL/D equals reported NLL/D: {nll_hits}/{total}")
    lines.append("dataset            H    m  md5  G1  G2(match/6)  valid")
    for name in DARTS_ORDER:
        rec = ds[name]
        md5ok = next((g["ok"] for g in gate_rows if g["dataset"] == name and g["check"] == "G0_md5"), False)
        n_match = sum(1 for e in gate_entries if e["dataset"] == name and e["match"])
        n_tot = sum(1 for e in gate_entries if e["dataset"] == name)
        lines.append(f"{name:<20} {str(rec.get('H', '-')):>4} {str(rec.get('m', '-')):>3}  {str(md5ok):<5} "
                     f"{str(rec.get('g1')):<5} {n_match}/{n_tot:<9} {rec.get('valid')}")
    lines.append(f"valid Darts datasets: {len(valid)}/8 {valid}")

    # ---- summary: per-dataset raw MAE table
    show = ["GPT-3", "GPT-4", "ARIMA(authors)", "SNaive", "Naive"] + [s for s in STAT_METHODS]
    lines.append("")
    lines.append("raw-scale MAE of the point forecast (LLM: pickle median; controls: point forecast)")
    lines.append("dataset              " + " ".join(f"{s:>14}" for s in show) + "   bestAuthor  SN/GPT3  ETS/GPT3")
    for name in DARTS_ORDER:
        rec = ds[name]
        if not rec.get("ok_csv"):
            continue
        mm = rec["methods"]
        vals = [mm[s]["mae_raw"] if s in mm else np.nan for s in show]
        best_author = min((mm[s]["mae_raw"] for s in AUTHOR_SET if s in mm), default=np.nan)
        g3 = mm["GPT-3"]["mae_raw"] if "GPT-3" in mm else np.nan
        sn = mm["SNaive"]["mae_raw"]
        ets = mm[PRIMARY_STAT]["mae_raw"] if PRIMARY_STAT in mm else np.nan
        lines.append(f"{name:<20} " + " ".join(f"{fmt(v):>14}" for v in vals)
                     + f"   {fmt(best_author):>10}  {fmt(sn / g3 if g3 else np.nan):>7}  {fmt(ets / g3 if g3 else np.nan):>8}")

    # ---- summary: counts written in advance (mechanical)
    def cmp_count(ctl, llm, metric="mae_raw", margin=1.0):
        n = k = 0
        ratios = []
        for name in valid:
            mm = ds[name]["methods"]
            if ctl not in mm:
                continue
            if llm == "LLAMA":
                if metric == "mae_raw":
                    if ident is None:
                        continue
                    a_ctl, a_llm = mm[ctl]["cands"][ident], ds[name]["llama"][0]
                else:
                    if not crps_ok:
                        continue
                    a_ctl, a_llm = mm[ctl]["crps"], ds[name]["llama"][1]
            else:
                if llm not in mm:
                    continue
                a_ctl, a_llm = mm[ctl][metric], mm[llm][metric]
            if not (np.isfinite(a_ctl) and np.isfinite(a_llm)) or a_llm <= 0:
                continue
            n += 1
            ratios.append(a_ctl / a_llm)
            k += int(a_ctl / a_llm <= margin)
        return k, n, ratios

    lines.append("")
    lines.append("counts written in advance over valid datasets: #(control <= LLM) / #compared   [also r<=1.05, r<=0.95; geomean r]")
    for ep, ctl, llm, metric in (("P1", "SNaive", "GPT-3", "mae_raw"), ("S1", PRIMARY_STAT, "GPT-3", "mae_raw"),
                                 ("S2a", "SNaive", "GPT-4", "mae_raw"), ("S2b", PRIMARY_STAT, "GPT-4", "mae_raw"),
                                 ("S3a", "SNaive", "LLAMA", "mae_raw"), ("S3b", PRIMARY_STAT, "LLAMA", "mae_raw"),
                                 ("S5a", "SNaive", "GPT-3", "crps"), ("S5b", PRIMARY_STAT, "GPT-3", "crps"),
                                 ("S5c", "SNaive", "LLAMA", "crps"), ("D1", "Naive", "GPT-3", "mae_raw"),
                                 ("D2", "AutoARIMA", "GPT-3", "mae_raw"), ("D3", "AutoTheta", "GPT-3", "mae_raw")):
        k, n, ratios = cmp_count(ctl, llm, metric)
        k105, _, _ = cmp_count(ctl, llm, metric, 1.05)
        k095, _, _ = cmp_count(ctl, llm, metric, 0.95)
        llm_name = LLAMA_AGG_TYPE + "(agg)" if llm == "LLAMA" else llm
        lines.append(f"{ep:<4} {ctl:>10} vs {llm_name:<18} [{metric}]: {k}/{n}   r<=1.05: {k105}/{n}   r<=0.95: {k095}/{n}"
                     f"   geomean r = {fmt(geomean(ratios))}")
        info.setdefault("darts_counts", {})[ep] = dict(control=ctl, llm=llm_name, metric=metric, k=k, n=n, k105=k105,
                                                       k095=k095, geomean=geomean(ratios))

    # S4: GPT-3 'wins' before and after adding the two controls written in advance
    wins_rep, wins_aug, wins_arima, sn_in_arima, ets_in_arima = [], [], [], [], []
    for name in valid:
        mm = ds[name]["methods"]
        if "GPT-3" not in mm:
            continue
        g3 = mm["GPT-3"]["mae_raw"]
        rep = [mm[s]["mae_raw"] for s in AUTHOR_SET if s in mm]
        aug = rep + [mm[s]["mae_raw"] for s in ("SNaive", PRIMARY_STAT) if s in mm]
        if rep and g3 < min(rep):
            wins_rep.append(name)
        if aug and g3 < min(aug):
            wins_aug.append(name)
        if "ARIMA(authors)" in mm and g3 < mm["ARIMA(authors)"]["mae_raw"]:
            wins_arima.append(name)
            if mm["SNaive"]["mae_raw"] <= g3:
                sn_in_arima.append(name)
            if PRIMARY_STAT in mm and mm[PRIMARY_STAT]["mae_raw"] <= g3:
                ets_in_arima.append(name)
    lines.append(f"S4   GPT-3 lowest MAE vs the authors' 5 baselines: {len(wins_rep)} {wins_rep}")
    lines.append(f"     GPT-3 lowest MAE vs authors' 5 + SNaive + {PRIMARY_STAT}: {len(wins_aug)} {wins_aug}")
    lines.append(f"P2   GPT-3 beats ARIMA(authors) on {len(wins_arima)} {wins_arima}; of these SNaive <= GPT-3 on "
                 f"{len(sn_in_arima)} {sn_in_arima}; {PRIMARY_STAT} <= GPT-3 on {len(ets_in_arima)} {ets_in_arima}")
    # D4: oracle best LLM per dataset (favourable to the LLM)
    k_or = n_or = 0
    for name in valid:
        mm = ds[name]["methods"]
        llm_vals = [mm[s]["mae_raw"] for s in PICKLE_LLMS if s in mm and np.isfinite(mm[s]["mae_raw"])]
        if llm_vals:
            n_or += 1
            k_or += int(mm["SNaive"]["mae_raw"] <= min(llm_vals))
    lines.append(f"D4   SNaive <= best of {len(PICKLE_LLMS)} pickle LLM variants (oracle, per dataset): {k_or}/{n_or}")
    info["darts_wins"] = dict(reported=wins_rep, augmented=wins_aug, gpt3_beats_arima=wins_arima,
                              sn_le_gpt3_within=sn_in_arima, ets_le_gpt3_within=ets_in_arima, oracle=[k_or, n_or])


# ----------------------------------------------------------------------------------------------------------------------
# compare subcommand: Monash
# ----------------------------------------------------------------------------------------------------------------------
def match_by_mae(med_arr, targets, maes):
    """One-to-one assignment pickle series -> tsf series by reproducing the stored per-series MAE; None if not unique."""
    n = len(med_arr)
    tg = np.stack(targets)  # (n, H)
    assign = np.full(n, -1)
    for i in range(n):
        cand = np.mean(np.abs(tg - med_arr[i][None, :]), axis=1)
        hit = np.flatnonzero(np.isclose(cand, maes[i], rtol=MONASH_RTOL, atol=1e-9))
        if len(hit) != 1:
            return None
        assign[i] = hit[0]
    return assign if len(set(assign.tolist())) == n else None


def monash_block(a, root: Path, out: Path, lines: list, info: dict):
    lines.append("")
    lines.append("== MONASH ==")
    if a.monash_dir is None or not a.monash_dir.exists():
        lines.append(f"skipped: --monash-dir not given or missing ({a.monash_dir})")
        return
    mcsv = pd.read_csv(root / "precomputed_outputs" / "deterministic_csvs" / "monash.csv")
    lastval = pd.read_csv(root / "data" / "last_val_mae.csv")
    ser_rows, ds_rows = [], []
    for name, (zips, m, m_alt, freq) in MONASH.items():
        drow = dict(dataset=name, m=m, m_alt=m_alt, status="", tsf="", order="", n_series=np.nan, H=np.nan,
                    g3_share=np.nan, valid=False)
        ds_rows.append(drow)
        obj, err = load_pickle(root / "precomputed_outputs" / "monash" / f"{name}.pkl")
        if not isinstance(obj, dict) or "text-davinci-003" not in obj:
            drow["status"] = err or "no text-davinci-003 entry"
            continue
        ent = obj["text-davinci-003"]
        # Added 2026-11-14: most Monash pickles store `median` as an (n_series, H) array, not as a
        # list of per-series objects. Normalise both layouts to a list of 1-D per-series medians.
        median_raw = ent["median"]
        if isinstance(median_raw, (list, tuple)):
            meds = list(median_raw)
        elif isinstance(median_raw, np.ndarray) and median_raw.ndim == 2:
            meds = [median_raw[i] for i in range(median_raw.shape[0])]
        elif isinstance(median_raw, np.ndarray) and median_raw.ndim == 1:
            meds = [median_raw]
        else:
            meds = [median_raw]
        med_arr = [as_1d(x) for x in meds]
        starts = []
        for x in meds:
            try:
                starts.append(int(x.index[0]) if isinstance(x, pd.Series) else None)
            except (TypeError, ValueError):
                starts.append(None)
        # Added 2026-11-14: a few pickles store `maes` as a ragged/2-D object (e.g. nn5_daily:
        # 19 arrays of length 6; traffic_hourly: 20 x 43), which made np.asarray raise and aborted the whole block.
        # Such datasets are skipped with a status instead of killing the run.
        try:
            maes = np.atleast_1d(np.asarray(ent["maes"], dtype=float))
        except (TypeError, ValueError) as exc:
            drow["status"] = f"stored maes is not a flat numeric vector ({type(exc).__name__}: {exc})"
            continue
        if maes.ndim != 1:
            drow["status"] = f"stored maes has shape {maes.shape}, expected one value per series"
            continue
        mae_stored = float(ent["mae"])
        n, horizon = len(med_arr), len(med_arr[0])
        drow.update(n_series=n, H=horizon)
        notes, chosen = [], None
        if len(maes) != n:
            drow["status"] = f"pickle has {n} medians but {len(maes)} stored maes"
            continue
        for z in zips:
            zp = a.monash_dir / z
            if not zp.exists():
                notes.append(f"{z}: missing")
                continue
            try:
                raw_series, meta = read_tsf_zip(zp)
            except Exception as exc:  # noqa: BLE001
                notes.append(f"{z}: {type(exc).__name__}: {exc}")
                continue
            if meta.get("frequency", freq) != freq:
                notes.append(f"{z}: @frequency {meta.get('frequency')} != expected {freq} (warning)")
            if len(raw_series) != n or any(len(s) <= horizon for s in raw_series):
                notes.append(f"{z}: {len(raw_series)} series vs {n} in pickle")
                continue
            # HF datasets stores targets as float32; try that first, then the float64 text values.
            for cast in ("float32", "float64"):
                series = [np.asarray(s, dtype=np.float32).astype(float) if cast == "float32" else np.asarray(s, dtype=float)
                          for s in raw_series]
                targets = [s[-horizon:] for s in series]
                perm = np.random.RandomState(0).permutation(np.arange(n))  # == np.random.seed(0); np.random.permutation
                ours = np.array([np.mean(np.abs(med_arr[i] - targets[perm[i]])) for i in range(n)])
                ok = np.isclose(ours, maes, rtol=MONASH_RTOL, atol=1e-9, equal_nan=True)
                order = "seed0-permutation"
                if ok.mean() < 1.0:
                    assign = match_by_mae(med_arr, targets, maes)
                    if assign is not None:
                        perm, order = assign, "matched-by-stored-MAE"
                        ours = np.array([np.mean(np.abs(med_arr[i] - targets[perm[i]])) for i in range(n)])
                        ok = np.isclose(ours, maes, rtol=MONASH_RTOL, atol=1e-9, equal_nan=True)
                mean_ok = bool(np.isclose(np.mean(ours), mae_stored, rtol=MONASH_RTOL, equal_nan=True))
                notes.append(f"{z} [{cast}]: {order}, per-series match {ok.mean():.4f}, mean match {mean_ok}")
                if ok.mean() >= 0.99 and mean_ok:
                    chosen = (z + f" [{cast}]", series, perm, order, float(ok.mean()))
                    break
            if chosen is not None:
                break
        drow["status"] = "; ".join(notes)
        if chosen is None:
            continue
        z, series, perm, order, share = chosen
        drow.update(tsf=z, order=order, g3_share=share, valid=True)
        maes_sn, maes_alt, maes_nv, short = [], [], [], 0
        for i in range(n):
            s = series[perm[i]]
            hist_full, target = s[:-horizon], s[-horizon:]
            L = starts[i]
            if L is not None and 0 < L <= len(hist_full):
                hist = hist_full[-L:]
            else:
                hist, short = hist_full, short + 1
            p_sn, _, m_eff = seasonal_naive(hist, horizon, m)
            p_nv, _, _ = seasonal_naive(hist, horizon, 1)
            r = dict(dataset=name, pickle_idx=i, tsf_idx=int(perm[i]), H=horizon, L_llm=L, len_hist_full=len(hist_full),
                     m_eff=m_eff, mae_gpt3_stored=maes[i], mae_gpt3_ours=float(np.mean(np.abs(med_arr[i] - target))),
                     mae_snaive=float(np.mean(np.abs(p_sn - target))), mae_naive=float(np.mean(np.abs(p_nv - target))))
            if m_alt is not None:
                p_alt, _, m_eff_alt = seasonal_naive(hist, horizon, m_alt)
                r.update(m_alt_eff=m_eff_alt, mae_snaive_alt=float(np.mean(np.abs(p_alt - target))))
                maes_alt.append(r["mae_snaive_alt"])
            maes_sn.append(r["mae_snaive"])
            maes_nv.append(r["mae_naive"])
            ser_rows.append(r)
        prow = mcsv[mcsv["Dataset"] == name]
        pr = prow.iloc[0] if len(prow) == 1 else None
        lv = lastval[lastval["dataset"] == name]
        drow.update(mae_gpt3=mae_stored, mae_snaive=float(np.mean(maes_sn)), mae_naive=float(np.mean(maes_nv)),
                    mae_snaive_alt=float(np.mean(maes_alt)) if maes_alt else np.nan, hist_not_truncated=short,
                    share_series_sn_le_gpt3=float(np.mean(np.array(maes_sn) <= maes)),
                    in_paper_table=pr is not None,
                    mae_llama2=float(pr["LLaMA-2"]) if pr is not None else np.nan,
                    mae_gpt3_paper_csv=float(pr["GPT-3"]) if pr is not None else np.nan,
                    best_monash_baseline=float(np.nanmin([float(pr[c]) for c in MONASH_BASELINES])) if pr is not None else np.nan,
                    last_value_authors=float(lv.iloc[0]["mae"]) if len(lv) == 1 else np.nan)
    pd.DataFrame(ser_rows).to_csv(out / "monash_per_series.csv", index=False)
    dsdf = pd.DataFrame(ds_rows)
    dsdf.to_csv(out / "monash_per_dataset.csv", index=False)

    lines.append("dataset                         n    H  valid  order                 SN       GPT-3    LLaMA-2  bestMonash  SN/GPT3")
    for _, r in dsdf.iterrows():
        if not r["valid"]:
            lines.append(f"{r['dataset']:<30} not valid: {r['status']}")
            continue
        lines.append(f"{r['dataset']:<30} {int(r['n_series']):>4} {int(r['H']):>4}  True   {r['order']:<20} "
                     f"{fmt(r['mae_snaive']):>9} {fmt(r['mae_gpt3']):>10} {fmt(r['mae_llama2']):>10} "
                     f"{fmt(r['best_monash_baseline']):>10} {fmt(r['mae_snaive'] / r['mae_gpt3']):>8}")
    v = dsdf[(dsdf["valid"]) & (dsdf.get("in_paper_table", False) == True)]  # noqa: E712
    if len(v) == 0:
        lines.append("no valid Monash dataset in the paper's table")
        return

    def cnt(col_a, col_b, sub, margin=1.0):
        ok = sub[np.isfinite(sub[col_a]) & np.isfinite(sub[col_b]) & (sub[col_b] > 0)]
        return int((ok[col_a] / ok[col_b] <= margin).sum()), len(ok), geomean((ok[col_a] / ok[col_b]).tolist())

    lines.append(f"valid Monash datasets in the paper table: {len(v)}/19")
    for ep, ca, cb in (("M1", "mae_snaive", "mae_gpt3"), ("M1s", "mae_snaive_alt", "mae_gpt3"),
                       ("M2", "mae_snaive", "mae_llama2"), ("D5", "mae_naive", "mae_gpt3")):
        sub = v if ep != "M1s" else v[np.isfinite(v["mae_snaive_alt"])]
        k, nn, g = cnt(ca, cb, sub)
        k105, _, _ = cnt(ca, cb, sub, 1.05)
        lines.append(f"{ep:<4} {ca} <= {cb}: {k}/{nn}   r<=1.05: {k105}/{nn}   geomean r = {fmt(g)}")
        info.setdefault("monash_counts", {})[ep] = dict(k=k, n=nn, k105=k105, geomean=g)
    wins = v[v["mae_gpt3"] < v["best_monash_baseline"]]
    k3, n3, _ = cnt("mae_snaive", "mae_gpt3", wins)
    lines.append(f"M3   GPT-3 beats all 12 Monash baselines on {len(wins)} {wins['dataset'].tolist()}; "
                 f"SNaive <= GPT-3 on {k3}/{n3} of these")
    # D6: mean rank of GPT-3 among the 12 Monash baselines (+GPT-3), with and without SNaive added
    ranks_wo, ranks_w = [], []
    for _, r in v.iterrows():
        pr = mcsv[mcsv["Dataset"] == r["dataset"]].iloc[0]
        base = [float(pr[c]) for c in MONASH_BASELINES if np.isfinite(float(pr[c]))]
        ranks_wo.append(1 + sum(b < r["mae_gpt3"] for b in base))
        ranks_w.append(1 + sum(b < r["mae_gpt3"] for b in base + [r["mae_snaive"]]))
    lines.append(f"D6   mean rank of GPT-3 among 12 Monash baselines: {np.mean(ranks_wo):.2f}/13; with SNaive added: "
                 f"{np.mean(ranks_w):.2f}/14")
    lv = v[np.isfinite(v["last_value_authors"])]
    rels = [rel_err(x, y) for x, y in zip(lv["mae_naive"], lv["last_value_authors"])]
    lines.append(f"G5   (diagnostic) our naive vs authors' 'Last Value' MAE: median rel diff {fmt(float(np.nanmedian(rels)))} "
                 f"over {len(rels)} datasets (their naive may use the full history / another convention)")


# ----------------------------------------------------------------------------------------------------------------------
def cmd_compare(a) -> int:
    root, out = a.llmtime_root, a.out
    out.mkdir(parents=True, exist_ok=True)
    lines = ["LLMTime case: LLMTime public forecasts vs seasonal naive / statistical baselines (mechanical output; "
             "mechanical output)",
             f"python {sys.version.split()[0]}, numpy {np.__version__}, pandas {pd.__version__}",
             f"llmtime root: {root}", f"darts csv: {a.darts_csv_dir}", f"monash dir: {a.monash_dir}",
             f"stat csv: {a.stat_csv}", ""]
    info = {"python": sys.version, "numpy": np.__version__, "pandas": pd.__version__, "args": {k: str(v) for k, v in vars(a).items()}}
    if a.only in ("all", "darts"):
        darts_block(a, root, out, lines, info)
    if a.only in ("all", "monash"):
        monash_block(a, root, out, lines, info)
    lines.append("")
    lines.append(f"pickle loader: inert shell used for {sorted(set(SafeUnpickler.shelled))} "
                 f"({len(SafeUnpickler.shelled)} references)")
    if SafeUnpickler.refused:
        lines.append("## refused classes (not loaded; review before allowing): " + ", ".join(sorted(set(SafeUnpickler.refused))))
    (out / "summary.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    (out / "run_info.json").write_text(json.dumps(info, indent=2, default=str), encoding="utf-8")
    print("\n".join(lines))
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("stats")
    s.add_argument("--darts-csv-dir", type=Path, required=True)
    s.add_argument("--out", type=Path, required=True)
    c = sub.add_parser("compare")
    c.add_argument("--llmtime-root", type=Path, required=True)
    c.add_argument("--darts-csv-dir", type=Path, required=True)
    c.add_argument("--monash-dir", type=Path, default=None)
    c.add_argument("--stat-csv", type=Path, default=None)
    c.add_argument("--only", choices=["all", "darts", "monash"], default="all")
    c.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    return cmd_stats(a) if a.cmd == "stats" else cmd_compare(a)


if __name__ == "__main__":
    sys.exit(main())
