"""Uniform re-check, phase B: cheap no-LLM controls under each B system's own evaluation protocol.

Criteria written in advance: recheck/criteria_round1.md. Every protocol choice fixed in this file is given below
with its source (paper table, paper section, or repository file and commit).
Zero LLM calls, CPU only, no network access.
Runs in the statsforecast environment of environment/requirements.txt (statsforecast 2.1.1, statsmodels 0.15.0,
numpy 2.5.4, pandas 2.3.3, pyarrow 26.0.1). Always start it with `python -I`.

Controls (criteria_round1.md, section 3):
  R1  seasonal naive; period m fixed from the sampling frequency (MONASH_M, DARTS, CF_LONG and TMMD below).
  R2  point-wise median of statsforecast AutoETS / AutoTheta / AutoARIMA, refitted at every forecast origin on data
      before that origin only. Period m2 = 24 when m > 24, otherwise m (criteria: "when the seasonal period exceeds 24 ... always use the daily period 24").
      A model that raises or returns a non-finite forecast at an origin is dropped there (median of the remaining);
      all three failing -> R1 at that origin. Every fallback is counted and reported.
Fitting history at an origin = the target history the system's own protocol hands to its forecaster: the look-back
window (EPF 168, ETT/Wind 96, ENTSO-e 1176, Time-MMD 8/36/96); LLMTime Darts: the whole training segment;
LLMTime Monash: the last 500 points (max_history_len = 500 in llmtime experiments/run_monash.py @ f74234c).
Models are always fitted on the raw target; errors are then computed on the paper's scale (raw, or z-scored with
training-partition statistics). Missing inputs are forward-filled causally (only past values); leading gaps are dropped.

Subcommands (one file, because `python -I` does not put the script folder on sys.path):
  verify          checksums of the downloaded public input files against the published values (PINS)
  llmtime-darts   LLMTime Darts rows (also used for LSTPrompt's four Darts rows)
  monash          LLMTime Monash rows (also LSTPrompt RiverFlow = saugeenday and US Births = us_births)
  epf-cache       R1 / R2 / components / ARIMA(2,1,2) at every 00:00 origin of the EPF test region (shared by MemCast,
                  JudgeCast and CastFSR; all three use the same last-14,496-hour slices and a 168 h look-back)
  entsoe-cache    same for JudgeCast's ENTSO-e Load 1H (Austria)
  memcast         MemCast EPF: day-aligned four-stride window family fixed in advance (190 placements per market)
  judgecast       JudgeCast EPF + ENTSO-e: stride family {24, 48, 72, 96} h starting at the test start
  castfsr         CastFSR ETTh1/ETTh2/ETTm1/ETTm2, Wind, EPF (z-scored with training statistics)
  timemmd         TimEvolve / KairosAgent on Time-MMD (descriptive only: no V1 anchor exists in either paper)
  summary         per-system r, V1, threshold counts -> ur_b_summary.txt / .csv

Safeguards: R2 sentinel and per-model failure tally; ENTSO-e
gate requires no missing target; summary reports fallback counts, system-level R1, anchor-only and median r,
LLMTime Darts/Monash subsets, R1 degeneration notes and N with/without LSTPrompt; verify returns 1 on
a mismatch. Optional POST HOC flag --r2-native-period (any subcommand except verify) writes to
<out>/POSTHOC_r2_native_period/ and never touches the primary outputs.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import time
import warnings
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd

# ----------------------------------------------------------------------------------------------------------------------
# Fixed in advance (criteria_round1.md). Do not change after seeing any result.
# ----------------------------------------------------------------------------------------------------------------------
SEED = 0                      # nothing below is random; kept for completeness
TOL_V1 = 0.05                 # criteria V1: relative error <= 5 %
R2_CAP = 24                   # criteria R2 fallback: period > 24 -> 24
THRESHOLDS = (1.00, 1.05, 1.10)
MODEL_ORDER = ("ETS", "Theta", "ARIMA")
SCALE_GATE = (1.0 / 3.0, 3.0)  # dataset-level gross-scale gate on the anchor ratio (same 1/3..3 rule as G4/W2 in electricity/)

LOG_FH = None


def log(msg: str) -> None:
    line = f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {msg}"
    print(line, flush=True)
    if LOG_FH is not None:
        LOG_FH.write(line + "\n")
        LOG_FH.flush()


def open_log(out: Path, name: str) -> None:
    global LOG_FH
    out.mkdir(parents=True, exist_ok=True)
    LOG_FH = open(out / f"{name}.log", "a", encoding="utf-8")
    log(f"=== {name} start | python {sys.version.split()[0]} | numpy {np.__version__} | pandas {pd.__version__} | "
        f"argv {sys.argv[1:]}")
    try:
        import statsforecast
        import statsmodels
        log(f"statsforecast {statsforecast.__version__} | statsmodels {statsmodels.__version__}")
    except Exception as exc:  # noqa: BLE001
        log(f"WARNING: could not import statsforecast/statsmodels: {type(exc).__name__}: {exc}")


# ----------------------------------------------------------------------------------------------------------------------
# Forecasting core
# ----------------------------------------------------------------------------------------------------------------------
def causal_ffill(y) -> np.ndarray:
    """Forward fill. Value i depends only on values <= i, so any prefix of the result equals ffill(prefix)."""
    return pd.Series(np.asarray(y, dtype=float)).ffill().to_numpy()


def history(y_ff: np.ndarray, origin: int, length: int | None) -> np.ndarray:
    """Target history strictly before `origin` (row index of the first forecast target), last `length` points,
    leading missing values dropped. y_ff must already be causally forward-filled."""
    h = y_ff[:origin] if length is None else y_ff[max(0, origin - length):origin]
    return h[np.isfinite(h)]


def snaive(hist, horizon: int, m: int):
    """Seasonal naive point forecast: yhat_{T+h} = y_{T+h-m*ceil(h/m)}. Falls back to m = 1 (naive) when the history
    is shorter than m. Returns (forecast, effective m)."""
    hist = np.asarray(hist, dtype=float)
    if hist.size == 0:                       # no usable history: the error shows up as NaN, never silently
        return np.full(horizon, np.nan), 0
    m_eff = int(m) if (m > 1 and len(hist) >= m) else 1
    last = hist[-m_eff:]
    return np.array([last[h % m_eff] for h in range(horizon)], dtype=float), m_eff


R2_NATIVE_PERIOD = False      # POST HOC only (--r2-native-period): use the native period instead of the cap of 24
SENTINEL_N = 20               # R2 sentinel: if the first 20 calls of a process all end in "all three failed" -> stop
R2_TALLY = {"calls": 0, "allfail": 0, **{f"fail_{k}": 0 for k in MODEL_ORDER}}
R2_FIRST_ERR: dict = {}       # first exception message per (model, exception class), logged once


def m2_of(m_r1: int) -> int:
    """R2 season length. Primary (criteria, literal): 24 if m > 24 else m. POST HOC mode: the native period m."""
    if R2_NATIVE_PERIOD:
        return max(int(m_r1), 1)
    return R2_CAP if m_r1 > R2_CAP else max(int(m_r1), 1)


def r2_forecast(hist, horizon: int, m_r1: int) -> dict:
    """R2 = point-wise median of AutoETS / AutoTheta / AutoARIMA (statsforecast), with the fallbacks of the criteria.
    Sentinel against silent degradation (e.g. an API mismatch makes every fit raise): per-model failures are tallied,
    the first message of each (model, exception class) is logged, and if the first SENTINEL_N calls of the process all
    fell back to R1 the run stops with an error instead of silently reporting R1 as R2."""
    from statsforecast.models import AutoARIMA, AutoETS, AutoTheta

    ctors = {"ETS": AutoETS, "Theta": AutoTheta, "ARIMA": AutoARIMA}
    m2 = m2_of(m_r1)
    y = np.asarray(hist, dtype=float)
    comp, stat = {}, {}
    for name in MODEL_ORDER:
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                mdl = ctors[name](season_length=m2)
                mdl.fit(y)
                pred = np.asarray(mdl.predict(h=horizon)["mean"], dtype=float)
            if pred.shape != (horizon,) or not np.all(np.isfinite(pred)):
                raise ValueError("non-finite or mis-shaped forecast")
            comp[name], stat[name] = pred, "ok"
        except Exception as exc:  # noqa: BLE001  (a failure is a recorded outcome, not a crash)
            comp[name], stat[name] = np.full(horizon, np.nan), f"fail:{type(exc).__name__}"
            R2_TALLY[f"fail_{name}"] += 1
            key = (name, type(exc).__name__)
            if key not in R2_FIRST_ERR:
                R2_FIRST_ERR[key] = str(exc)[:300]
                log(f"R2 component failure (first of its kind): {name} {type(exc).__name__}: {str(exc)[:300]} "
                    f"[history length {len(y)}, season_length {m2}, horizon {horizon}]")
    ok = [comp[k] for k in MODEL_ORDER if stat[k] == "ok"]
    R2_TALLY["calls"] += 1
    if ok:
        point = np.median(np.vstack(ok), axis=0)
        mode = {3: "median3", 2: "median2", 1: "single"}[len(ok)]
    else:
        point, _ = snaive(y, horizon, m_r1)
        mode = "R1"
        R2_TALLY["allfail"] += 1
    if R2_TALLY["calls"] == SENTINEL_N and R2_TALLY["allfail"] == SENTINEL_N:
        raise RuntimeError(f"R2 SENTINEL: the first {SENTINEL_N} R2 fits all failed for all three models "
                           f"(first errors: {R2_FIRST_ERR}). R2 would silently equal R1 -- stopping. Report this.")
    return dict(point=point, comp=comp, stat=stat, m2=m2, mode=mode)


def log_r2_tally(tag: str) -> None:
    t = R2_TALLY
    log(f"R2 tally [{tag}]: calls={t['calls']} all-three-failed(->R1)={t['allfail']} "
        f"fail_ETS={t['fail_ETS']} fail_Theta={t['fail_Theta']} fail_ARIMA={t['fail_ARIMA']}")
    for k in MODEL_ORDER:
        if t["calls"] >= SENTINEL_N and t[f"fail_{k}"] == t["calls"]:
            log(f"WARNING: {k} failed at EVERY R2 call in this run ({t['calls']}); R2 had at most two members. "
                f"Check the first error message above.")


def arima212(hist, horizon: int):
    """CastFSR's ARIMA expert as released: statsmodels ARIMA(order=(2,1,2)), default settings, refitted per request on
    the target history (CastFSR C.3; model_server.py in repo def273e). Returns (forecast, status)."""
    from statsmodels.tsa.arima.model import ARIMA

    try:
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            res = ARIMA(np.asarray(hist, dtype=float), order=(2, 1, 2)).fit()
            fc = np.asarray(res.forecast(horizon), dtype=float)
        if fc.shape != (horizon,) or not np.all(np.isfinite(fc)):
            raise ValueError("non-finite forecast")
        conv = any("converg" in str(w.message).lower() for w in caught)
        return fc, ("ok_convwarn" if conv else "ok")
    except Exception as exc:  # noqa: BLE001
        return np.full(horizon, np.nan), f"fail:{type(exc).__name__}"


def geomean(vals) -> float:
    v = np.asarray([x for x in vals if x is not None and np.isfinite(x) and x > 0], dtype=float)
    return float(np.exp(np.mean(np.log(v)))) if v.size else float("nan")


def rel_dev(ours: float, paper: float) -> float:
    return float(ours / paper - 1.0) if (np.isfinite(ours) and np.isfinite(paper) and paper != 0) else float("nan")


def pct(x, q) -> float:
    x = np.asarray([v for v in x if np.isfinite(v)], dtype=float)
    return float(np.percentile(x, q)) if x.size else float("nan")


def r2_mode_counts(modes, stats_by_model) -> dict:
    out = {f"fail_{k}": int(sum(1 for s in stats_by_model[k] if s != "ok")) for k in MODEL_ORDER}
    modes = list(modes)
    out.update(n_origins=len(modes), n_median2=modes.count("median2"), n_single=modes.count("single"),
               n_allfail_R1=modes.count("R1"))
    return out


FB_COLS = ("n_origins", "fail_ETS", "fail_Theta", "fail_ARIMA", "n_median2", "n_single", "n_allfail_R1",
           "n_r1_degenerate")


def fb_text(row) -> str:
    """One-line fallback summary for a dataset row (R2 per-model failures, R2 fallbacks, R1 period degenerations)."""
    def g(c):
        v = row.get(c, np.nan) if isinstance(row, dict) else (row[c] if c in row else np.nan)
        return "na" if v is None or (isinstance(v, float) and not np.isfinite(v)) else int(v)
    return (f"origins={g('n_origins')} fail E/T/A={g('fail_ETS')}/{g('fail_Theta')}/{g('fail_ARIMA')} "
            f"median2={g('n_median2')} single={g('n_single')} allfail->R1={g('n_allfail_R1')} "
            f"R1-period->naive={g('n_r1_degenerate')}")


# ----------------------------------------------------------------------------------------------------------------------
# Checksums of the downloaded public inputs (source commit or record given per group)
# ----------------------------------------------------------------------------------------------------------------------
PINS = {
    # zhouhaoyi/ETDataset @ 1d16c8f4f943005d613b5bc962e9eeb06058cf07, ETT-small/<file>: git blob sha1 and size
    "ett": {"ETTh1.csv": ("git", "a52c4925778c07c1ef1a2cf6fd01594919717d9e", 2589657),
            "ETTh2.csv": ("git", "6e3760778598fdee5208213d3fce122637307eec", 2417960),
            "ETTm1.csv": ("git", "62c9f979e2dc5b05d9cc5b38891e60e6baf77417", 10360719),
            "ETTm2.csv": ("git", "f9d46027c987d442d2d8f81308d1d8c4d1d35db8", 9677236)},
    # AdityaLab/Time-MMD @ 00281e2d86058286d5548b15a7670e8eda57ef62, numerical/<D>/<D>.csv
    "timemmd": {"Agriculture.csv": ("git", "3a6160f747e3c9d71d372100ba559f9ec6199efe", 38244),
                "Climate.csv": ("git", "ea59211c83a0376418e3821a5a1b3624f1d91e16", 133695),
                "Economy.csv": ("git", "109f23ec31742c591aae752be165bb13c96d553c", 31813),
                "Energy.csv": ("git", "aa0f63fa086e6f587d83f175174d8b227cb2710a", 140287),
                "Environment.csv": ("git", "f0d37ac951aa5162e33c49b94290bfacc30e0f2c", 1811606),
                "Security.csv": ("git", "ee8d6db7e9cdbb1a682c96593f4833df750f8d1c", 13349),
                "SocialGood.csv": ("git", "68fb31c64f193dd441f505d22d7039f860e000d0", 34206),
                "Traffic.csv": ("git", "d9b5c1a4c99c8e9b4443fea27dc719d249defa9a", 33209)},
    # huggingface.co/datasets/autogluon/fev_datasets @ d3e7e720f4158eab03ebcb021f1cce779cd92acc, entsoe/1H/
    "entsoe": {"train-00000-of-00001.parquet": ("sha256",
                                                "8536abd6617d51219051ffcdfe68d1efe3807e3b7799f56bdb294b2d9b1f0224",
                                                6036971)},
    # Zenodo record API checksums (Monash archive), fetched 2026-11-16
    "monash": {"weather_dataset.zip": ("md5", "57155594af0883ccd5e63a5948976796", 38820451),
               "covid_deaths_dataset.zip": ("md5", "65c233f20dba0b1e63d1fac2448b7c08", 27335),
               "solar_weekly_dataset.zip": ("md5", "5259d84348fe87cb2322c90b02ec7845", 24375),
               "tourism_monthly_dataset.zip": ("md5", "7b9a152b2736aff87bb5155f6a650693", 199791),
               "tourism_quarterly_dataset.zip": ("md5", "fc5fa2e1e08103c4b586d5a3bd5097fb", 93833),
               "tourism_yearly_dataset.zip": ("md5", "a0b9b63d7f855e76ac406ffbe9237267", 36749),
               "australian_electricity_demand_dataset.zip": ("md5", "c9ec3ee8e81cd78d9edd2a29a7a2640b", 5770526),
               "pedestrian_counts_dataset.zip": ("md5", "420043b57ed8577564d299742e8acf97", 4587054),
               "traffic_weekly_dataset.zip": ("md5", "0c23d1d99d49c6f0c96f8be1e9393948", 245126),
               "hospital_dataset.zip": ("md5", "00ba7422b837555c0715f4245fe608f7", 78110),
               "fred_md_dataset.zip": ("md5", "339cc7c28d9e6358bd6ed4115f1b166d", 169107),
               "us_births_dataset.zip": ("md5", "6680000cb82f7db6ced6b480bde89410", 16332),
               "nn5_weekly_dataset.zip": ("md5", "9e77d1b11763a4a487c5aa0f75890450", 62043),
               "saugeenday_dataset.zip": ("md5", "25365107befc47a70fae017043993fd5", 28721),
               "cif_2016_dataset.zip": ("md5", "1e3ff512e4d08849ce71138a6dda9c19", 53344),
               "bitcoin_dataset_without_missing_values.zip": ("md5", "0cf444f1ec0b230352bb1d90dde0eb1a", 220635),
               "sunspot_dataset_without_missing_values.zip": ("md5", "00ce29842aefe5f6adb8fead301609f5", 68476)},
}


def file_digest(path: Path, kind: str) -> str:
    data = path.read_bytes()
    if kind == "git":
        return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()
    return hashlib.new(kind, data).hexdigest()


def cmd_verify(a) -> int:
    open_log(a.out, "verify")
    rows = []

    def check(group, folder: Path | None, names=None):
        for fname, (kind, want, size) in PINS[group].items():
            if names is not None and fname not in names:
                continue
            p = None if folder is None else folder / fname
            if p is None or not p.exists():
                rows.append(dict(group=group, file=fname, status="MISSING", kind=kind, want=want, got=""))
                continue
            got = file_digest(p, kind)
            ok = (got.lower() == want.lower()) and p.stat().st_size == size
            rows.append(dict(group=group, file=fname, status="OK" if ok else "MISMATCH", kind=kind, want=want, got=got,
                             size=p.stat().st_size, size_want=size))

    check("ett", a.ett_dir)
    check("timemmd", a.timemmd_dir)
    check("entsoe", a.entsoe_file.parent if a.entsoe_file else None)
    check("monash", a.monash_dir)
    if a.darts_csv_dir:
        for name, spec in DARTS.items():
            p = a.darts_csv_dir / spec["file"]
            got = file_digest(p, "md5") if p.exists() else ""
            rows.append(dict(group="darts", file=spec["file"], kind="md5", want=spec["md5"], got=got,
                             status="OK" if got == spec["md5"] else ("MISSING" if not got else "MISMATCH")))
    if a.epf_raw_dir:
        for mkt in EPF_MARKETS:
            p = a.epf_raw_dir / mkt / f"{mkt}.csv"
            man = a.epf_raw_dir / mkt / "SOURCE_MANIFEST.json"
            got = file_digest(p, "sha256") if p.exists() else ""
            want = ""
            if man.exists():
                try:
                    want = json.loads(man.read_text(encoding="utf-8"))["integrity"]["sha256"]
                except Exception:  # noqa: BLE001
                    want = ""
            status = "MISSING" if not got else ("OK" if want and got.lower() == want.lower() else
                                                ("no-pin" if not want else "MISMATCH"))
            rows.append(dict(group="epf", file=f"{mkt}.csv", kind="sha256", want=want, got=got, status=status))
    if a.wind_csv:
        got = file_digest(a.wind_csv, "sha256") if a.wind_csv.exists() else ""
        rows.append(dict(group="wind", file=a.wind_csv.name, kind="sha256", want="", got=got,
                         status="no-pin" if got else "MISSING"))
    df = pd.DataFrame(rows)
    df.to_csv(a.out / "verify.csv", index=False)
    for r in rows:
        log(f"{r['group']:<8} {r['file']:<45} {r['status']:<9} {r['kind']} {r['got']}")
    bad = df[df["status"].isin(["MISMATCH"])]
    log(f"verify: {len(df)} files, {int((df['status'] == 'OK').sum())} OK, {len(bad)} MISMATCH, "
        f"{int((df['status'] == 'MISSING').sum())} MISSING")
    return 1 if len(bad) else 0


# ----------------------------------------------------------------------------------------------------------------------
# LLMTime / LSTPrompt: Darts (copied unchanged from llmtime_case/llmtime_controls.py)
# ----------------------------------------------------------------------------------------------------------------------
TESTFRAC = 0.2
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
DARTS_ORDER = list(DARTS)
R12_STAT_NAMES = {"ETS": "AutoETS", "Theta": "AutoTheta", "ARIMA": "AutoARIMA"}


def load_darts_series(csv_dir: Path, name: str):
    spec = DARTS[name]
    path = csv_dir / spec["file"]
    md5 = hashlib.md5(path.read_bytes()).hexdigest()
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
    col = vals.columns[spec["col"]]
    series = pd.Series(vals[col].to_numpy(dtype=float), index=idx).iloc[::spec["step"]]
    split = int(len(series) * (1 - TESTFRAC))
    return series.iloc[:split], series.iloc[split:], md5, note


def cmd_llmtime_darts(a) -> int:
    open_log(a.out, "llmtime_darts")
    agg = pd.read_csv(a.llmtime_root / "precomputed_outputs" / "deterministic_csvs" / "darts_results_agg.csv")
    r12 = pd.read_csv(a.r12_stat_csv) if (a.r12_stat_csv and a.r12_stat_csv.exists()) else None
    rows, pts = [], []
    for name in DARTS_ORDER:
        spec = DARTS[name]
        tr, te, md5, note = load_darts_series(a.darts_csv_dir, name)
        y_tr, y_te = tr.to_numpy(dtype=float), te.to_numpy(dtype=float)
        horizon = len(y_te)
        hist = history(causal_ffill(y_tr), len(y_tr), None)          # whole training segment, as LLMTime
        p1, m_eff = snaive(hist, horizon, spec["m"])
        res = r2_forecast(hist, horizon, spec["m"])

        def mae(p):
            return float(np.mean(np.abs(np.asarray(p) - y_te)))

        sub = agg[(agg["Dataset"] == spec["agg"]) & (agg["Type"] == "GPT-3")]
        scale = float(np.mean(np.abs(y_te)))                           # agg MAE = raw MAE / mean|y_test| (as in llmtime_case)
        mae_rep = float(sub["MAE"].iloc[0]) * scale if len(sub) else float("nan")
        row = dict(system="LLMTime", block="darts", dataset=name, H=horizon, n_hist=len(hist), m_r1=spec["m"],
                   m_r1_eff=m_eff, m_r2=res["m2"], md5_ok=(md5 == spec["md5"]), note=note,
                   mae_r1=mae(p1), mae_r2=mae(res["point"]), r2_mode=res["mode"],
                   mae_reported=mae_rep, reported_source="darts_results_agg.csv GPT-3 MAE x mean|y_test|",
                   n_agg_rows=len(sub))
        for k in MODEL_ORDER:
            row[f"mae_{k}"] = mae(res["comp"][k]) if res["stat"][k] == "ok" else float("nan")
            row[f"stat_{k}"] = res["stat"][k]
        row.update(r2_mode_counts([res["mode"]], {k: [res["stat"][k]] for k in MODEL_ORDER}))
        row["n_r1_degenerate"] = int(m_eff != spec["m"])
        row["r_r1"] = row["mae_r1"] / mae_rep
        row["r_r2"] = row["mae_r2"] / mae_rep
        if r12 is not None:   # sensitivity / cross-check against the llmtime_case fits (its periods; Sunspots m = 33)
            comps12, maxdiff = [], 0.0
            for k in MODEL_ORDER:
                s12 = r12[(r12["dataset"] == name) & (r12["method"] == R12_STAT_NAMES[k])].sort_values("h")
                if len(s12) == horizon and (s12["status"] == "ok").all():
                    v12 = s12["mean"].to_numpy(dtype=float)
                    comps12.append(v12)
                    if res["stat"][k] == "ok":
                        maxdiff = max(maxdiff, float(np.max(np.abs(v12 - res["comp"][k]))))
            if comps12:
                row["mae_r2_r12file"] = mae(np.median(np.vstack(comps12), axis=0))
            row["maxabsdiff_components_vs_r12"] = maxdiff if res["m2"] == spec["m"] else float("nan")
        rows.append(row)
        for h in range(horizon):
            pts.append(dict(dataset=name, h=h + 1, y=y_te[h], r1=p1[h], r2=res["point"][h],
                            **{k: res["comp"][k][h] for k in MODEL_ORDER}))
        log(f"{name:<22} H={horizon:<4} m={spec['m']}/{res['m2']} MAE R1={row['mae_r1']:.4f} R2={row['mae_r2']:.4f} "
            f"GPT-3(rep)={mae_rep:.4f} r_R2={row['r_r2']:.4f} mode={res['mode']} stat={res['stat']}")
    pd.DataFrame(rows).to_csv(a.out / "llmtime_darts.csv", index=False)
    pd.DataFrame(pts).to_csv(a.out / "llmtime_darts_points.csv", index=False)
    bad = [r["dataset"] for r in rows if any(r[f"stat_{k}"] != "ok" for k in MODEL_ORDER)]
    log(f"SMOKE CHECK darts: datasets with any R2 component not ok: {bad if bad else 'none'} "
        f"(expected: none, except possibly SunspotsDataset)")
    log_r2_tally("llmtime-darts")
    log("wrote llmtime_darts.csv, llmtime_darts_points.csv")
    return 0


# ----------------------------------------------------------------------------------------------------------------------
# LLMTime / LSTPrompt: Monash
# ----------------------------------------------------------------------------------------------------------------------
MONASH_M = {"weather": 7, "covid_deaths": 7, "solar_weekly": 52, "tourism_monthly": 12, "tourism_quarterly": 4,
            "tourism_yearly": 1, "australian_electricity_demand": 48, "pedestrian_counts": 24, "traffic_hourly": 24,
            "traffic_weekly": 52, "hospital": 12, "fred_md": 12, "us_births": 7, "nn5_weekly": 52, "nn5_daily": 7,
            "saugeenday": 7, "cif_2016": 12, "bitcoin": 7, "sunspot": 7, "solar_10_minutes": 144}
MONASH_MAX_HIST = 500   # llmtime experiments/run_monash.py: max_history_len = 500; train = [x[-max_history_len:] ...]


def read_tsf_zip(path: Path):
    """Minimal reader for the Monash .tsf format; reads the single .tsf member of the zip in memory (no extraction)."""
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


def cmd_monash(a) -> int:
    open_log(a.out, "monash")
    r12 = pd.read_csv(a.r12_monash_csv)
    mcsv = pd.read_csv(a.llmtime_root / "precomputed_outputs" / "deterministic_csvs" / "monash.csv")
    only = set(a.datasets.split(",")) if a.datasets else None
    for _, d in r12.iterrows():
        name = str(d["dataset"])
        if only is not None and name not in only:
            continue
        valid = str(d["valid"]).strip().lower() == "true"
        prow = mcsv[mcsv["Dataset"] == name]
        if not valid or len(prow) != 1:
            log(f"{name}: skipped (llmtime_case valid={valid}, rows in monash.csv={len(prow)})")
            continue
        mt = re.match(r"^(.+?) \[(float32|float64)\]$", str(d["tsf"]).strip())
        if mt is None:
            log(f"{name}: cannot parse llmtime_case tsf field {d['tsf']!r}; skipped")
            continue
        zname, cast = mt.group(1), mt.group(2)
        series, meta = read_tsf_zip(a.monash_dir / zname)
        n_exp, horizon, m = int(float(d["n_series"])), int(float(d["H"])), MONASH_M[name]
        limit = len(series) if not a.smoke else min(a.smoke, len(series))
        per, t0 = [], time.time()
        for i in range(limit):
            s = np.asarray(series[i], dtype=np.float32).astype(float) if cast == "float32" else np.asarray(series[i])
            target = s[-horizon:]
            hist = history(causal_ffill(s[:-horizon]), len(s) - horizon, MONASH_MAX_HIST)
            p1, m_eff = snaive(hist, horizon, m)
            pn, _ = snaive(hist, horizon, 1)
            res = r2_forecast(hist, horizon, m)
            row = dict(dataset=name, series=i, n_hist=len(hist), m_r1_eff=m_eff, m_r2=res["m2"],
                       mae_r1=float(np.mean(np.abs(p1 - target))), mae_naive=float(np.mean(np.abs(pn - target))),
                       mae_r2=float(np.mean(np.abs(res["point"] - target))), r2_mode=res["mode"])
            for k in MODEL_ORDER:
                row[f"mae_{k}"] = float(np.mean(np.abs(res["comp"][k] - target))) if res["stat"][k] == "ok" else np.nan
                row[f"stat_{k}"] = res["stat"][k]
            per.append(row)
            if (i + 1) % 250 == 0:
                log(f"{name}: {i + 1}/{limit} series, {time.time() - t0:.0f} s")
        df = pd.DataFrame(per)
        df.to_csv(a.out / f"monash_series_{name}.csv", index=False)
        lv = float(prow["Last Value"].iloc[0])
        rep = float(prow["GPT-3"].iloc[0])
        ds = dict(system="LLMTime", block="monash", dataset=name, tsf=f"{zname} [{cast}]", n_series=limit,
                  n_expected=n_exp, gate_n=(len(series) == n_exp), smoke=bool(a.smoke), H=horizon, m_r1=m,
                  m_r2=m2_of(m), mae_r1=float(df["mae_r1"].mean()),
                  mae_naive=float(df["mae_naive"].mean()), mae_r2=float(df["mae_r2"].mean()),
                  n_nan_series=int(df["mae_r2"].isna().sum()), mae_reported=rep,
                  reported_source="monash.csv GPT-3", last_value_paper=lv,
                  seconds=round(time.time() - t0, 1))
        for k in MODEL_ORDER:
            ds[f"mae_{k}_okseries"] = float(df[f"mae_{k}"].mean())
        ds.update(r2_mode_counts(df["r2_mode"], {k: df[f"stat_{k}"] for k in MODEL_ORDER}))
        ds["n_r1_degenerate"] = int((df["m_r1_eff"] != m).sum())   # series where history < m: R1 is plain naive
        ds["r1_note"] = (f"R1 = naive on {ds['n_r1_degenerate']}/{limit} series (history shorter than m={m})"
                         if ds["n_r1_degenerate"] else "")
        ds["v1_rel"] = rel_dev(ds["mae_naive"], lv)
        ds["v1_pass"] = bool(abs(ds["v1_rel"]) <= TOL_V1)
        ds["r_r1"] = ds["mae_r1"] / rep
        ds["r_r2"] = ds["mae_r2"] / rep
        pd.DataFrame([ds]).to_csv(a.out / f"monash_dataset_{name}.csv", index=False)
        log(f"{name:<30} n={limit}/{n_exp} H={horizon} m={m} naive={ds['mae_naive']:.6g} LastValue={lv:.6g} "
            f"(V1 rel {ds['v1_rel']:+.4f}) R1={ds['mae_r1']:.6g} R2={ds['mae_r2']:.6g} GPT-3={rep:.6g} "
            f"r_R2={ds['r_r2']:.4f} fallbacks median2={ds['n_median2']} single={ds['n_single']} "
            f"R1={ds['n_allfail_R1']} | {fb_text(ds)} ({ds['seconds']} s)")
        if ds["r1_note"]:
            log(f"{name}: NOTE {ds['r1_note']}")
    log_r2_tally("monash")
    return 0


# ----------------------------------------------------------------------------------------------------------------------
# EPF (MemCast, JudgeCast, CastFSR): shared cache
# ----------------------------------------------------------------------------------------------------------------------
EPF_MARKETS = ("BE", "DE", "FR", "NP", "PJM")
N_SLICE = 14496               # every system keeps the last 14,496 hourly rows (CastFSR A.2; JudgeCast Table 6; MemCast Table 7)
CF_TRAIN = 10224              # CastFSR training rows -> z-score statistics
CF_TEST0 = 11640              # CastFSR first test origin (00:00 of its first test day)
DAY0 = 11616                  # = N_SLICE - 2880: JudgeCast test start; first 00:00 inside MemCast's family segment
N_DAYS = 120                  # 00:00 origins DAY0 + 24k, k = 0..119 (last target row 14495)
EPF_L, EPF_H, EPF_M = 168, 24, 24
EPF_EXPECTED = {  # slice row 0, row 10224, row 11640, last row (CastFSR A.2 dates) and row 11616 (one day before 11640)
    "BE": ("2015-05-08 00:00:00", "2016-07-07 00:00:00", "2016-09-04 00:00:00", "2016-12-31 23:00:00", "2016-09-03 00:00:00"),
    "FR": ("2015-05-08 00:00:00", "2016-07-07 00:00:00", "2016-09-04 00:00:00", "2016-12-31 23:00:00", "2016-09-03 00:00:00"),
    "DE": ("2016-05-07 00:00:00", "2017-07-07 00:00:00", "2017-09-04 00:00:00", "2017-12-31 23:00:00", "2017-09-03 00:00:00"),
    "NP": ("2017-04-30 00:00:00", "2018-06-30 00:00:00", "2018-08-28 00:00:00", "2018-12-24 23:00:00", "2018-08-27 00:00:00"),
    "PJM": ("2017-04-30 00:00:00", "2018-06-30 00:00:00", "2018-08-28 00:00:00", "2018-12-24 23:00:00", "2018-08-27 00:00:00"),
}


def load_epf(raw_dir: Path, mkt: str):
    frame = pd.read_csv(raw_dir / mkt / f"{mkt}.csv")
    frame = frame.iloc[-N_SLICE:].reset_index(drop=True)
    stamps = frame.iloc[:, 0].astype(str).str.strip().tolist()
    price = frame.iloc[:, 1].to_numpy(dtype=float)
    return stamps, price


def cmd_epf_cache(a) -> int:
    open_log(a.out, "epf_cache")
    rows, meta = [], {}
    markets = a.markets.split(",") if a.markets else list(EPF_MARKETS)
    n_days = N_DAYS if not a.smoke else min(a.smoke, N_DAYS)
    for mkt in markets:
        stamps, price = load_epf(a.raw_dir, mkt)
        exp = EPF_EXPECTED[mkt]
        got = (stamps[0], stamps[CF_TRAIN], stamps[CF_TEST0], stamps[-1], stamps[DAY0])
        gate = (got == exp) and len(stamps) == N_SLICE and bool(np.all(np.isfinite(price)))
        meta[mkt] = dict(gate_split=gate, got=got, expected=exp, n=len(stamps),
                         sd_train_ddof0=float(np.std(price[:CF_TRAIN])), mean_train=float(np.mean(price[:CF_TRAIN])),
                         n_nonfinite=int((~np.isfinite(price)).sum()))
        log(f"{mkt}: gate_split={gate} got={got} sd_train={meta[mkt]['sd_train_ddof0']:.4f}")
        y_ff = causal_ffill(price)
        t0 = time.time()
        for k in range(n_days):
            o = DAY0 + 24 * k
            hist = history(y_ff, o, EPF_L)
            truth = price[o:o + EPF_H]
            p1, _ = snaive(hist, EPF_H, EPF_M)
            res = r2_forecast(hist, EPF_H, EPF_M)
            a212, st212 = arima212(hist, EPF_H)
            for h in range(EPF_H):
                rows.append(dict(market=mkt, k=k, origin_row=o, origin_ts=stamps[o], h=h, ts=stamps[o + h],
                                 y=truth[h], r1=p1[h], r2=res["point"][h], ets=res["comp"]["ETS"][h],
                                 theta=res["comp"]["Theta"][h], arima=res["comp"]["ARIMA"][h], r2_mode=res["mode"],
                                 st_ets=res["stat"]["ETS"], st_theta=res["stat"]["Theta"],
                                 st_arima=res["stat"]["ARIMA"], arima212=a212[h], st_arima212=st212,
                                 hist_len=len(hist)))
            if (k + 1) % 20 == 0:
                log(f"{mkt}: {k + 1}/{n_days} origins, {time.time() - t0:.0f} s")
    pd.DataFrame(rows).to_csv(a.out / "epf_cache.csv", index=False)
    (a.out / "epf_meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    log_r2_tally("epf-cache")
    log("wrote epf_cache.csv, epf_meta.json")
    return 0


def daily_sq_errors(cache: pd.DataFrame, horizon: int) -> dict:
    """Per origin k: sum over the horizon of squared errors, per method. Returns {method: array over k}."""
    out = {}
    cache = cache.sort_values(["k", "h"])
    ks = np.sort(cache["k"].unique())
    for meth in ("r1", "r2", "ets", "theta", "arima", "arima212"):
        if meth not in cache.columns:
            continue
        se = ((cache[meth] - cache["y"]) ** 2).to_numpy().reshape(len(ks), horizon)
        out[meth] = se.sum(axis=1)   # NaN if the model failed anywhere in that origin
    out["_k"] = ks
    return out


def origin_fallbacks(cache: pd.DataFrame, m: int = 24) -> dict:
    first = cache[cache["h"] == 0]
    out = r2_mode_counts(first["r2_mode"], {"ETS": first["st_ets"], "Theta": first["st_theta"],
                                            "ARIMA": first["st_arima"]})
    # R1 degenerates to naive only if the history is shorter than m (168 / 1176 >= 24, so expected 0)
    out["n_r1_degenerate"] = int((first["hist_len"] < m).sum()) if "hist_len" in first.columns else 0
    return out


# ----------------------------------------------------------------------------------------------------------------------
# MemCast
# ----------------------------------------------------------------------------------------------------------------------
MEMCAST_REPORTED = {"NP": 36.871, "PJM": 30.238, "BE": 756.308, "FR": 756.981, "DE": 210.445}      # Table 2 MSE
MEMCAST_ARIMA = {"NP": 78.944, "PJM": 181.141, "BE": 6813.559, "FR": 3072.651, "DE": 414.126}      # Table 2 ARIMA MSE
MEMCAST_BEST_NONLLM = {"NP": 55.857, "PJM": 63.342, "BE": 887.125, "FR": 876.179, "DE": 290.971}   # Table 2, for the scale filter
MEMCAST_STRIDE_DAYS = (1, 2, 3, 4)   # {24, 48, 72, 96} h
MEMCAST_NWIN = 30


def memcast_family(n_days: int):
    """Day-aligned subset of the four-stride family fixed in advance: 30 windows of 24 h, stride s days, first window at a
    00:00 inside the test segment, all windows inside it (electricity/memcast/epf_dayaligned.ps1)."""
    fam = []
    for sd in MEMCAST_STRIDE_DAYS:
        for j in range(0, n_days - (MEMCAST_NWIN - 1) * sd):
            fam.append((sd, j, j + sd * np.arange(MEMCAST_NWIN)))
    return fam


def cmd_memcast(a) -> int:
    open_log(a.out, "memcast")
    cache = pd.read_csv(a.out / "epf_cache.csv")
    meta = json.loads((a.out / "epf_meta.json").read_text(encoding="utf-8"))
    place_rows, mkt_rows = [], []
    for mkt in EPF_MARKETS:
        c = cache[cache["market"] == mkt]
        if c.empty:
            continue
        se = daily_sq_errors(c, EPF_H)
        n_days = len(se["_k"])
        fam = memcast_family(n_days)
        rep, ar_paper, best = MEMCAST_REPORTED[mkt], MEMCAST_ARIMA[mkt], MEMCAST_BEST_NONLLM[mkt]
        for sd, j, days in fam:
            r = dict(market=mkt, stride_h=24 * sd, start_day=int(j),
                     start_ts=c[(c["k"] == j) & (c["h"] == 0)]["origin_ts"].iloc[0])
            for meth in ("r1", "r2", "ets", "theta", "arima"):
                r[f"mse_{meth}"] = float(se[meth][days].sum() / (MEMCAST_NWIN * EPF_H))
            r["scale_ok"] = bool(SCALE_GATE[0] <= r["mse_r1"] / best <= SCALE_GATE[1])   # SN-1d vs best non-LLM
            r["r_r1"], r["r_r2"] = r["mse_r1"] / rep, r["mse_r2"] / rep
            r["arima_vs_paper"] = r["mse_arima"] / ar_paper
            place_rows.append(r)
        pm = pd.DataFrame([p for p in place_rows if p["market"] == mkt])
        if pm.empty:
            log(f"MemCast {mkt}: only {n_days} origins in the cache, no complete placement (smoke run?); skipped")
            continue
        sub = pm[pm["scale_ok"]]
        med_arima = float(np.nanmedian(pm["mse_arima"]))
        row = dict(system="MemCast", dataset=mkt, gate_split=meta[mkt]["gate_split"], n_placements=len(pm),
                   mse_reported=rep, paper_arima=ar_paper, median_mse_arima=med_arima,
                   v1_rel=rel_dev(med_arima, ar_paper), share_placements_arima_within5=float(
                       np.mean(np.abs(pm["arima_vs_paper"] - 1) <= TOL_V1)),
                   median_mse_r1=float(pm["mse_r1"].median()), median_mse_r2=float(pm["mse_r2"].median()),
                   r_r1=float(pm["r_r1"].median()), r_r1_p05=pct(pm["r_r1"], 5), r_r1_p95=pct(pm["r_r1"], 95),
                   r_r2=float(pm["r_r2"].median()), r_r2_p05=pct(pm["r_r2"], 5), r_r2_p95=pct(pm["r_r2"], 95),
                   n_scale_ok=len(sub), r_r2_scaleok=float(sub["r_r2"].median()) if len(sub) else np.nan,
                   r_r2_scaleok_p05=pct(sub["r_r2"], 5), r_r2_scaleok_p95=pct(sub["r_r2"], 95))
        row["v1_pass"] = bool(abs(row["v1_rel"]) <= TOL_V1)
        row.update(origin_fallbacks(c))
        mkt_rows.append(row)
        log(f"MemCast {mkt}: placements={len(pm)} V1 ARIMA median {med_arima:.3f} vs paper {ar_paper} "
            f"(rel {row['v1_rel']:+.3f}) | r_R2 median {row['r_r2']:.3f} [{row['r_r2_p05']:.3f}, {row['r_r2_p95']:.3f}] "
            f"| r_R1 median {row['r_r1']:.3f} | scale_ok {len(sub)} | {fb_text(row)}")
    pd.DataFrame(place_rows).to_csv(a.out / "memcast_placements.csv", index=False)
    pd.DataFrame(mkt_rows).to_csv(a.out / "memcast_markets.csv", index=False)
    log("wrote memcast_placements.csv, memcast_markets.csv")
    return 0


# ----------------------------------------------------------------------------------------------------------------------
# JudgeCast (EPF + ENTSO-e)
# ----------------------------------------------------------------------------------------------------------------------
JUDGE_REPORTED = {"NP": 19.657, "PJM": 25.946, "BE": 610.917, "FR": 677.679, "DE": 158.678, "ENTSOE": 2.393e6}
JUDGE_ARIMA = {"NP": 45.681, "PJM": 53.988, "BE": 1319.458, "FR": 1391.465, "DE": 334.941, "ENTSOE": 46.943e6}
JUDGE_STRIDE_DAYS = (1, 2, 3, 4)     # criteria V3: {24, 48, 72, 96} h
ENTSOE_FIRST, ENTSOE_LAST = "2015-01-01 00:00:00", "2019-12-26 23:00:00"   # JudgeCast Table 6
ENTSOE_N, ENTSOE_TEST, ENTSOE_H, ENTSOE_L, ENTSOE_M = 43680, 8736, 168, 1176, 24


def cmd_entsoe_cache(a) -> int:
    open_log(a.out, "entsoe_cache")
    import pyarrow.parquet as pq

    df = pq.read_table(a.parquet).to_pandas()
    ids = [str(x) for x in df["id"].tolist()]
    log(f"series ids in file: {ids}")
    pick = [i for i, x in enumerate(ids) if x.strip().upper() == "AT"]
    if not pick:
        pick = [i for i, x in enumerate(ids) if "AUSTRIA" in x.upper()]
    if not pick:
        pick = [i for i, x in enumerate(ids) if re.search(r"(^|[^A-Z])AT([^A-Z]|$)", x.upper())]
    if len(pick) != 1:
        log(f"STOP: cannot identify the Austrian series uniquely (candidates {[ids[i] for i in pick]}). "
            f"Report the id list; do not choose by hand.")
        (a.out / "entsoe_meta.json").write_text(json.dumps(dict(gate=False, ids=ids, reason="ambiguous id")),
                                                encoding="utf-8")
        return 2
    row = df.iloc[pick[0]]
    ts = pd.to_datetime(np.asarray(row["timestamp"]))
    y = np.asarray(row["target"], dtype=float)
    sel = (ts >= pd.Timestamp(ENTSOE_FIRST)) & (ts <= pd.Timestamp(ENTSOE_LAST))
    ts, y = ts[sel], y[sel]
    steps = np.diff(ts.values).astype("timedelta64[m]").astype(int)
    # n_nan == 0 is part of the gate: a missing target would make whole window-family members NaN and be dropped
    # silently by the medians downstream.
    gate = (len(y) == ENTSOE_N and len(ts) > 0 and str(ts[0]) == ENTSOE_FIRST and str(ts[-1]) == ENTSOE_LAST
            and bool(np.all(steps == 60)) and int(np.isnan(y).sum()) == 0)
    meta = dict(gate=gate, id=ids[pick[0]], n=len(y), first=str(ts[0]) if len(ts) else "", last=str(ts[-1]) if len(ts) else "",
                n_nonhourly_steps=int(np.sum(steps != 60)), n_nan=int(np.isnan(y).sum()),
                full_series_first=str(pd.to_datetime(np.asarray(row["timestamp"]))[0]),
                full_series_last=str(pd.to_datetime(np.asarray(row["timestamp"]))[-1]))
    log(f"ENTSO-e meta: {meta}")
    (a.out / "entsoe_meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    if not gate:
        log("STOP: ENTSO-e slice does not match JudgeCast Table 6 (43,680 hourly rows, 2015-01-01 .. 2019-12-26, "
            "no missing target). JudgeCast ENTSO-e is then excluded; report the meta line.")
        return 2
    test0 = ENTSOE_N - ENTSOE_TEST
    y_ff = causal_ffill(y)
    rows, t0 = [], time.time()
    n_orig = (ENTSOE_N - ENTSOE_H - test0) // 24 + 1
    if a.smoke:
        n_orig = min(n_orig, a.smoke)
    for k in range(n_orig):
        o = test0 + 24 * k
        hist = history(y_ff, o, ENTSOE_L)
        truth = y[o:o + ENTSOE_H]
        p1, _ = snaive(hist, ENTSOE_H, ENTSOE_M)
        res = r2_forecast(hist, ENTSOE_H, ENTSOE_M)
        for h in range(ENTSOE_H):
            rows.append(dict(market="ENTSOE", k=k, origin_row=o, origin_ts=str(ts[o]), h=h, y=truth[h], r1=p1[h],
                             r2=res["point"][h], ets=res["comp"]["ETS"][h], theta=res["comp"]["Theta"][h],
                             arima=res["comp"]["ARIMA"][h], r2_mode=res["mode"], st_ets=res["stat"]["ETS"],
                             st_theta=res["stat"]["Theta"], st_arima=res["stat"]["ARIMA"], hist_len=len(hist)))
        if (k + 1) % 25 == 0:
            log(f"ENTSO-e: {k + 1}/{n_orig} origins, {time.time() - t0:.0f} s")
    log_r2_tally("entsoe-cache")
    pd.DataFrame(rows).to_csv(a.out / "entsoe_cache.csv", index=False)
    log("wrote entsoe_cache.csv")
    return 0


def judge_members(n_days: int, offsets: bool):
    mem = []
    for sd in JUDGE_STRIDE_DAYS:
        for off in (range(sd) if offsets else (0,)):
            mem.append((sd, off, np.arange(off, n_days, sd)))
    return mem


def cmd_judgecast(a) -> int:
    open_log(a.out, "judgecast")
    sources = []
    epf = pd.read_csv(a.out / "epf_cache.csv")
    meta = json.loads((a.out / "epf_meta.json").read_text(encoding="utf-8"))
    for mkt in EPF_MARKETS:
        sources.append((mkt, epf[epf["market"] == mkt], EPF_H, bool(meta.get(mkt, {}).get("gate_split", False))))
    ent_path = a.out / "entsoe_cache.csv"
    if ent_path.exists():
        em = json.loads((a.out / "entsoe_meta.json").read_text(encoding="utf-8"))
        sources.append(("ENTSOE", pd.read_csv(ent_path), ENTSOE_H, bool(em.get("gate", False))))
    else:
        log("entsoe_cache.csv not found: ENTSO-e excluded")
    mem_rows, ds_rows = [], []
    for name, c, horizon, gate in sources:
        if c.empty:
            continue
        se = daily_sq_errors(c, horizon)
        n_days = len(se["_k"])
        rep, ar_paper = JUDGE_REPORTED[name], JUDGE_ARIMA[name]
        for offsets in (False, True):
            for sd, off, days in judge_members(n_days, offsets):
                r = dict(dataset=name, family="main" if not offsets else "with_offsets", stride_h=24 * sd,
                         offset_h=24 * off, n_windows=len(days))
                for meth in ("r1", "r2", "ets", "theta", "arima"):
                    r[f"mse_{meth}"] = float(se[meth][days].sum() / (len(days) * horizon))
                r["r_r1"], r["r_r2"] = r["mse_r1"] / rep, r["mse_r2"] / rep
                mem_rows.append(r)
        mm = pd.DataFrame([m for m in mem_rows if m["dataset"] == name and m["family"] == "main"])
        mo = pd.DataFrame([m for m in mem_rows if m["dataset"] == name and m["family"] == "with_offsets"])
        med_arima = float(np.nanmedian(mm["mse_arima"]))
        row = dict(system="JudgeCast", dataset=name, gate_split=gate, n_members=len(mm), n_days=n_days,
                   mse_reported=rep, paper_arima=ar_paper, median_mse_arima=med_arima,
                   v1_rel=rel_dev(med_arima, ar_paper),
                   r_r1=float(mm["r_r1"].median()), r_r1_p05=pct(mm["r_r1"], 5), r_r1_p95=pct(mm["r_r1"], 95),
                   r_r2=float(mm["r_r2"].median()), r_r2_p05=pct(mm["r_r2"], 5), r_r2_p95=pct(mm["r_r2"], 95),
                   r_r2_offsets_median=float(mo["r_r2"].median()), r_r2_offsets_p05=pct(mo["r_r2"], 5),
                   r_r2_offsets_p95=pct(mo["r_r2"], 95))
        row["v1_pass"] = bool(abs(row["v1_rel"]) <= TOL_V1)
        row.update(origin_fallbacks(c))
        ds_rows.append(row)
        log(f"JudgeCast {name}: gate={gate} V1 ARIMA median {med_arima:.4g} vs paper {ar_paper:.4g} "
            f"(rel {row['v1_rel']:+.3f}) | r_R2 median {row['r_r2']:.3f} [{row['r_r2_p05']:.3f}, {row['r_r2_p95']:.3f}]"
            f" | r_R1 {row['r_r1']:.3f} | {fb_text(row)}")
    pd.DataFrame(mem_rows).to_csv(a.out / "judgecast_members.csv", index=False)
    pd.DataFrame(ds_rows).to_csv(a.out / "judgecast_datasets.csv", index=False)
    log("wrote judgecast_members.csv, judgecast_datasets.csv")
    return 0


# ----------------------------------------------------------------------------------------------------------------------
# CastFSR
# ----------------------------------------------------------------------------------------------------------------------
CASTFSR_T1 = {  # Table 1 MSE (arXiv 2608.03031v3): pool experts (C.3), CastFSR-Zero, CastFSR-R1
    "ETTh1": dict(ARIMA=0.156, DLinear=0.122, PatchTST=0.117, iTransformer=0.091, Chronos2=0.103, Zero=0.080, R1=0.077),
    "ETTh2": dict(ARIMA=0.356, DLinear=0.252, PatchTST=0.261, iTransformer=0.264, Chronos2=0.257, Zero=0.268, R1=0.242),
    "ETTm1": dict(ARIMA=0.142, DLinear=0.079, PatchTST=0.084, iTransformer=0.083, Chronos2=0.060, Zero=0.055, R1=0.055),
    "ETTm2": dict(ARIMA=0.173, DLinear=0.138, PatchTST=0.139, iTransformer=0.139, Chronos2=0.144, Zero=0.127, R1=0.127),
    "Wind": dict(ARIMA=3.682, DLinear=2.440, PatchTST=2.522, iTransformer=2.616, Chronos2=2.291, Zero=1.596, R1=1.757),
    "BE": dict(ARIMA=1.973, DLinear=1.677, PatchTST=1.164, iTransformer=1.465, Chronos2=1.186, Zero=0.960, R1=0.927),
    "DE": dict(ARIMA=1.519, DLinear=1.005, PatchTST=0.845, iTransformer=1.112, Chronos2=0.798, Zero=0.393, R1=0.386),
    "FR": dict(ARIMA=6.369, DLinear=5.203, PatchTST=5.335, iTransformer=5.448, Chronos2=4.786, Zero=3.939, R1=4.032),
    "NP": dict(ARIMA=0.727, DLinear=0.488, PatchTST=0.385, iTransformer=0.453, Chronos2=0.301, Zero=0.221, R1=0.172),
    "PJM": dict(ARIMA=0.991, DLinear=0.269, PatchTST=0.180, iTransformer=0.357, Chronos2=0.185, Zero=0.140, R1=0.133),
}
CASTFSR_POOL = ("ARIMA", "DLinear", "PatchTST", "iTransformer", "Chronos2")
CF_LONG = {  # file, timestamp column, value column, m_R1, train fraction, first origin, windows, last scored timestamp
    "ETTh1": ("ETTh1.csv", "date", "OT", 24, 0.6, "2018-02-01 00:00:00", 36, "2018-06-24 23:00:00"),
    "ETTh2": ("ETTh2.csv", "date", "OT", 24, 0.6, "2018-02-01 00:00:00", 36, "2018-06-24 23:00:00"),
    "ETTm1": ("ETTm1.csv", "date", "OT", 96, 0.6, "2018-02-01 00:00:00", 145, "2018-06-25 23:45:00"),
    "ETTm2": ("ETTm2.csv", "date", "OT", 96, 0.6, "2018-02-01 00:00:00", 145, "2018-06-25 23:45:00"),
    "Wind": ("wind.csv", "date", "target", 96, 0.7, "2021-02-10 00:00:00", 101, "2021-05-21 23:45:00"),
}
CF_LHS = 96   # look-back = horizon = stride = 96 (CastFSR 4.1.1)


def cmd_castfsr(a) -> int:
    open_log(a.out, "castfsr")
    ds_rows, win_rows = [], []
    for name, (fname, tcol, vcol, m_r1, frac, first, n_win, last_ts) in CF_LONG.items():
        path = (a.wind_csv if name == "Wind" else a.ett_dir / fname)
        if path is None or not path.exists():
            log(f"{name}: input missing ({path}); skipped")
            continue
        df = pd.read_csv(path)
        ts = pd.to_datetime(df[tcol], format="%Y/%m/%d %H:%M" if name == "Wind" else None)
        y = pd.to_numeric(df[vcol], errors="coerce").to_numpy(dtype=float)
        n = len(y)
        n_train = int(frac * n)
        mu, sd = float(np.nanmean(y[:n_train])), float(np.nanstd(y[:n_train]))
        hits = np.flatnonzero(ts == pd.Timestamp(first))
        o0 = int(hits[0]) if len(hits) == 1 else -1
        origins = [o0 + CF_LHS * k for k in range(n_win)] if o0 >= 0 else []
        gate = (o0 >= CF_LHS and origins[-1] + CF_LHS - 1 < n
                and str(ts[origins[-1] + CF_LHS - 1]) == last_ts and o0 >= n_train)
        if a.smoke:
            origins = origins[:a.smoke]
        y_ff = causal_ffill(y)
        se = {k: [] for k in ("r1", "r2", "ETS", "Theta", "ARIMA", "arima212")}
        modes, stats = [], {k: [] for k in MODEL_ORDER}
        st212, n_deg = [], 0
        for w, o in enumerate(origins):
            hist = history(y_ff, o, CF_LHS)
            truth = y[o:o + CF_LHS]
            p1, m_eff = snaive(hist, CF_LHS, m_r1)
            n_deg += int(m_eff != m_r1)
            res = r2_forecast(hist, CF_LHS, m_r1)
            a212, s212 = arima212(hist, CF_LHS)
            for key, pred in (("r1", p1), ("r2", res["point"]), ("arima212", a212),
                              *((k, res["comp"][k]) for k in MODEL_ORDER)):
                se[key].append(float(np.mean(((pred - truth) / sd) ** 2)))
            modes.append(res["mode"])
            for k in MODEL_ORDER:
                stats[k].append(res["stat"][k])
            st212.append(s212)
            win_rows.append(dict(dataset=name, window=w, origin_ts=str(ts[o]), zmse_r1=se["r1"][-1],
                                 zmse_r2=se["r2"][-1], zmse_arima212=se["arima212"][-1], r2_mode=res["mode"],
                                 st_arima212=s212))
        ds_rows.append(_castfsr_row(name, gate, n, n_train, mu, sd, m_r1, se, modes, stats, st212,
                                    extra=dict(first_origin=str(ts[o0]) if o0 >= 0 else "", n_windows=len(origins),
                                               n_r1_degenerate=n_deg)))
    # EPF part from the shared cache: CastFSR origins are 11640 + 48 j = DAY0 + 24 (2 j + 1), j = 0..59
    cache_path = a.out / "epf_cache.csv"
    if cache_path.exists():
        cache = pd.read_csv(cache_path)
        meta = json.loads((a.out / "epf_meta.json").read_text(encoding="utf-8"))
        for mkt in EPF_MARKETS:
            c = cache[(cache["market"] == mkt) & (cache["k"] % 2 == 1)].sort_values(["k", "h"])
            if c.empty:
                continue
            sd = meta[mkt]["sd_train_ddof0"]
            ks = np.sort(c["k"].unique())
            first_ok = c["origin_row"].min() == CF_TEST0
            gate = bool(meta[mkt]["gate_split"]) and first_ok and (len(ks) == 60 or a.smoke)
            se = {}
            for key, col in (("r1", "r1"), ("r2", "r2"), ("ETS", "ets"), ("Theta", "theta"), ("ARIMA", "arima"),
                             ("arima212", "arima212")):
                z2 = (((c[col] - c["y"]) / sd) ** 2).to_numpy().reshape(len(ks), EPF_H)
                se[key] = list(z2.mean(axis=1))
            first = c[c["h"] == 0]
            stats = {"ETS": list(first["st_ets"]), "Theta": list(first["st_theta"]), "ARIMA": list(first["st_arima"])}
            ds_rows.append(_castfsr_row(mkt, gate, N_SLICE, CF_TRAIN, meta[mkt]["mean_train"], sd, EPF_M, se,
                                        list(first["r2_mode"]), stats, list(first["st_arima212"]),
                                        extra=dict(first_origin=str(first["origin_ts"].iloc[0]), n_windows=len(ks),
                                                   n_r1_degenerate=int((first["hist_len"] < EPF_M).sum()))))
    else:
        log("epf_cache.csv not found: run epf-cache first; EPF part of CastFSR skipped")
    out = pd.DataFrame(ds_rows)
    # R3 readout (criteria_round1.md section 3): the single pool expert with the lowest geometric-mean ratio to C* over the
    # 10 datasets (fixed before computing), plus the per-dataset best expert as a sensitivity.
    cstar = {d: min(v["Zero"], v["R1"]) for d, v in CASTFSR_T1.items()}
    gm = {e: geomean([CASTFSR_T1[d][e] / cstar[d] for d in CASTFSR_T1]) for e in CASTFSR_POOL}
    best_single = min(gm, key=gm.get)
    log(f"R3 readout: geometric-mean ratio to C* per pool expert {gm}; best single expert = {best_single}")
    if not out.empty:
        out["r3_expert"] = best_single
        out["r3_mse"] = out["dataset"].map(lambda d: CASTFSR_T1[d][best_single])
        out["r3_oracle_mse"] = out["dataset"].map(lambda d: min(CASTFSR_T1[d][e] for e in CASTFSR_POOL))
        out["cstar"] = out["dataset"].map(cstar)
        out["castfsr_r1_only"] = out["dataset"].map(lambda d: CASTFSR_T1[d]["R1"])
        out["r_r3"] = out["r3_mse"] / out["cstar"]
        out["r_r3_oracle"] = out["r3_oracle_mse"] / out["cstar"]
        out["r_r2"] = out["zmse_r2"] / out["cstar"]
        out["r_r1"] = out["zmse_r1"] / out["cstar"]
        out["r_r2_vs_R1only"] = out["zmse_r2"] / out["castfsr_r1_only"]
        for _, r in out.iterrows():
            log(f"CastFSR {r['dataset']:<6} gate={r['gate']} anchor ARIMA(2,1,2) zMSE {r['zmse_arima212']:.4f} vs "
                f"paper {r['paper_arima']} (q={r['anchor_ratio']:.3f}, V1 {'PASS' if r['v1_pass'] else 'fail'}, "
                f"scale gate {r['scale_gate']}) | zMSE R1 {r['zmse_r1']:.4f} R2 {r['zmse_r2']:.4f} | C* {r['cstar']} "
                f"| r_R3 {r['r_r3']:.3f} r_R2 {r['r_r2']:.3f} | {fb_text(r)}")
    out.to_csv(a.out / "castfsr_datasets.csv", index=False)
    pd.DataFrame(win_rows).to_csv(a.out / "castfsr_windows.csv", index=False)
    log_r2_tally("castfsr")
    log("wrote castfsr_datasets.csv, castfsr_windows.csv")
    return 0


def _castfsr_row(name, gate, n, n_train, mu, sd, m_r1, se, modes, stats, st212, extra) -> dict:
    t1 = CASTFSR_T1[name]
    row = dict(system="CastFSR", dataset=name, gate=bool(gate), n_rows=n, n_train=n_train, mean_train=mu,
               sd_train_ddof0=sd, m_r1=m_r1, m_r2=m2_of(m_r1), **extra)
    for key in ("r1", "r2", "arima212", "ETS", "Theta", "ARIMA"):
        vals = np.asarray(se[key], dtype=float)
        row[f"zmse_{key}"] = float(np.mean(vals)) if vals.size and np.all(np.isfinite(vals)) else (
            float(np.nanmean(vals)) if vals.size else np.nan)
        row[f"nfail_{key}"] = int(np.sum(~np.isfinite(vals)))
    row["paper_arima"] = t1["ARIMA"]
    row["anchor_ratio"] = row["zmse_arima212"] / t1["ARIMA"]
    row["v1_pass"] = bool(abs(row["anchor_ratio"] - 1) <= TOL_V1 and row["nfail_arima212"] == 0)
    row["scale_gate"] = bool(SCALE_GATE[0] <= row["anchor_ratio"] <= SCALE_GATE[1])
    row["n_arima212_convwarn"] = int(sum(1 for s in st212 if s == "ok_convwarn"))
    row.update(r2_mode_counts(modes, stats))
    return row


# ----------------------------------------------------------------------------------------------------------------------
# Time-MMD (TimEvolve, KairosAgent) -- descriptive only
# ----------------------------------------------------------------------------------------------------------------------
TMMD = {  # look-back, horizons (TimEvolve App. B Table 4), R1 period from the release cadence
    "Agriculture": (8, (6, 8, 10, 12), 12), "Climate": (8, (6, 8, 10, 12), 52), "Economy": (8, (6, 8, 10, 12), 12),
    "Energy": (36, (12, 24, 36, 48), 52), "Environment": (96, (48, 96, 192, 336), 7),
    "Security": (8, (6, 8, 10, 12), 12), "SocialGood": (8, (6, 8, 10, 12), 12), "Traffic": (8, (6, 8, 10, 12), 12),
}
TIMEVOLVE_MSE = {"Agriculture": 0.129, "Climate": 0.314, "Economy": 0.181, "Energy": 0.181, "Environment": 0.274,
                 "Security": 58.937, "SocialGood": 0.808, "Traffic": 0.087}
KAIROS_MSE = {"Agriculture": 0.194, "Climate": 0.863, "Economy": 0.186, "Energy": 0.217, "Environment": 0.378,
              "Security": 76.658, "SocialGood": 0.769, "Traffic": 0.151}


def cmd_timemmd(a) -> int:
    open_log(a.out, "timemmd")
    only = set(a.domains.split(",")) if a.domains else None
    rows = []
    for dom, (look, hs, m_r1) in TMMD.items():
        if only is not None and dom not in only:
            continue
        df = pd.read_csv(a.timemmd_dir / f"{dom}.csv")
        dates = pd.to_datetime(df["date"])
        order = np.argsort(dates.to_numpy(), kind="stable")      # chronological (Economy and Climate are reversed)
        dates = dates.iloc[order].reset_index(drop=True)
        y = pd.to_numeric(df["OT"], errors="coerce").to_numpy(dtype=float)[order]
        mono = bool(dates.is_monotonic_increasing and dates.is_unique)
        gap_days = float(np.median(np.diff(dates.to_numpy()).astype("timedelta64[h]").astype(float))) / 24.0
        log(f"{dom}: {len(y)} rows, {dates.iloc[0].date()} .. {dates.iloc[-1].date()}, median step {gap_days:.1f} days "
            f"(R1 period used: {m_r1}; check that the cadence matches)")
        n = len(y)
        n_train, n_test = int(n * 0.7), int(n * 0.2)
        trv = y[:n_train][np.isfinite(y[:n_train])]
        mu, sd = float(trv.mean()), float(trv.std())
        y_ff = causal_ffill(y)
        hmax = max(hs)
        origins = list(range(n - n_test, n - min(hs) + 1))
        if a.smoke:
            origins = origins[:a.smoke]
        full_sens = look < m_r1
        preds = {}
        modes, stats = [], {k: [] for k in MODEL_ORDER}
        t0, n_deg = time.time(), 0
        for i, t in enumerate(origins):
            hh = min(hmax, n - t)
            hist = history(y_ff, t, look)
            p1, m_eff = snaive(hist, hh, m_r1)
            n_deg += int(m_eff != m_r1)
            res = r2_forecast(hist, hh, m_r1)
            preds[t] = {"r1": p1, "r2": res["point"], **{k: res["comp"][k] for k in MODEL_ORDER}}
            modes.append(res["mode"])
            for k in MODEL_ORDER:
                stats[k].append(res["stat"][k])
            if full_sens:   # sensitivity: all history before the origin (only where look-back < R1 period)
                hf = history(y_ff, t, None)
                preds[t]["r1_full"] = snaive(hf, hh, m_r1)[0]
                preds[t]["r2_full"] = r2_forecast(hf, hh, m_r1)["point"]
            if (i + 1) % 250 == 0:
                log(f"{dom}: {i + 1}/{len(origins)} origins, {time.time() - t0:.0f} s")
        methods = ["r1", "r2", *MODEL_ORDER] + (["r1_full", "r2_full"] if full_sens else [])
        per_h = {meth: [] for meth in methods}
        per_h_mae = {meth: [] for meth in methods}
        for hzn in hs:
            for meth in methods:
                se_sum, ae_sum, cnt = 0.0, 0.0, 0
                for t in origins:
                    if t + hzn > n:
                        continue
                    truth = (y[t:t + hzn] - mu) / sd
                    pred = (preds[t][meth][:hzn] - mu) / sd
                    ok = np.isfinite(truth)
                    if not np.all(np.isfinite(pred[ok])):   # a component model failed at some origin
                        se_sum, ae_sum = np.nan, np.nan
                        break
                    se_sum += float(np.sum((pred[ok] - truth[ok]) ** 2))
                    ae_sum += float(np.sum(np.abs(pred[ok] - truth[ok])))
                    cnt += int(ok.sum())
                per_h[meth].append(se_sum / cnt if cnt else np.nan)
                per_h_mae[meth].append(ae_sum / cnt if cnt else np.nan)
        row = dict(system="TimEvolve/KairosAgent", dataset=dom, n=n, n_train=n_train, n_test=n_test,
                   chronological_unique=mono, mean_train=mu, sd_train_ddof0=sd, lookback=look, horizons=str(hs),
                   m_r1=m_r1, m_r2=m2_of(m_r1), n_r1_degenerate=n_deg,
                   n_missing_targets_test=int(np.sum(~np.isfinite(y[n - n_test:]))))
        for meth in methods:
            row[f"mse_{meth}"] = float(np.mean(per_h[meth]))
            row[f"mae_{meth}"] = float(np.mean(per_h_mae[meth]))
            row[f"mse_{meth}_per_h"] = str([round(v, 6) for v in per_h[meth]])
        row["timevolve_mse"], row["kairos_mse"] = TIMEVOLVE_MSE[dom], KAIROS_MSE[dom]
        for tag, ref in (("timevolve", TIMEVOLVE_MSE[dom]), ("kairos", KAIROS_MSE[dom])):
            row[f"r_r1_{tag}"] = row["mse_r1"] / ref
            row[f"r_r2_{tag}"] = row["mse_r2"] / ref
            if full_sens:
                row[f"r_r2full_{tag}"] = row["mse_r2_full"] / ref
        row.update(r2_mode_counts(modes, stats))
        rows.append(row)
        log(f"Time-MMD {dom:<12} n={n} origins={len(origins)} MSE R1={row['mse_r1']:.4f} R2={row['mse_r2']:.4f} "
            f"| TimEvolve {TIMEVOLVE_MSE[dom]} (r_R2 {row['r_r2_timevolve']:.3f}) Kairos {KAIROS_MSE[dom]} "
            f"(r_R2 {row['r_r2_kairos']:.3f}) | {fb_text(row)} ({time.time() - t0:.0f} s)")
        if n_deg:
            log(f"{dom}: NOTE R1 = naive at {n_deg}/{len(origins)} origins (look-back {look} < period {m_r1})")
        pd.DataFrame([row]).to_csv(a.out / f"timemmd_{dom}.csv", index=False)
    log_r2_tally("timemmd")
    return 0


# ----------------------------------------------------------------------------------------------------------------------
# Summary
# ----------------------------------------------------------------------------------------------------------------------
LSTPROMPT = {  # LSTPrompt Table 1 (arXiv 2402.16132v1), MAE on raw scale; ARIMA column = V1 anchor (Darts rows only)
    "AirPassengersDataset": dict(lst=13.02, arima=24.03), "MonthlyMilkDataset": dict(lst=7.71, arima=37.19),
    "AusBeerDataset": dict(lst=13.29, arima=17.13), "SunspotsDataset": dict(lst=46.84, arima=43.56),
    "saugeenday": dict(lst=24.17, arima=None), "us_births": dict(lst=429.2, arima=None),
}


EXPECTED_N = {"LLMTime": 25, "LSTPrompt": 6, "CastFSR": 10, "MemCast": 5, "JudgeCast": 6, "TimEvolve": 8,
              "KairosAgent": 8}


def _truthy(x) -> bool:
    return str(x).strip().lower() == "true"


def _fb_sum(rows: list) -> dict:
    """Sum the fallback / degeneration counters over the dataset rows that enter the system r."""
    tot = {c: 0 for c in FB_COLS}
    for r in rows:
        for c in FB_COLS:
            v = r.get(c, np.nan)
            if v is not None and np.isfinite(float(v)):
                tot[c] += int(v)
    return tot


def _sys_line(name, v1, v1_note, inc_rows, extra="", anchor_key="anchor_pass"):
    """inc_rows: per-dataset dicts that enter the system r (keys r, r_R1, anchor_pass, fallback counters)."""
    r_list = [d["r"] for d in inc_rows]
    r = geomean(r_list)
    r1 = geomean([d.get("r_R1", np.nan) for d in inc_rows])
    anchored = [d["r"] for d in inc_rows if _truthy(d.get(anchor_key, False))]
    cat = "n/a" if not np.isfinite(r) else ("control matched" if r <= 1.05 else "system clearly ahead")
    thr = " ".join(f"r<={t:.2f}:{'Y' if np.isfinite(r) and r <= t else 'N'}" for t in THRESHOLDS)
    n_ok = len([x for x in r_list if x is not None and np.isfinite(x) and x > 0])
    warn = ""
    if name in EXPECTED_N and n_ok < EXPECTED_N[name]:
        warn = f"WARNING: only {n_ok} of the expected {EXPECTED_N[name]} datasets enter r (see per-dataset rows)"
    fb = _fb_sum(inc_rows)
    return dict(system=name, v1_pass=v1, v1_note=v1_note, n_datasets=n_ok, r_system=r,
                r_system_median=float(np.nanmedian(r_list)) if r_list else np.nan, r_R1_system=r1,
                r_anchor_only=geomean(anchored), n_anchor_only=len(anchored),
                category=cat if v1 else f"({cat}; protocol not verified, not counted)", thresholds=thr, note=extra, warning=warn,
                **{f"sum_{c}": fb[c] for c in FB_COLS})


def _ds(system, block, r, metric, control, control_value, reported, rr, rr1, included, anchor_pass, **kw):
    d = dict(system=system, block=block, dataset=r["dataset"], metric=metric, control=control,
             control_value=control_value, reported=reported, r=rr, r_R1=rr1, included=bool(included),
             anchor_pass=bool(anchor_pass), r1_note="")
    note = r.get("r1_note", "") if hasattr(r, "get") else ""
    d["r1_note"] = note if isinstance(note, str) else ""
    for c in FB_COLS:
        d[c] = r[c] if c in r else np.nan
    d.update(kw)
    return d


def cmd_summary(a) -> int:
    open_log(a.out, "summary")
    out = a.out
    sys_rows, ds_rows = [], []
    lines = ["Uniform re-check, phase B -- mechanical summary (decision rules: criteria_round1.md)"]
    if R2_NATIVE_PERIOD:
        lines.append("*** POST HOC (--r2-native-period): R2 uses the native seasonal period, NOT the advance-fixed "
                     "cap of 24. Not part of the primary analysis. ***")
    lines.append("")

    # LLMTime ---------------------------------------------------------------------------------------------------------
    darts = pd.read_csv(out / "llmtime_darts.csv") if (out / "llmtime_darts.csv").exists() else pd.DataFrame()
    mon_files = sorted(out.glob("monash_dataset_*.csv"))
    mon = pd.concat([pd.read_csv(p) for p in mon_files], ignore_index=True) if mon_files else pd.DataFrame()
    if not mon.empty and "smoke" in mon.columns and mon["smoke"].map(_truthy).any():
        lines.append("WARNING: some Monash rows come from a --smoke run")
    inc_llm = {"darts": [], "monash": []}
    for block, df in (("darts", darts), ("monash", mon)):
        for _, r in df.iterrows():
            ok = True
            if "gate_n" in r:      # Monash: series count equals the validated count in llmtime_case
                ok = ok and _truthy(r["gate_n"])
            if "md5_ok" in r:      # Darts: CSV md5 equals darts' registry value
                ok = ok and _truthy(r["md5_ok"])
            anchor = _truthy(r["v1_pass"]) if "v1_pass" in r else False   # Darts rows carry no anchor
            d = _ds("LLMTime", block, r, "MAE", "R2", r["mae_r2"], r["mae_reported"], r["r_r2"], r["r_r1"], ok, anchor)
            ds_rows.append(d)
            if ok:
                inc_llm[block].append(d)
    n_v1 = int(mon["v1_pass"].map(_truthy).sum()) if not mon.empty else 0
    sub_txt = "; ".join(
        f"{b}: n={len(v)} geomean r={geomean([d['r'] for d in v]):.4f} median r={np.nanmedian([d['r'] for d in v]) if v else np.nan:.4f}"
        for b, v in inc_llm.items())
    sys_rows.append(_sys_line("LLMTime", n_v1 > 0,
                              f"M-type: Monash naive vs monash.csv 'Last Value', {n_v1}/{len(mon)} datasets <=5% (anchor subset = Monash datasets that pass; Darts has no anchor)",
                              inc_llm["darts"] + inc_llm["monash"], f"subsets: {sub_txt}"))

    # LSTPrompt -------------------------------------------------------------------------------------------------------
    inc_lst, v1_hits, v1_tot = [], 0, 0
    r12m = pd.read_csv(a.r12_darts_metrics) if (a.r12_darts_metrics and a.r12_darts_metrics.exists()) else None
    for dname, v in LSTPROMPT.items():
        frame = darts if dname in DARTS else mon
        if frame.empty or "dataset" not in frame.columns:
            continue
        src = frame[frame["dataset"] == dname]
        if src.empty:
            continue
        r = src.iloc[0]
        anchor = False
        if v["arima"] is not None and r12m is not None:
            s = r12m[(r12m["dataset"] == dname) & (r12m["method"] == "ARIMA(authors)")]
            if len(s) == 1:
                v1_tot += 1
                ours = float(s["mae_raw"].iloc[0])
                anchor = abs(rel_dev(ours, v["arima"])) <= TOL_V1
                v1_hits += int(anchor)
                lines.append(f"LSTPrompt V1-P {dname}: ARIMA(authors) MAE recomputed in llmtime_case from LLMTime's "
                             f"published ARIMA forecasts = {ours:.4f} vs LSTPrompt Table 1 {v['arima']} "
                             f"(rel {rel_dev(ours, v['arima']):+.5f})")
        d = _ds("LSTPrompt", "darts" if dname in DARTS else "monash", r, "MAE", "R2", float(r["mae_r2"]), v["lst"],
                float(r["mae_r2"]) / v["lst"], float(r["mae_r1"]) / v["lst"], True, anchor)
        ds_rows.append(d)
        inc_lst.append(d)
    sys_rows.append(_sys_line("LSTPrompt", v1_hits > 0,
                              f"P-type: ARIMA column recomputed from LLMTime's published ARIMA forecasts, {v1_hits}/{v1_tot} <=5% (counts below are given both with and without LSTPrompt)",
                              inc_lst, "Darts 4 + Monash 2"))

    # CastFSR ---------------------------------------------------------------------------------------------------------
    cf = pd.read_csv(out / "castfsr_datasets.csv") if (out / "castfsr_datasets.csv").exists() else pd.DataFrame()
    if not cf.empty:
        inc_cf, inc_cf_r2 = [], []
        for _, r in cf.iterrows():
            ok = _truthy(r["gate"]) and _truthy(r["scale_gate"])
            d = _ds("CastFSR", "epf" if r["dataset"] in EPF_MARKETS else "long", r, "z-MSE", f"R3({r['r3_expert']})",
                    r["r3_mse"], r["cstar"], r["r_r3"], r["r_r1"], ok, _truthy(r["v1_pass"]), r_R2=r["r_r2"],
                    r_R3_oracle=r["r_r3_oracle"], anchor_ratio=r["anchor_ratio"])
            ds_rows.append(d)
            if ok:
                inc_cf.append(d)
                inc_cf_r2.append(dict(d, r=r["r_r2"]))
        n1 = int(cf["v1_pass"].map(_truthy).sum())
        excl = [d["dataset"] for d in ds_rows if d["system"] == "CastFSR" and not d["included"]]
        sys_rows.append(_sys_line("CastFSR", n1 > 0, f"M-type: ARIMA(2,1,2) anchor {n1}/{len(cf)} datasets <=5%",
                                  inc_cf,
                                  f"main control R3; inclusion = structure gate + magnitude gate (not included: {excl if excl else 'none'}); "
                                  f"R2 system r = {geomean([d['r'] for d in inc_cf_r2]):.4f} (median "
                                  f"{np.nanmedian([d['r'] for d in inc_cf_r2]) if inc_cf_r2 else np.nan:.4f}); "
                                  f"R3 per-dataset best (sensitivity) = {geomean([d['r_R3_oracle'] for d in inc_cf]):.4f}"))

    # MemCast ---------------------------------------------------------------------------------------------------------
    mc = pd.read_csv(out / "memcast_markets.csv") if (out / "memcast_markets.csv").exists() else pd.DataFrame()
    if not mc.empty:
        inc_mc = []
        for _, r in mc.iterrows():
            ok = _truthy(r["gate_split"])
            d = _ds("MemCast", "epf", r, "MSE", "R2 (family median)", r["median_mse_r2"], r["mse_reported"], r["r_r2"],
                    r["r_r1"], ok, _truthy(r["v1_pass"]), r_p05=r["r_r2_p05"], r_p95=r["r_r2_p95"],
                    r_scaleok=r["r_r2_scaleok"])
            ds_rows.append(d)
            if ok:
                inc_mc.append(d)
        kept = [d["dataset"] for d in inc_mc]
        pl = pd.read_csv(out / "memcast_placements.csv")
        pl = pl[pl["market"].isin(kept)]
        sysfam = pl.groupby(["stride_h", "start_day"])["r_r2"].apply(
            lambda s: geomean(list(s)) if len(s) == len(kept) else np.nan)
        n1 = int(mc["v1_pass"].map(_truthy).sum())
        sys_rows.append(_sys_line("MemCast", n1 > 0,
                                  f"M-type: AutoARIMA(m=24) window-family median vs Table 2 ARIMA, {n1}/{len(mc)} <=5%", inc_mc,
                                  f"inclusion = structure gate; system-level window family (day-aligned, geometric mean over markets): median {np.nanmedian(sysfam):.4f}, "
                                  f"5%-95% [{pct(sysfam, 5):.4f}, {pct(sysfam, 95):.4f}]; after the magnitude filter (sensitivity) system r = "
                                  f"{geomean([d['r_scaleok'] for d in inc_mc]):.4f}"))

    # JudgeCast -------------------------------------------------------------------------------------------------------
    jc = pd.read_csv(out / "judgecast_datasets.csv") if (out / "judgecast_datasets.csv").exists() else pd.DataFrame()
    if not jc.empty:
        inc_jc = []
        for _, r in jc.iterrows():
            ok = _truthy(r["gate_split"])
            d = _ds("JudgeCast", "entsoe" if r["dataset"] == "ENTSOE" else "epf", r, "MSE", "R2 (family median)",
                    np.nan, r["mse_reported"], r["r_r2"], r["r_r1"], ok, _truthy(r["v1_pass"]), r_p05=r["r_r2_p05"],
                    r_p95=r["r_r2_p95"], r_offsets_median=r["r_r2_offsets_median"])
            ds_rows.append(d)
            if ok:
                inc_jc.append(d)
        kept = [d["dataset"] for d in inc_jc]
        mem = pd.read_csv(out / "judgecast_members.csv")
        mem = mem[(mem["family"] == "main") & mem["dataset"].isin(kept)]
        sysfam = mem.groupby("stride_h")["r_r2"].apply(lambda s: geomean(list(s)))
        n1 = int(jc["v1_pass"].map(_truthy).sum())
        sys_rows.append(_sys_line("JudgeCast", n1 > 0,
                                  f"M-type: AutoARIMA(m=24) stride-family median vs Table 1 ARIMA, {n1}/{len(jc)} <=5%", inc_jc,
                                  f"inclusion = structure gate (ENTSO-e also needs no missing values); system-level stride family (4 members, geometric mean over datasets): median "
                                  f"{np.nanmedian(sysfam):.4f}, 5%-95% [{pct(sysfam, 5):.4f}, {pct(sysfam, 95):.4f}]; "
                                  f"Rossmann not included (subset not public)"))

    # TimEvolve / KairosAgent (descriptive) --------------------------------------------------------------------------
    tm_files = sorted(out.glob("timemmd_*.csv"))
    tm = pd.concat([pd.read_csv(p) for p in tm_files], ignore_index=True) if tm_files else pd.DataFrame()
    if not tm.empty:
        for tag, sname in (("timevolve", "TimEvolve"), ("kairos", "KairosAgent")):
            rows_t = []
            for _, r in tm.iterrows():
                note = (f"R1 = naive at {int(r['n_r1_degenerate'])} origins (look-back < period)"
                        if "n_r1_degenerate" in r and r["n_r1_degenerate"] > 0 else "")
                d = _ds(sname, "timemmd", r, "std-MSE", "R2", r["mse_r2"], r[f"{tag}_mse"], r[f"r_r2_{tag}"],
                        r[f"r_r1_{tag}"], False, False, r_R2_fullhistory=r.get(f"r_r2full_{tag}", np.nan))
                d["r1_note"] = note
                ds_rows.append(d)
                rows_t.append(d)
            sys_rows.append(_sys_line(sname, False, "protocol not verified: the paper tables have no no-LLM baseline that this toolchain can reproduce (only trained DLinear/PatchTST and foundation models)",
                                      rows_t, "descriptive only"))
    sys_rows.append(dict(system="MUSE-Bench", v1_pass=False, v1_note="protocol not verified: processed benchmark data and windows are not public",
                         n_datasets=0, r_system=np.nan, category="(protocol not verified, not counted)", thresholds="",
                         note="see recheck/system_protocols.csv", warning=""))

    # Output --------------------------------------------------------------------------------------------------------
    sdf, ddf = pd.DataFrame(sys_rows), pd.DataFrame(ds_rows)
    sdf.to_csv(out / "ur_b_summary.csv", index=False)
    ddf.to_csv(out / "ur_b_per_dataset.csv", index=False)
    lines.append("")
    lines.append(f"{'system':<12} {'V1':<5} {'n':>3} {'r':>8} {'median':>8} {'r_R1':>8} {'r_anch':>8}  category / thresholds")

    def f4(x):
        return f"{x:.4f}" if isinstance(x, (int, float)) and np.isfinite(x) else "nan"

    for _, r in sdf.iterrows():
        lines.append(f"{r['system']:<12} {str(bool(r['v1_pass'])):<5} {int(r['n_datasets']):>3} {f4(r['r_system']):>8} "
                     f"{f4(r.get('r_system_median', np.nan)):>8} {f4(r.get('r_R1_system', np.nan)):>8} "
                     f"{f4(r.get('r_anchor_only', np.nan)):>8}  {r['category']}  {r['thresholds']}")
        lines.append(f"{'':<12} V1: {r['v1_note']}")
        if "sum_n_origins" in r and np.isfinite(r["sum_n_origins"]):
            lines.append(f"{'':<12} fallbacks (datasets in r): R2 fits={int(r['sum_n_origins'])}, failures "
                         f"ETS/Theta/ARIMA={int(r['sum_fail_ETS'])}/{int(r['sum_fail_Theta'])}/{int(r['sum_fail_ARIMA'])}, "
                         f"median-of-2={int(r['sum_n_median2'])}, single={int(r['sum_n_single'])}, "
                         f"all-three-failed->R1={int(r['sum_n_allfail_R1'])}; R1 period->naive={int(r['sum_n_r1_degenerate'])}"
                         f"; r_anch over {int(r['n_anchor_only'])} anchor-passing datasets")
        if r["note"]:
            lines.append(f"{'':<12} {r['note']}")
        if isinstance(r.get("warning", ""), str) and r.get("warning", ""):
            lines.append(f"{'':<12} {r['warning']}")
    notes = ddf[ddf["r1_note"].astype(str).str.len() > 0] if "r1_note" in ddf.columns else pd.DataFrame()
    for _, r in notes.iterrows():
        lines.append(f"R1 note [{r['system']} {r['dataset']}]: {r['r1_note']}")
    lines.append("")
    passed = sdf[sdf["v1_pass"] == True]  # noqa: E712
    for label, sub in (("including LSTPrompt (P-type anchor)", passed),
                       ("excluding LSTPrompt", passed[passed["system"] != "LSTPrompt"])):
        lines.append(f"B systems passing V1, {label}: N_B = {len(sub)} ({', '.join(sub['system'])})")
        for t in THRESHOLDS:
            k = int((sub["r_system"] <= t).sum())
            lines.append(f"    r <= {t:.2f}: {k}/{len(sub)}")
    lines.append("")
    lines.append("columns: r = geometric mean over datasets in r; median = median of the same r; r_R1 = R1 lower "
                 "reference; r_anch = only datasets whose own anchor is within 5 % (sensitivity)")
    lines.append("per-dataset rows (with block, fallback counters, R1 notes): ur_b_per_dataset.csv")
    (out / "ur_b_summary.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    for ln in lines:
        log(ln)
    return 0


# ----------------------------------------------------------------------------------------------------------------------
def main() -> int:
    global R2_NATIVE_PERIOD
    np.random.seed(SEED)
    try:  # never crash on a console code page
        sys.stdout.reconfigure(errors="replace")
    except Exception:  # noqa: BLE001
        pass
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    def add(name, fn):
        p = sub.add_parser(name)
        p.add_argument("--out", type=Path, required=True)
        p.add_argument("--smoke", type=int, default=0, help="limit origins/series per dataset (smoke test)")
        p.add_argument("--r2-native-period", action="store_true",
                       help="POST HOC sensitivity only: R2 uses the native seasonal period instead of the advance-fixed cap "
                            "of 24. All inputs and outputs then live in <out>/POSTHOC_r2_native_period/; the primary "
                            "outputs in <out> are never read or written.")
        p.set_defaults(fn=fn)
        return p

    p = add("verify", cmd_verify)
    for opt in ("--ett-dir", "--timemmd-dir", "--entsoe-file", "--monash-dir", "--darts-csv-dir", "--epf-raw-dir",
                "--wind-csv"):
        p.add_argument(opt, type=Path, default=None)
    p = add("llmtime-darts", cmd_llmtime_darts)
    p.add_argument("--darts-csv-dir", type=Path, required=True)
    p.add_argument("--llmtime-root", type=Path, required=True)
    p.add_argument("--r12-stat-csv", type=Path, default=None, help="optional cross-check: llmtime_case/out/stat_forecasts.csv")
    p = add("monash", cmd_monash)
    p.add_argument("--monash-dir", type=Path, required=True)
    p.add_argument("--llmtime-root", type=Path, required=True)
    p.add_argument("--r12-monash-csv", type=Path, required=True, help="llmtime_case/out/monash_per_dataset.csv")
    p.add_argument("--datasets", default="")
    p = add("epf-cache", cmd_epf_cache)
    p.add_argument("--raw-dir", type=Path, required=True)
    p.add_argument("--markets", default="")
    p = add("entsoe-cache", cmd_entsoe_cache)
    p.add_argument("--parquet", type=Path, required=True)
    add("memcast", cmd_memcast)
    add("judgecast", cmd_judgecast)
    p = add("castfsr", cmd_castfsr)
    p.add_argument("--ett-dir", type=Path, required=True)
    p.add_argument("--wind-csv", type=Path, required=True)
    p = add("timemmd", cmd_timemmd)
    p.add_argument("--timemmd-dir", type=Path, required=True)
    p.add_argument("--domains", default="")
    p = add("summary", cmd_summary)
    p.add_argument("--r12-darts-metrics", type=Path, default=None, help="optional: llmtime_case/out/darts_metrics.csv")
    a = ap.parse_args()
    if a.r2_native_period:
        if a.cmd == "verify":
            ap.error("--r2-native-period is meaningless for verify")
        R2_NATIVE_PERIOD = True
        a.out = a.out / "POSTHOC_r2_native_period"     # separate folder: primary outputs are untouched
        a.out.mkdir(parents=True, exist_ok=True)
        (a.out / "README_POST_HOC.txt").write_text(
            "POST HOC sensitivity (added 2026-11-16, before any phase-B result existed):\n"
            "R2 uses the native seasonal period of the series (weekly 52, half-hourly 48, 15-minute 96, Sunspots 33)\n"
            "instead of the advance-fixed rule 'period > 24 -> 24'. NOT part of the primary analysis; the decision\n"
            "rules use only the outputs in the parent folder.\n", encoding="utf-8")
    rc = a.fn(a)
    if R2_NATIVE_PERIOD:
        log("*** POST HOC run (--r2-native-period); outputs written to POSTHOC_r2_native_period ***")
    return rc


if __name__ == "__main__":
    sys.exit(main())
