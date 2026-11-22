r"""Supplementary uniform re-check, phase C (5 systems not covered by the first re-check).

Criteria written in advance: recheck/criteria_round2.md, the only source of rules for this phase. The criteria of
the first re-check are in recheck/criteria_round1.md; execution conventions are shared with recheck/round1/ur_b.py.

Citation tags used in the comments:
    [criteria §x.y]          criteria_round2.md section x.y
    [criteria_round1 §x]     criteria_round1.md section x
    [B0.1-n] execution convention n of recheck/round1/ur_b.py, adopted by [criteria §1.4]
    [UR_B]   recheck/round1/ur_b.py conventions
    "NOT IN CRITERIA" marks an implementation choice the criteria do not fix. Where such a choice could change a
    number, the script STOPS instead of choosing.

Zero LLM calls, CPU only. Only `compevo-check` uses the network (GitHub; everything downloaded is saved as untrusted
data, code saved as .txt, nothing is executed or imported). The CiK scoring code (HF compute_rcrps_with_hf_dataset.py)
was read as TEXT and re-written here from the criteria wording [criteria §5.1]; it is not imported and not copied for
execution. Always run with `python -I` in the environment of environment/requirements.txt (Python 3.14.2,
statsforecast 2.1.1, statsmodels 0.15.0, numpy 2.5.4, pandas 2.3.3, pyarrow 26.0.1) [criteria §5.9 pinned environment].

Inputs:
    --parquet          CiK ICML2025-00000-of-00001.parquet (Hugging Face); size and SHA256 are checked against
                       the values in CIK_PARQUET_PIN before use
    --json             N2F AULF_test_data_2021.json; size and SHA256 are checked against N2F_JSON_PIN
    --ext-root         root folder for the untrusted CompEvo download (compevo-check only)
    --ur-b-summary     phase-B summary (default: recheck/round1/out/ur_b_summary.csv)
    --round1-readings  phase-A readings (default: recheck/round1/read_values.md)
Outputs: --out-dir (default: recheck/round2/out). Every output file is created with mode "x": an existing file is
never overwritten (V1 counts only the first formal run [criteria §5.9 safeguard 1]). Each run writes its log to <out>/logs/.

Subcommands
    selftest       scorer unit tests on synthetic data only [criteria §5.11]; prints PASS / FAIL only
    smoke          structure gates + <= 10 CiK instances + 3 N2F windows; counts / ok / timings only, never an
                   aggregate error, anchor value or ratio [criteria §5.9 safeguard 2]; decides the single allowed anchor
                   interface fix [criteria §5.9-3] and records it for `cik`
    compevo-check  the 7 conditions of [criteria §5.7] on github.com/Aliiina-z/CompEvo (text only); any condition not met ->
                   "window or data undetermined", nothing computed
    cik            THE formal CiK / BNP run (R1, R2, Exp-Smoothing anchor, V1, descriptive items) [criteria §5.1, 5.2, 5.9]
    n2f            THE formal N2F Electricity run, 100 windows, pooled RMSE [criteria §5.6]
    nexus          R3 read-out from the Table 1 values [criteria §5.4, 6.3]
    summary        combines with the first re-check: status table, section 7 (K, a, b, verdict), section 8
                   (two calibres, three thresholds, abstract rule), 7.3 descriptive items [criteria §7, 8, 10]

Exit codes: 0 ok | 1 selftest failed | 2 structure gate / smoke check failed / CompEvo all 7 met | 3 R2 sentinel
            | 4 network failure | 5 non-finite R1/R2 (stopped before the anchor phase / before writing)
            | 11 environment | 12 refuse to overwrite | 13 first-run lock | 14 missing prerequisite

Safeguards: smoke records whether its CiK part passed and `cik` refuses otherwise; empty / gappy CiK histories stop
at the gate; R1/R2 are scored and checked for non-finite values before the lock; summary refuses a non-finite counted
r; summary works when CompEvo could not be fetched ("undetermined (network)"); CompEvo condition 6 is conservative;
smoke can be re-run, each run in <out>/smoke/<run>/.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import warnings
from collections import Counter
from fractions import Fraction
from pathlib import Path

import numpy as np
import pandas as pd

SCRIPT_VERSION = "ur_c.py v1 (2026-11-18)"

# ----------------------------------------------------------------------------------------------------------------------
# Constants (all literal values from the criteria; do not change after seeing any result)
# ----------------------------------------------------------------------------------------------------------------------
CIK_PARQUET_PIN = ("ICML2025-00000-of-00001.parquet",
                   "44827A18C708D2A948A58832419C475353F5538B163F16ED3D83E2B98B9130B0", 213493)   # [criteria §6.1]
N2F_JSON_PIN = ("AULF_test_data_2021.json",
                "C56C5660942CD4672A17CC6C64653189CA11C52D9ECE45990588BDC5413DA92B", 153249)      # [criteria §6.4]
ENV_PINNED = {"python": "3.14.2", "statsforecast": "2.1.1", "statsmodels": "0.15.0", "numpy": "2.5.4",
              "pandas": "2.3.3"}                                                                  # [criteria §5.9 pinned environment]

TOL_V1 = 0.05                       # [criteria_round1 §4] [criteria §5.9 decision] |anchor / 0.605 - 1| <= 0.05, unrounded [criteria §5.12]
SCALE_GATE = (1.0 / 3.0, 3.0)       # [B0.1-7] [criteria §1.4] magnitude gate, only where an anchor exists
THRESHOLDS = (1.00, 1.05, 1.10)     # [criteria_round1 §5, §6] [criteria §5.12]
P1, P2 = 1.221, 1.10                # [criteria §7.1] [criteria §5.12]
LST_ANCHOR_R = 1.405                # [criteria §7.3-3]
R2_CAP = 24                         # [criteria_round1 §3] [B0.1-2]
MODEL_ORDER = ("ETS", "Theta", "ARIMA")
SENTINEL_N = 20                     # [criteria §5.2] [UR_B] first 20 R2 calls all "three failed" -> stop
RCRPS_CAP = 5.0                     # [criteria §5.1-5]
N_SAMPLES = 25                      # [criteria §5.9-5] run_baselines.py default
SEED_OFFSETS = tuple(1000 * j for j in range(1, 21))   # [criteria §5.9 descriptive items] seed + 1000*j, j = 1..20
FREQ_TABLE = {"h": 24, "D": 7, "MS": 12, "10min": 144, "s": 1}   # [criteria §5.2 sensitivity] the complete table

CIK_SYSTEM = 0.159                  # [criteria §5.3] [criteria §6.1] Direct Prompt (ours), Llama-3.1-405B-Inst, with context
BNP_SYSTEM = 0.110                  # [criteria §5.3] [criteria §6.2] min cell of Median-/SampleWise-CorDP, Table 1
CIK_ANCHOR_PAPER = 0.605            # [criteria §5.9] Exp-Smoothing, Table 1 / Table 3
CIK_EXPSMOOTH_FAILURES_PAPER = 5    # [criteria §10] paper Table 6, Exp-Smoothing significant failures
N2F_SYSTEM = 280.39                 # [criteria §5.6] [criteria §6.4] Electricity RMSE, Filtered News
N2F_M = 48                          # [criteria §5.6] period 48 -> R2 uses 24
N2F_N_WINDOWS, N2F_LEN = 100, 48    # [criteria §5.6] [criteria §6.4] structure gate
COMPEVO_SYSTEM = 354.18             # [criteria §5.7] only used if the 7 conditions held (never computed by this script)

NEXUS_COLS = ("Weather MAE", "Elec MAPE", "Eq-3d MAPE", "Com-3d MAPE", "Eq-7d MAPE", "Com-7d MAPE")   # [criteria §5.4, 6.3]
NEXUS_POOL = ("Chronos-2", "TimesFM-2.5", "TiRex")       # [criteria §5.4] pool; also the tie-breaking order
NEXUS_SYSTEMS = ("Nexus (Gemini-3.1-Pro)", "Nexus (Claude-Sonnet-4.5)")
NEXUS_MAIN = {  # [criteria §6.3] Table 1, main metric, verbatim
    "TimesFM-2.5": (2.770, 6.939, 2.245, 2.755, 3.235, 3.757),
    "Chronos-2": (2.659, 6.189, 2.046, 2.628, 3.115, 3.762),
    "TiRex": (2.675, 6.697, 2.068, 2.606, 3.111, 3.695),
    "Nexus (Claude-Sonnet-4.5)": (2.052, 5.821, 2.070, 2.543, 3.069, 3.668),
    "Nexus (Gemini-3.1-Pro)": (1.970, 5.305, 1.958, 2.488, 2.994, 3.434),
}
NEXUS_RMSE = {  # [criteria §6.3] Table 1 RMSE columns, descriptive only [criteria §5.4]
    "TimesFM-2.5": (3.888, 1689.9, 11.432, 37.407, 16.332, 56.004),
    "Chronos-2": (3.753, 1524.6, 10.638, 34.428, 16.045, 54.467),
    "TiRex": (3.800, 1632.8, 10.746, 32.574, 15.901, 51.199),
    "Nexus (Claude-Sonnet-4.5)": (2.802, 1390.6, 10.678, 34.097, 16.132, 50.731),
    "Nexus (Gemini-3.1-Pro)": (2.717, 1309.9, 10.272, 31.461, 15.341, 48.610),
}

# First re-check values, read as recheck/round1/read_values.md and ur_b.py report them.
A_READINGS = {  # read_values.md table rows: "<control> / <system>" as printed there; r = the unrounded quotient
    "MoiraiAgent": ("0.6978 / 0.6887", 0.6978, 0.6887),
    "TSOrchestra": ("0.7281 / 0.6768", 0.7281, 0.6768),
    "FASE": ("0.728 / 0.679", 0.728, 0.679),
    "TimeRSI": ("0.8293 / 0.5916", 0.8293, 0.5916),
}
B_PASSING_EXPECTED = ("LLMTime", "LSTPrompt", "CastFSR", "JudgeCast")   # ur_b_summary.csv, v1_pass == True
ORIG_COUNTS_EXPECTED = {"incl": (0, 2, 4), "excl": (0, 2, 4)}            # phase A+B counts (N=8 / N=7)
SQUARED_METRIC_ORIG = {"CastFSR": "z-MSE", "JudgeCast": "MSE"}            # [criteria §5.10] sqrt(r) only for these (post hoc)
KNOWN_BEFORE_CRITERIA = {  # [criteria §2.1] [criteria §10]
    "CiK": "Direct Prompt 0.159; ARIMA 0.475, ETS 0.530, Exp-Smoothing 0.605, Chronos-Large 0.326 (full table read)",
    "Nexus": "Table 1 in full (r could already be computed from the numbers in 6.3 before the criteria were written)",
    "N2F": "Table 3 (deep-model baselines only)",
    "CompEvo": "baseline cells same as N2F",
    "BNP": "smallest cell of the proposed method 0.110; base forecasters 0.382, 0.492, 0.636",
}

# ----------------------------------------------------------------------------------------------------------------------
# Paths (defaults relative to this script inside the repository; override with --out-dir, --ur-b-summary, --round1-readings)
# ----------------------------------------------------------------------------------------------------------------------
HERE = Path(__file__).resolve().parent                      # recheck/round2
RECHECK = HERE.parent                                       # recheck
OUT = HERE / "out"
SMOKE_DIR = OUT / "smoke"
LOG_DIR = OUT / "logs"
UR_B_SUMMARY = RECHECK / "round1" / "out" / "ur_b_summary.csv"      # phase-B summary
RESULTS_A = RECHECK / "round1" / "read_values.md"                   # phase-A readings
IFACE_NAME = "cik_anchor_interface.json"      # written by every smoke run into out/smoke/<RUN_TS>/
CIK_LOCK = OUT / "cik_FIRST_RUN.lock"
INTERFACE_ERRS = ("TypeError", "AttributeError", "ImportError", "ModuleNotFoundError", "NameError")

CIK_OUTPUTS = ("cik_instances.csv", "cik_forecasts.csv", "cik_primary.json", "cik_primary.txt",
               "cik_anchor_seeds.csv", "cik_anchor_seed_rcrps.csv", "cik_anchor_samples_offset0.npz",
               "cik_sens_freq.csv", "cik_descriptive.json")
N2F_OUTPUTS = ("n2f_windows.csv", "n2f_forecasts.csv", "n2f_summary.json", "n2f_summary.txt")
NEXUS_OUTPUTS = ("nexus_r3.json", "nexus_r3.txt", "nexus_r3.csv")
COMPEVO_OUTPUTS = ("compevo_check.json", "compevo_check.txt", "compevo_tree.csv", "compevo_evidence.txt")
SUMMARY_OUTPUTS = ("ur_c_summary.txt", "ur_c_summary.json", "ur_c_status.csv")
SMOKE_OUTPUTS = ("smoke_cik.json", "smoke_n2f.json", "smoke_inputs.json", "cik_anchor_interface.json")


# ----------------------------------------------------------------------------------------------------------------------
# Logging, hashing, write-once outputs
# ----------------------------------------------------------------------------------------------------------------------
class Stop(Exception):
    def __init__(self, code: int, msg: str):
        super().__init__(msg)
        self.code, self.msg = code, msg


LOG_FH = None
LOG_PATH: Path | None = None
RUN_TS = time.strftime("%Y%m%d_%H%M%S")
WRITTEN: list[Path] = []
SP_NONE_FIX = False   # [criteria §5.9-3] the single allowed interface fix; set only from the smoke probe record


def log(msg: str = "") -> None:
    line = f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {msg}"
    print(line, flush=True)
    if LOG_FH is not None:
        LOG_FH.write(line + "\n")
        LOG_FH.flush()


def open_log(cmd: str) -> None:
    global LOG_FH, LOG_PATH, RUN_TS
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    base = RUN_TS
    for i in range(1, 100):                       # two starts within one second get distinct names
        LOG_PATH = LOG_DIR / f"{cmd}_{RUN_TS}.log"
        if not LOG_PATH.exists():
            break
        RUN_TS = f"{base}_{i}"
    LOG_FH = open(LOG_PATH, "x", encoding="utf-8", newline="\n")


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest().upper()


def ensure_absent(paths) -> None:
    ex = [str(p) for p in paths if Path(p).exists()]
    if ex:
        raise Stop(12, "REFUSE: output already exists, nothing is overwritten (V1 and every formal result count only "
                       "the first formal run [criteria §5.9 safeguard 1]): " + " ; ".join(ex))


def write_text(p: Path, text: str) -> None:
    ensure_absent([p])
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "x", encoding="utf-8", newline="\n") as f:
        f.write(text)
    WRITTEN.append(p)


def _jd(o):
    if isinstance(o, np.integer):
        return int(o)
    if isinstance(o, np.floating):
        return float(o)
    if isinstance(o, np.bool_):
        return bool(o)
    if isinstance(o, np.ndarray):
        return o.tolist()
    return str(o)


def write_json(p: Path, obj) -> None:
    write_text(p, json.dumps(obj, ensure_ascii=False, indent=2, default=_jd) + "\n")


def write_csv(p: Path, df: pd.DataFrame) -> None:
    write_text(p, df.to_csv(index=False, lineterminator="\n"))


def write_npz(p: Path, arrays: dict) -> None:
    ensure_absent([p])
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "xb") as f:
        np.savez_compressed(f, **arrays)
    WRITTEN.append(p)


def finish(cmd: str, rc: int) -> None:
    """Close the log."""
    global LOG_FH
    log(f"=== {cmd} end | exit code {rc}")
    if LOG_FH is not None:
        LOG_FH.close()
        LOG_FH = None


def env_versions() -> dict:
    v = {"python": sys.version.split()[0], "numpy": np.__version__, "pandas": pd.__version__}
    for mod in ("statsforecast", "statsmodels", "pyarrow"):
        try:
            v[mod] = __import__(mod).__version__
        except Exception as exc:  # noqa: BLE001
            v[mod] = f"IMPORT-ERROR {type(exc).__name__}"
    return v


def header(cmd: str, strict_env: bool) -> dict:
    me = Path(__file__).resolve()
    log(f"=== {cmd} start | {SCRIPT_VERSION} | argv {sys.argv[1:]}")
    log(f"script {me}")
    v = env_versions()
    log("versions: " + " | ".join(f"{k} {v[k]}" for k in ("python", "statsforecast", "statsmodels", "numpy",
                                                            "pandas", "pyarrow")))
    bad = {k: (v.get(k), want) for k, want in ENV_PINNED.items() if v.get(k) != want}
    if bad:
        msg = "environment differs from the pinned versions [criteria §5.9 pinned environment]: " + str(bad)
        if strict_env:
            raise Stop(11, msg + " -- refusing to compute")
        log("NOTE: " + msg + " (this subcommand computes no forecast)")
    return v


def verify_pinned(path: Path, pin) -> str:
    if not path.exists():
        raise Stop(14, f"input not found: {path}")
    got, size = sha256_file(path), path.stat().st_size
    log(f"input {path} SHA256 {got} size {size}")
    if path.name != pin[0] or got != pin[1] or size != pin[2]:
        raise Stop(14, f"input does not match the pinned file {pin[0]} / {pin[1]} / {pin[2]} B")
    return got


# ----------------------------------------------------------------------------------------------------------------------
# Scoring: RCRPS re-written from the criteria wording [criteria §5.1] (HF script read as text only)
# ----------------------------------------------------------------------------------------------------------------------
def crps_pwm(target, samples) -> np.ndarray:
    """[criteria §5.1-1] CRPS per variable, probability-weighted-moment form (HF :26-69). samples (n, d), target (d,).
    n == 1 (point forecast): |y - x|, which equals the PWM value of n identical copies (the PWM denominator n(n-1) is
    0 at n = 1)."""
    y = np.asarray(target, dtype=float)
    x = np.asarray(samples, dtype=float)
    if x.ndim != 2 or x.shape[1:] != y.shape:
        raise ValueError(f"shape mismatch {y.shape} vs {x.shape}")
    n = x.shape[0]
    if n == 1:
        return np.abs(y - x[0])
    s = np.sort(x, axis=0)
    abs_diff = np.abs(y[None, :] - s).sum(axis=0) / n
    beta0 = s.sum(axis=0) / n
    i_arr = np.arange(n, dtype=float)[:, None]
    beta1 = (i_arr * s).sum(axis=0) / (n * (n - 1))
    return abs_diff + beta0 - 2.0 * beta1


def mean_crps(target, samples) -> float:
    y = np.asarray(target, dtype=float)
    if y.size == 0:
        raise RuntimeError("CRPS received an empty target")
    return float(crps_pwm(y, samples).mean())


def constraint_violation(inst: dict, samples: np.ndarray, scaling: float) -> np.ndarray:
    """[criteria §5.1-3] per-sample violation: forecast, constraint_min / constraint_max and variable-max thresholds are all
    multiplied by metric_scaling; min and max terms are means over ALL steps; the variable-max term is the mean over the
    indexed steps only; the three terms are ADDED (HF :310-334)."""
    ss = scaling * samples
    v = np.clip(scaling * inst["cmin"] - ss, 0.0, None).mean(axis=1)
    v = v + np.clip(ss - scaling * inst["cmax"], 0.0, None).mean(axis=1)
    idx = inst["vmax_idx"]
    if len(idx) > 0:
        thr = scaling * np.asarray(inst["vmax_vals"], dtype=float)
        v = v + np.clip(ss[:, idx] - thr[None, :], 0.0, None).mean(axis=1)
    return v


def rcrps_raw(inst: dict, samples) -> float:
    """[criteria §5.1-3..5] RCRPS before the cap: metric_scaling * CRPS(RoI rule) + CRPS(10 * violation vs 0) (HF :376-420).
    metric_scaling is the HF field value, never recomputed [criteria §5.1-2]. No clipping of the forecast [criteria §5.1-7]."""
    x = np.asarray(samples, dtype=float)
    if x.ndim == 1:
        x = x[None, :]
    y = np.asarray(inst["future"], dtype=float)
    if x.shape[1] != y.shape[0]:
        raise ValueError("forecast length differs from the future length")
    scaling = float(inst["scaling"])
    roi = np.asarray(inst["roi"], dtype=np.int64)
    if len(roi) > 0:                                   # [criteria §5.1-4] "length > 0"
        mask = np.zeros(y.shape[0], dtype=bool)
        mask[roi] = True
        c = 0.5 * mean_crps(y[mask], x[:, mask]) + 0.5 * mean_crps(y[~mask], x[:, ~mask])
    else:
        c = mean_crps(y, x)
    viol = 10.0 * constraint_violation(inst, x, scaling)
    vcrps = float(crps_pwm(np.zeros(1), viol[:, None])[0])
    return float(scaling * c + vcrps)


def cap_rcrps(raw: float) -> float:
    """[criteria §5.1-5] RCRPS >= 5 is recorded as 5 (HF :492-494)."""
    return RCRPS_CAP if raw >= RCRPS_CAP else raw


def aggregate_rcrps(weights, capped) -> float:
    """[criteria §5.1-6] sum Fraction(w_i) * RCRPS_i / sum Fraction(w_i), row by row in parquet order. The accumulators start
    at 0.0 as in HF :472-501 (Fraction * float -> float), so the arithmetic is the same as the reference text."""
    ws, tw = 0.0, 0.0
    for w, m in zip(weights, capped):
        f = Fraction(str(w))
        ws += f * float(m)
        tw += f
    return float(ws / tw)


def pooled_rmse(pairs) -> float:
    """[criteria §5.6] N2F: squared errors of ALL points pooled, then sqrt (accuracy-ts.py:282-286)."""
    y = np.concatenate([np.asarray(t, dtype=float) for t, _ in pairs])
    f = np.concatenate([np.asarray(p, dtype=float) for _, p in pairs])
    return float(np.sqrt(np.mean((y - f) ** 2)))


# ----------------------------------------------------------------------------------------------------------------------
# Controls: R1 seasonal naive, R2 statistical ensemble (ur_b.py, unchanged logic) [criteria_round1 §3] [B0.1-1, 2]
# ----------------------------------------------------------------------------------------------------------------------
def causal_ffill(y) -> np.ndarray:
    """[B0.1-5] forward fill only (value i depends on values <= i)."""
    return pd.Series(np.asarray(y, dtype=float)).ffill().to_numpy()


def snaive(hist, horizon: int, m: int):
    """[criteria §5.2] R1: yhat_{T+h} = y_{T+h-m*ceil(h/m)} (same as ur_b.py). History shorter than m -> naive (m=1),
    the caller counts it. Returns (forecast, effective m)."""
    hist = np.asarray(hist, dtype=float)
    if hist.size == 0:
        return np.full(horizon, np.nan), 0
    m = int(m)
    m_eff = m if (m > 1 and len(hist) >= m) else 1
    last = hist[-m_eff:]
    return np.array([last[h % m_eff] for h in range(horizon)], dtype=float), m_eff


class R2Tally:
    """[criteria §5.2] [UR_B] R2 sentinel. hard=True (primary runs): the first 20 calls all "three failed" -> stop; a model
    failing at EVERY call -> stop (checked at the end of the phase, before anything is scored or written).
    hard=False (descriptive sensitivities fixed in advance; NOT IN CRITERIA which tally they use): log only."""

    def __init__(self, tag: str, hard: bool):
        self.tag, self.hard = tag, hard
        self.calls, self.allfail = 0, 0
        self.fail = {k: 0 for k in MODEL_ORDER}
        self.modes = {"median3": 0, "median2": 0, "single": 0, "R1": 0}
        self.first_err: dict = {}
        self.tripped = False

    def record(self, stat: dict, mode: str) -> None:
        self.calls += 1
        for k in MODEL_ORDER:
            if stat[k] != "ok":
                self.fail[k] += 1
        self.modes[mode] += 1
        if mode == "R1":
            self.allfail += 1
        if self.calls == SENTINEL_N and self.allfail == SENTINEL_N:
            self.tripped = True
            if self.hard:
                raise Stop(3, f"R2 SENTINEL [{self.tag}]: the first {SENTINEL_N} R2 calls all failed for all three "
                              f"models (first errors: {self.first_err}). R2 would silently equal R1 -- stopping "
                              f"[criteria §5.2] [criteria §9].")
            log(f"WARNING (descriptive sensitivity tally, not a stop): R2 SENTINEL [{self.tag}]: the first "
                f"{SENTINEL_N} R2 calls all fell back to R1 (first errors: {self.first_err})")

    def final_check(self) -> None:
        if self.calls == 0:
            return
        every = [k for k in MODEL_ORDER if self.calls >= SENTINEL_N and self.fail[k] == self.calls]
        if every:
            msg = (f"R2 SENTINEL [{self.tag}]: model(s) {every} failed at EVERY one of {self.calls} R2 calls "
                   f"(first errors: {self.first_err})")
            if self.hard:
                raise Stop(3, msg + " -- stopping [criteria §5.2] [criteria §9]")
            log("WARNING (descriptive sensitivity tally, not a stop): " + msg)

    def line(self) -> str:
        return (f"R2 tally [{self.tag}]: calls={self.calls} all-three-failed(->R1)={self.allfail} "
                f"fail_ETS={self.fail['ETS']} fail_Theta={self.fail['Theta']} fail_ARIMA={self.fail['ARIMA']} "
                f"median3={self.modes['median3']} median2={self.modes['median2']} single={self.modes['single']}")

    def as_dict(self) -> dict:
        return dict(tag=self.tag, hard_sentinel=self.hard, sentinel_tripped=self.tripped,
                    every_call_failed=[k for k in MODEL_ORDER if self.calls and self.fail[k] == self.calls],
                    calls=self.calls, allfail_to_R1=self.allfail,
                    **{f"fail_{k}": v for k, v in self.fail.items()}, **{f"mode_{k}": v for k, v in self.modes.items()},
                    first_errors={f"{a}/{b}": c for (a, b), c in self.first_err.items()})


def combine_r2(comp: dict, stat: dict, hist, horizon: int, m_r1: int):
    """[criteria_round1 §3] one model fails -> median of the other two; two fail -> the remaining one ([B0.1-2]); all three -> R1."""
    ok = [comp[k] for k in MODEL_ORDER if stat[k] == "ok"]
    if ok:
        return np.median(np.vstack(ok), axis=0), {3: "median3", 2: "median2", 1: "single"}[len(ok)]
    point, _ = snaive(hist, horizon, m_r1)
    return point, "R1"


def r2_forecast(hist, horizon: int, m_r1: int, m2: int, tally: R2Tally) -> dict:
    """[criteria_round1 §3] [B0.1-2] point-wise median of statsforecast 2.1.1 AutoETS / AutoTheta / AutoARIMA, season_length = m2.
    Raising or non-finite / mis-shaped output = failure of that model (counted)."""
    from statsforecast.models import AutoARIMA, AutoETS, AutoTheta

    ctors = {"ETS": AutoETS, "Theta": AutoTheta, "ARIMA": AutoARIMA}
    y = np.asarray(hist, dtype=float)
    comp, stat = {}, {}
    for name in MODEL_ORDER:
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                mdl = ctors[name](season_length=int(m2))
                mdl.fit(y)
                pred = np.asarray(mdl.predict(h=horizon)["mean"], dtype=float)
            if pred.shape != (horizon,) or not np.all(np.isfinite(pred)):
                raise ValueError("non-finite or mis-shaped forecast")
            comp[name], stat[name] = pred, "ok"
        except Exception as exc:  # noqa: BLE001  (a failure is a recorded outcome)
            comp[name], stat[name] = np.full(horizon, np.nan), f"fail:{type(exc).__name__}"
            key = (name, type(exc).__name__)
            if key not in tally.first_err:
                tally.first_err[key] = str(exc)[:300]
                log(f"R2 component failure (first of its kind) [{tally.tag}]: {name} {type(exc).__name__}: "
                    f"{str(exc)[:300]} [history length {len(y)}, season_length {m2}, horizon {horizon}]")
    point, mode = combine_r2(comp, stat, y, horizon, m_r1)
    tally.record(stat, mode)
    return dict(point=point, comp=comp, stat=stat, mode=mode)


# ----------------------------------------------------------------------------------------------------------------------
# CiK Exp-Smoothing anchor [criteria §5.9] (statsmodels.py.txt:57-90 and appendix D.9; "our convention" items marked)
# ----------------------------------------------------------------------------------------------------------------------
def anchor_config(n_past: int, sp: int, fix: bool):
    """[criteria §5.9-2, 5.9-3] trend 'add' unless len(past) < 5; seasonal_periods = instance field, set to -1 when
    len(past) < 2*sp; seasonal 'add' iff sp >= 1; sp passed as is, or None when seasonal is None and the single
    interface fix allowed by the criteria is active."""
    trend = None if n_past < 5 else "add"
    sp_eff = int(sp)
    if n_past < 2 * sp_eff:
        sp_eff = -1
    seasonal = "add" if sp_eff >= 1 else None
    sp_arg = None if (fix and seasonal is None) else sp_eff
    return trend, seasonal, sp_eff, sp_arg


def anchor_run(hist, horizon: int, sp: int, seed: int, offsets, fix: bool) -> dict:
    """[criteria §5.9-1..5, 7] fit ONCE with all defaults, then simulate 25 paths for each seed offset with a NEW
    np.random.default_rng(seed + offset) per call (offset 0 = the V1 run). The fit is deterministic, so fitting once
    and simulating per offset equals re-running the anchor per offset. Any exception, mis-shaped or non-finite output
    -> that (instance, offset) is a failure (RCRPS 5 is assigned by the caller). Warnings are ignored and counted."""
    from statsmodels.tsa.holtwinters import ExponentialSmoothing

    endog = np.asarray(hist, dtype=np.float64)             # [criteria §5.9-1] numpy float64 1-d (our convention)
    trend, seasonal, sp_eff, sp_arg = anchor_config(len(endog), sp, fix)
    out = dict(trend=trend, seasonal=seasonal, sp_eff=sp_eff, sp_arg=sp_arg, fit_status="ok", samples={},
               sim_status={}, warn=Counter())
    try:
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            res = ExponentialSmoothing(endog=endog, trend=trend, seasonal=seasonal, seasonal_periods=sp_arg).fit()
        out["warn"].update(w.category.__name__ for w in caught)
    except Exception as exc:  # noqa: BLE001
        out["fit_status"] = f"fail:{type(exc).__name__}: {str(exc)[:200]}"
        for off in offsets:
            out["samples"][off], out["sim_status"][off] = None, "fit_failed"
        return out
    for off in offsets:
        try:
            with warnings.catch_warnings(record=True) as caught:
                warnings.simplefilter("always")
                sim = res.simulate(nsimulations=horizon, repetitions=N_SAMPLES,
                                   random_state=np.random.default_rng(int(seed) + int(off)))   # [criteria §5.9-5]
            out["warn"].update(w.category.__name__ for w in caught)
            sim = np.asarray(sim, dtype=float)
            if sim.shape != (horizon, N_SAMPLES):
                raise ValueError(f"simulate returned shape {sim.shape}, expected {(horizon, N_SAMPLES)}")
            s = sim.T                                                # (25, H), as CiK's .transpose()
            if not np.all(np.isfinite(s)):
                raise ValueError("non-finite simulated values")
            out["samples"][off], out["sim_status"][off] = s, "ok"
        except Exception as exc:  # noqa: BLE001
            out["samples"][off], out["sim_status"][off] = None, f"fail:{type(exc).__name__}: {str(exc)[:200]}"
    return out


# ----------------------------------------------------------------------------------------------------------------------
# CiK data and structure gate [criteria §6.1]
# ----------------------------------------------------------------------------------------------------------------------
def parse_series(s: str):
    """past_time / future_time: column-oriented JSON {"<col>": {"<ISO timestamp>": value, ...}}.
    The target is the last column (HF :367). Order of the JSON object is kept; the gate then requires strictly
    increasing timestamps, so file order and time order coincide."""
    obj = json.loads(s)
    if not isinstance(obj, dict) or len(obj) == 0:
        raise ValueError("not a non-empty column-oriented JSON object")
    keys_c = list(obj.keys())
    inner = obj[keys_c[-1]]
    if not isinstance(inner, dict) or len(inner) == 0:
        raise ValueError("target column is not a non-empty {timestamp: value} object")
    tkeys = list(inner.keys())
    vals = np.array([np.nan if inner[k] is None else float(inner[k]) for k in tkeys], dtype=float)
    ts = pd.DatetimeIndex(pd.to_datetime(tkeys, format="ISO8601"))
    return [str(c) for c in keys_c], ts, vals


def _int_arr(x) -> np.ndarray:
    if x is None:
        return np.zeros(0, dtype=np.int64)
    a = np.asarray(x).ravel()
    if a.size == 0:
        return np.zeros(0, dtype=np.int64)
    af = a.astype(float)
    if not np.all(np.isfinite(af)) or not np.all(af == np.round(af)):
        raise ValueError("non-integer index")
    return af.astype(np.int64)


def _float_arr(x) -> np.ndarray:
    if x is None:
        return np.zeros(0, dtype=float)
    return np.asarray(x, dtype=float).ravel()


def infer_freq(ts: pd.DatetimeIndex):
    """[criteria §5.2 sensitivity] same inference as the input pre-check: pd.infer_freq on the last <= 60 stamps."""
    if len(ts) < 3:
        return None
    try:
        return pd.infer_freq(ts[-min(len(ts), 60):])
    except Exception:  # noqa: BLE001
        return None


def load_cik(path: Path):
    """Returns (instances in parquet row order, gate report). Gate items [criteria §6.1]; items marked EXTRA are NOT IN
    CRITERIA: they only guard against inputs that would make the reference scorer produce NaN or crash, and they STOP
    instead of choosing a treatment."""
    df = pd.read_parquet(path)
    recs = df.to_dict(orient="records")
    insts, gate_fail, extra_fail = [], [], []
    for i, rec in enumerate(recs):
        try:
            pcols, pts, pv = parse_series(rec["past_time"])
            fcols, fts, fv = parse_series(rec["future_time"])
            inst = dict(row=i, name=str(rec["name"]), seed=int(rec["seed"]), weight=str(rec["weight"]).strip(),
                        sp=int(rec["seasonal_period"]), scaling=float(rec["metric_scaling"]),
                        roi=_int_arr(rec["region_of_interest"]), cmin=float(rec["constraint_min"]),
                        cmax=float(rec["constraint_max"]), vmax_idx=_int_arr(rec["constraint_variable_max_index"]),
                        vmax_vals=_float_arr(rec["constraint_variable_max_values"]), past_cols=pcols,
                        future_cols=fcols, past_ts=pts, future_ts=fts, past_raw=pv, future=fv, H=len(fv))
        except Exception as exc:  # noqa: BLE001
            gate_fail.append(f"row {i}: parse error {type(exc).__name__}: {str(exc)[:150]}")
            continue
        insts.append(inst)
    g = {"n_rows": len(df), "n_parsed": len(insts)}
    # [criteria §6.1] 355 rows, 71 tasks x 5 seeds, (name, seed) unique, weight sum 105
    if len(df) != 355:
        gate_fail.append(f"rows {len(df)} != 355")
    names = Counter(x["name"] for x in insts)
    seeds_per = {n: len({x["seed"] for x in insts if x["name"] == n}) for n in names}
    g["n_tasks"] = len(names)
    g["seeds_per_task_counts"] = dict(Counter(seeds_per.values()))
    if len(names) != 71:
        gate_fail.append(f"tasks {len(names)} != 71")
    if any(v != 5 for v in seeds_per.values()):
        gate_fail.append("some task does not have exactly 5 seeds")
    pairs = Counter((x["name"], x["seed"]) for x in insts)
    if any(v > 1 for v in pairs.values()):
        gate_fail.append("(name, seed) not unique")
    try:
        wsum = sum((Fraction(x["weight"]) for x in insts), Fraction(0))
        g["weight_sum"] = str(wsum)
        if wsum != 105:
            gate_fail.append(f"weight sum {wsum} != 105")
    except Exception as exc:  # noqa: BLE001
        gate_fail.append(f"weight not parseable as Fraction: {exc}")
    n_nonmono = n_cols = n_roi_bad = n_scal = n_cnan = n_vbad = n_fut_nf = n_sp_bad = n_past_nf = 0
    for x in insts:
        if not (np.all(np.diff(x["past_ts"].asi8) > 0) and np.all(np.diff(x["future_ts"].asi8) > 0)):
            n_nonmono += 1                                           # [criteria §6.1] strictly increasing timestamps
        if not (len(x["past_cols"]) == 1 and x["past_cols"] == x["future_cols"]):
            n_cols += 1                                              # [criteria §6.1] target column unique
        roi, H = x["roi"], x["H"]
        if len(roi) > 0 and (np.any(roi < 0) or np.any(roi >= H) or len(set(roi.tolist())) != len(roi)
                             or len(roi) >= H):
            n_roi_bad += 1                                           # [criteria §6.1] RoI in [0,H), unique, not all H
        if not (np.isfinite(x["scaling"]) and x["scaling"] > 0):
            n_scal += 1                                              # EXTRA
        if np.isnan(x["cmin"]) or np.isnan(x["cmax"]):
            n_cnan += 1                                              # EXTRA
        vi = x["vmax_idx"]
        if len(vi) > 0 and (len(vi) != len(x["vmax_vals"]) or np.any(vi < 0) or np.any(vi >= H)
                            or not np.all(np.isfinite(x["vmax_vals"]))):
            n_vbad += 1                                              # EXTRA
        if not np.all(np.isfinite(x["future"])):
            n_fut_nf += 1                                            # EXTRA
        if x["sp"] not in (-1, 7, 24):
            n_sp_bad += 1                                            # EXTRA ([criteria §5.2] lists only -1 / 24 / 7)
        if not np.all(np.isfinite(x["past_raw"])):
            n_past_nf += 1                                           # handled by [B0.1-5], counted
    for cnt, msg in ((n_nonmono, "timestamps not strictly increasing"), (n_cols, "target column not unique"),
                     (n_roi_bad, "RoI index out of [0,H), duplicated, or covering all H steps")):
        if cnt:
            gate_fail.append(f"{cnt} instance(s): {msg}")
    for cnt, msg in ((n_scal, "metric_scaling not finite > 0"), (n_cnan, "constraint_min/max is NaN"),
                     (n_vbad, "variable-max index/value invalid"), (n_fut_nf, "non-finite future value"),
                     (n_sp_bad, "seasonal_period not in {-1, 7, 24}")):
        if cnt:
            extra_fail.append(f"EXTRA (NOT IN CRITERIA, stop and report): {cnt} instance(s): {msg}")
    g["finite_constraint_min"] = int(sum(np.isfinite(x["cmin"]) for x in insts))      # [criteria §6.1] counts only
    g["finite_constraint_max"] = int(sum(np.isfinite(x["cmax"]) for x in insts))
    g["roi_nonempty"] = int(sum(len(x["roi"]) > 0 for x in insts))
    g["vmax_nonempty"] = int(sum(len(x["vmax_idx"]) > 0 for x in insts))
    g["seasonal_period_counts"] = {str(k): v for k, v in sorted(Counter(x["sp"] for x in insts).items())}
    pl = [len(x["past_raw"]) for x in insts]
    fl = [x["H"] for x in insts]
    if pl:
        g["past_len_min_med_max"] = (min(pl), float(np.median(pl)), max(pl))
        g["future_len_min_med_max"] = (min(fl), float(np.median(fl)), max(fl))
    g["inferred_freq_counts"] = dict(Counter(str(infer_freq(x["past_ts"])) for x in insts))
    g["past_with_nonfinite_ffilled"] = n_past_nf
    g["future_starts_after_past_end"] = int(sum(int(x["future_ts"][0] > x["past_ts"][-1]) for x in insts))
    for x in insts:                                                  # [B0.1-5] causal ffill, leading gaps dropped
        h = causal_ffill(x["past_raw"])
        x["hist"] = h[np.isfinite(h)]
        x["m"] = x["sp"] if x["sp"] in (7, 24) else 1                # [criteria §5.2] 24 / 7 -> m; -1 -> m = 1
        x["m2"] = min(x["m"], R2_CAP)                                # [criteria §5.2] season_length = min(m, 24)
    n_empty = sum(1 for x in insts if len(x["hist"]) == 0)
    if n_empty:                                                      # R1/R2 would be NaN
        extra_fail.append(f"EXTRA (NOT IN CRITERIA, stop and report): {n_empty} instance(s): no finite past "
                          f"value")
    if n_past_nf:                                                    # anchor endog would differ [criteria §5.9-1]
        extra_fail.append(f"EXTRA (NOT IN CRITERIA, stop and report): {n_past_nf} instance(s): non-finite "
                          f"past values (anchor endog would differ from the past_time column [criteria §5.9-1])")
    g["gate_failures"], g["extra_check_failures"] = gate_fail, extra_fail
    g["ok"] = not gate_fail and not extra_fail
    return insts, g


def log_gate(g: dict, tag: str) -> None:
    for k in ("n_rows", "n_parsed", "n_tasks", "seeds_per_task_counts", "weight_sum", "seasonal_period_counts",
              "past_len_min_med_max", "future_len_min_med_max", "roi_nonempty", "vmax_nonempty",
              "finite_constraint_min", "finite_constraint_max", "inferred_freq_counts", "past_with_nonfinite_ffilled",
              "future_starts_after_past_end"):
        if k in g:
            log(f"{tag} gate info {k}: {g[k]}")
    for m in g.get("gate_failures", []) + g.get("extra_check_failures", []):
        log(f"{tag} STOP item: {m}")
    log(f"{tag} structure gate: {'PASS' if g['ok'] else 'FAIL'}")


# ----------------------------------------------------------------------------------------------------------------------
# N2F data and structure gate [criteria §5.6] [criteria §6.4]
# ----------------------------------------------------------------------------------------------------------------------
NUM_RE = re.compile(r"-?\d+(?:\.\d+)?")     # [criteria §5.6] the tokeniser of the input pre-check


def parse_n2f(path: Path):
    items = json.loads(path.read_text(encoding="utf-8-sig"))
    fails, wins = [], []
    if not isinstance(items, list):
        return [], ["top level is not a list"]
    if len(items) != N2F_N_WINDOWS:
        fails.append(f"{len(items)} windows != {N2F_N_WINDOWS}")
    for i, it in enumerate(items):
        if not isinstance(it, dict) or "instruction" not in it or "output" not in it:
            fails.append(f"window {i}: missing instruction/output")
            continue
        a_ = [float(t) for t in NUM_RE.findall(str(it["instruction"]))]
        b_ = [float(t) for t in NUM_RE.findall(str(it["output"]))]
        if len(a_) != N2F_LEN or len(b_) != N2F_LEN:
            fails.append(f"window {i}: instruction {len(a_)} / output {len(b_)} numbers, need {N2F_LEN} each")
            continue
        mm = re.search(r"region for prediction is ([A-Za-z]+)", str(it.get("input", "")))
        wins.append(dict(idx=i, hist=np.array(a_), truth=np.array(b_), region=mm.group(1) if mm else ""))
    return wins, fails


# ----------------------------------------------------------------------------------------------------------------------
# Nexus R3 read-out and judgement helpers
# ----------------------------------------------------------------------------------------------------------------------
def geomean(vals) -> float:
    v = np.asarray([float(x) for x in vals], dtype=float)
    if v.size == 0 or not np.all(np.isfinite(v)) or np.any(v <= 0):
        return float("nan")
    return float(np.exp(np.mean(np.log(v))))


def nexus_r3(table: dict, pool=NEXUS_POOL, systems=NEXUS_SYSTEMS) -> dict:
    """[criteria §5.4] system value = per column the smaller of the two Nexus versions; best single model = the pool model
    (same model on all columns) with the smallest geometric mean of model / system; ties -> pool order (strict <).
    Sensitivity: per column the best pool model, then the geometric mean."""
    ncol = len(next(iter(table.values())))
    sysv = [min(table[s][j] for s in systems) for j in range(ncol)]
    which = [min(systems, key=lambda s, j=j: table[s][j]) for j in range(ncol)]
    gm = {m: geomean([table[m][j] / sysv[j] for j in range(ncol)]) for m in pool}
    best = None
    for m in pool:
        if best is None or gm[m] < gm[best]:
            best = m
    percol = [min(table[m][j] for m in pool) / sysv[j] for j in range(ncol)]
    percol_model = [min(pool, key=lambda m, j=j: table[m][j]) for j in range(ncol)]
    return dict(system_values=sysv, system_version=which, geomean_by_model=gm, best_model=best, r=gm[best],
                per_column_ratio_best=[table[best][j] / sysv[j] for j in range(ncol)],
                sens_per_column_best_ratio=percol, sens_per_column_best_model=percol_model,
                r_sens_per_column_best=geomean(percol))


def tier(n: int, count: int) -> str:
    """[criteria_round1 §6] count = systems with r <= threshold."""
    if n < 6:
        return "N<6, not read"
    if count >= math.ceil(n / 2):
        return "matched tier"
    if count <= math.floor(n / 4):
        return "ahead tier (counter-evidence)"
    return "mixed tier"


def overall_tier(tiers) -> str:
    """[criteria_round1 §6] three thresholds in different tiers -> "close"."""
    t = list(tiers)
    return t[0] if all(x == t[0] for x in t) else "close"


def verdict_72(k: int, a: int, b: int) -> str:
    """[criteria §7.2]"""
    if k <= 2:
        return "insufficient test"
    if a >= k - 1 and b == k:
        return "supported"
    if a <= math.floor(k / 2) or (k - b) >= 2:
        return "not supported"
    return "partially supported"


def p_flags(r: float) -> dict:
    """[criteria §7.1] [criteria §5.12] unrounded comparisons."""
    ok = r is not None and np.isfinite(r)
    return dict(P1=bool(ok and r > P1), P2=bool(ok and r > P2), gt_1405=bool(ok and r > LST_ANCHOR_R))


def fmt(x, nd=3) -> str:
    return f"{x:.{nd}f}" if isinstance(x, (int, float, np.floating)) and np.isfinite(x) else "—"


# ----------------------------------------------------------------------------------------------------------------------
# selftest [criteria §5.11] -- synthetic data only, never reads HF data, prints PASS / FAIL only
# ----------------------------------------------------------------------------------------------------------------------
def _crps_slow(target, samples) -> np.ndarray:
    """Definition form as in tests/test_crps.py (text): E|X-y| - 0.5 E|X-X'| over distinct pairs (float64 here)."""
    n = samples.shape[0]
    first = np.abs(samples - target[None, :]).mean(axis=0)
    s = np.zeros(target.shape, dtype=float)
    for i in range(n - 1):
        for j in range(i + 1, n):
            s = s + np.abs(samples[i] - samples[j])
    return first - 0.5 * (s / (n * (n - 1) / 2))


def _mk(y, scaling, roi=(), cmin=-np.inf, cmax=np.inf, vidx=(), vvals=()) -> dict:
    return dict(future=np.asarray(y, dtype=float), scaling=float(scaling), roi=np.asarray(roi, dtype=np.int64),
                cmin=float(cmin), cmax=float(cmax), vmax_idx=np.asarray(vidx, dtype=np.int64),
                vmax_vals=np.asarray(vvals, dtype=float))


def _close(a, b, tol=1e-12) -> bool:
    return abs(float(a) - float(b)) <= tol * max(1.0, abs(float(b)))


def run_selftests() -> list:
    res = []

    def t(name, fn):
        try:
            ok, det = fn()
        except Exception as exc:  # noqa: BLE001
            ok, det = False, f"exception {type(exc).__name__}: {exc}"
        res.append((name, bool(ok), det))

    def t1():  # [criteria §5.11-1] PWM == slow definition, relative difference < 1e-9
        rng = np.random.default_rng(511)
        worst = 0.0
        for n in (3, 7, 25, 60):
            for _ in range(5):
                y = rng.normal(0.0, 1.0, size=10)
                x = rng.normal(0.3, 1.5, size=(n, 10))
                a_, b_ = crps_pwm(y, x), _crps_slow(y, x)
                worst = max(worst, float(np.max(np.abs(a_ - b_) / np.maximum(np.abs(b_), 1e-3))))
        return worst < 1e-9, f"max relative difference {worst:.3e}"

    def t2():  # [criteria §5.11-2] n identical points -> |y - x| (and the n = 1 branch)
        x = np.array([1.5, -2.0, 3.25])
        y = np.array([1.0, 1.0, 5.0])
        want = np.array([0.5, 3.0, 1.75])
        return all(np.allclose(crps_pwm(y, np.tile(x, (n, 1))), want, rtol=0, atol=1e-12)
                   for n in (1, 2, 7, 25)), ""

    def t3a():  # [criteria §5.11-3] RoI: 0.5*mean(RoI) + 0.5*mean(rest); scaling 0.5 -> 0.5*(0.5*1.5 + 0.5*3.5) = 1.25
        inst = _mk([0, 0, 0, 0], 0.5, roi=[0, 1])
        v = rcrps_raw(inst, np.array([[1.0, 2.0, 3.0, 4.0]]))
        return _close(v, 1.25), f"got {v}"

    def t3b():  # min/max: CRPS 0.5*1.5 = 0.75; min term 0.125 + max term 0.125 -> 10*0.25 = 2.5; total 3.25
        inst = _mk([1, 1, 1, 1], 0.5, cmin=0.0, cmax=2.0)
        v = rcrps_raw(inst, np.array([[-1.0, 0.0, 2.0, 3.0]]))
        return _close(v, 3.25), f"got {v}"

    def t3c():  # variable max on steps 1, 3 only: mean(0.5, 0) = 0.25 -> 2.5; CRPS 1.0; total 3.5
        inst = _mk([0, 0, 0, 0], 1.0, vidx=[1, 3], vvals=[0.5, 2.0])
        v = rcrps_raw(inst, np.array([[1.0, 1.0, 1.0, 1.0]]))
        return _close(v, 3.5), f"got {v}"

    def t3d():  # sample violation CRPS against 0: V = {0, 10, 10} -> 20/3 - 0.5*(40/6) = 10/3
        v = float(crps_pwm(np.zeros(1), np.array([[0.0], [10.0], [10.0]]))[0])
        inst = _mk([0, 0], 1.0, cmax=0.0)   # samples [0,0],[10,10],[10,10]: CRPS(X vs 0) and max violation
        w = rcrps_raw(inst, np.array([[0.0, 0.0], [10.0, 10.0], [10.0, 10.0]]))
        # CRPS per step: E|X| = 20/3, E|X-X'| = 40/6 -> 20/3 - 10/3 = 10/3; violation per sample 0,10,10 -> x10 = 0,100,
        # 100 -> CRPS 100/3; total 10/3 + 100/3 = 110/3
        return _close(v, 10.0 / 3.0) and _close(w, 110.0 / 3.0), f"got {v}, {w}"

    def t4():  # [criteria §5.11-4] cap
        return (cap_rcrps(7.0) == 5.0 and cap_rcrps(5.0) == 5.0 and cap_rcrps(4.999) == 4.999
                and cap_rcrps(0.0) == 0.0), ""

    def t5():  # [criteria §5.11-5] Fraction aggregation: (1/3*0.6 + 1/2*3.0 + 1*5)/(11/6) = 40.2/11
        v = aggregate_rcrps(["1/3", "1/2", "1"], [cap_rcrps(0.6), cap_rcrps(3.0), cap_rcrps(6.0)])
        return _close(v, 40.2 / 11.0), f"got {v}"

    def t6():  # R1 incl. h > m and degeneration [criteria §5.2]
        f, me = snaive([1, 2, 3, 4, 5, 6, 7], 7, 3)
        g_, mg = snaive([1, 2], 4, 3)
        h_, mh = snaive([4, 9], 3, 1)
        return (np.array_equal(f, [5, 6, 7, 5, 6, 7, 5]) and me == 3 and np.array_equal(g_, [2, 2, 2, 2]) and mg == 1
                and np.array_equal(h_, [9, 9, 9]) and mh == 1), ""

    def t7():  # N2F pooled RMSE: errors 3,4,0,0 -> sqrt(25/4) = 2.5 (per-window mean of RMSE would be 1.768)
        v = pooled_rmse([(np.array([0.0, 0.0]), np.array([3.0, 4.0])), (np.array([1.0, 1.0]), np.array([1.0, 1.0]))])
        return _close(v, 2.5), f"got {v}"

    def t8():  # N2F tokeniser [criteria §5.6]
        toks = [float(x) for x in NUM_RE.findall("The historical load data is: 1234.5,-6.0,7")]
        return toks == [1234.5, -6.0, 7.0], f"got {toks}"

    def t9():  # R2 fallback rules and sentinel [criteria_round1 §3] [criteria §5.2]
        a_, b_, c_ = np.array([1.0, 1.0]), np.array([2.0, 4.0]), np.array([9.0, 0.0])
        ok_all = {"ETS": "ok", "Theta": "ok", "ARIMA": "ok"}
        p3, m3 = combine_r2({"ETS": a_, "Theta": b_, "ARIMA": c_}, ok_all, [5.0], 2, 1)
        p2, m2 = combine_r2({"ETS": a_, "Theta": b_, "ARIMA": c_}, dict(ok_all, ARIMA="fail:X"), [5.0], 2, 1)
        p1, m1 = combine_r2({"ETS": a_, "Theta": b_, "ARIMA": c_}, {"ETS": "f", "Theta": "f", "ARIMA": "ok"},
                            [5.0], 2, 1)
        p0, m0 = combine_r2({"ETS": a_, "Theta": b_, "ARIMA": c_}, {"ETS": "f", "Theta": "f", "ARIMA": "f"},
                            [3.0, 5.0], 2, 1)
        ok = (np.array_equal(p3, [2.0, 1.0]) and m3 == "median3" and np.array_equal(p2, [1.5, 2.5])
              and m2 == "median2" and np.array_equal(p1, c_) and m1 == "single" and np.array_equal(p0, [5.0, 5.0])
              and m0 == "R1")
        tl = R2Tally("selftest", hard=True)
        bad = {"ETS": "f", "Theta": "f", "ARIMA": "f"}
        fired_early = False
        try:
            for _ in range(SENTINEL_N - 1):
                tl.record(bad, "R1")
        except Stop:
            fired_early = True
        fired = False
        try:
            tl.record(bad, "R1")
        except Stop as s:
            fired = s.code == 3
        tl2 = R2Tally("selftest2", hard=True)
        for _ in range(SENTINEL_N):
            tl2.record({"ETS": "f", "Theta": "ok", "ARIMA": "ok"}, "median2")
        fired2 = False
        try:
            tl2.final_check()
        except Stop as s:
            fired2 = s.code == 3
        return ok and not fired_early and fired and fired2, ""

    def t10():  # Nexus rule and tie order [criteria §5.4]
        tab = {"A": (2.0, 2.0), "B": (1.5, 3.0), "C": (2.0, 2.0), "S1": (1.0, 1.2), "S2": (1.1, 1.0)}
        r = nexus_r3(tab, pool=("B", "A", "C"), systems=("S1", "S2"))
        tie = nexus_r3({"A": (2.0,), "C": (2.0,), "S1": (1.0,), "S2": (1.0,)}, pool=("C", "A"), systems=("S1", "S2"))
        return (r["system_values"] == [1.0, 1.0] and r["best_model"] == "A" and _close(r["r"], 2.0)
                and _close(r["r_sens_per_column_best"], math.sqrt(1.5 * 2.0)) and tie["best_model"] == "C"), ""

    def t11():  # judgement tables [criteria_round1 §6] [criteria §7.2]
        ok = (tier(8, 4) == "matched tier" and tier(8, 2) == "ahead tier (counter-evidence)" and tier(8, 3) == "mixed tier"
              and tier(9, 5) == "matched tier" and tier(9, 3) == "mixed tier" and tier(5, 5).startswith("N<6")
              and overall_tier(["ahead tier (counter-evidence)", "ahead tier (counter-evidence)", "matched tier"]) == "close"
              and overall_tier(["mixed tier"] * 3) == "mixed tier")
        ok = ok and verdict_72(2, 2, 2) == "insufficient test" and verdict_72(3, 2, 3) == "supported"
        ok = ok and verdict_72(3, 1, 3) == "not supported" and verdict_72(3, 2, 2) == "partially supported"
        ok = ok and verdict_72(4, 3, 4) == "supported" and verdict_72(4, 3, 3) == "partially supported" and verdict_72(4, 2, 4) == "not supported"
        ok = ok and verdict_72(5, 4, 5) == "supported" and verdict_72(5, 2, 5) == "not supported" and verdict_72(5, 3, 3) == "not supported"
        ok = ok and verdict_72(5, 3, 4) == "partially supported"
        return ok, ""

    def t12():  # anchor configuration [criteria §5.9-2, 3]
        ok = anchor_config(3, -1, False) == (None, None, -1, -1) and anchor_config(3, -1, True) == (None, None, -1, None)
        ok = ok and anchor_config(10, 7, False) == ("add", None, -1, -1)
        ok = ok and anchor_config(14, 7, False) == ("add", "add", 7, 7)
        ok = ok and anchor_config(47, 24, False) == ("add", None, -1, -1)
        ok = ok and anchor_config(48, 24, True) == ("add", "add", 24, 24)
        return ok, ""

    def t13():  # unrounded threshold comparisons [criteria §5.12]
        f1 = p_flags(1.2214)
        f2 = p_flags(1.2209999)
        ok = f1["P1"] and f1["P2"] and not f2["P1"] and f2["P2"] and not p_flags(1.10)["P2"]
        ok = ok and not (1.0500000001 <= 1.05)
        # V1 boundary: 0.605 * 1.05 = 0.63525 -> 0.6352 is inside 5 %, 0.6353 is outside
        ok = ok and abs(0.6352 / CIK_ANCHOR_PAPER - 1.0) <= TOL_V1 and not (abs(0.6353 / CIK_ANCHOR_PAPER - 1.0) <= TOL_V1)
        return ok, ""

    for name, fn in (("5.11-1 PWM vs slow definition", t1), ("5.11-2 identical points = |y-x|", t2),
                     ("5.11-3a RoI example", t3a), ("5.11-3b min/max constraint example", t3b),
                     ("5.11-3c variable-max example", t3c), ("5.11-3d sample violation CRPS", t3d),
                     ("5.11-4 truncation at 5", t4), ("5.11-5 Fraction aggregation", t5),
                     ("R1 seasonal naive incl. h>m", t6), ("N2F pooled RMSE", t7), ("N2F tokeniser", t8),
                     ("R2 fallback + sentinel", t9), ("Nexus R3 rule + tie order", t10),
                     ("judgement tables (tier, 7.2)", t11), ("anchor configuration", t12),
                     ("unrounded thresholds", t13)):
        t(name, fn)
    return res


def selftests_must_pass() -> None:
    res = run_selftests()
    bad = [r for r in res if not r[1]]
    log(f"selftest: {len(res) - len(bad)}/{len(res)} PASS")
    if bad:
        for name, _, det in bad:
            log(f"selftest FAIL: {name} {det}")
        raise Stop(1, "scorer unit tests failed -- no formal run before they pass [criteria §5.9 safeguard 3] [criteria §5.11]")


def cmd_selftest(a) -> int:
    header("selftest", strict_env=False)
    res = run_selftests()
    for name, ok, det in res:
        log(f"{'PASS' if ok else 'FAIL'}  {name}" + ("" if ok else f"  ({det})"))
    nbad = sum(1 for r in res if not r[1])
    log(f"selftest: {len(res) - nbad}/{len(res)} PASS -> {'ALL PASS' if nbad == 0 else 'FAILED'}")
    return 0 if nbad == 0 else 1


# ----------------------------------------------------------------------------------------------------------------------
# smoke -- counts, ok / fail, timings only [criteria §5.9 safeguard 2]
# ----------------------------------------------------------------------------------------------------------------------
def check_prior_inputs() -> dict:
    out = {}
    for p in (UR_B_SUMMARY, RESULTS_A):
        found = p.exists()
        out[str(p)] = dict(exists=found, ok=found)
        log(f"prior-round input {p}: {'OK' if found else 'MISSING'}")
    if RESULTS_A.exists():
        txt = RESULTS_A.read_text(encoding="utf-8", errors="replace")
        miss = [k for k, (s, _, _) in A_READINGS.items() if s not in txt]
        out["results_a_strings_missing"] = miss
        log(f"round-1 literal readings present: {4 - len(miss)}/4")
    return out


def _readjson_agrees(s: str, ts: pd.DatetimeIndex, vals: np.ndarray) -> bool:
    """Evidence only: does pandas' read_json (the HF way, :366-367) give the same target column?"""
    import io
    d = pd.read_json(io.StringIO(s))
    v2 = d[d.columns[-1]].to_numpy(dtype=float)
    t2 = pd.DatetimeIndex(pd.to_datetime(d.index))
    return (len(v2) == len(vals) and bool(np.allclose(v2, vals, rtol=1e-12, atol=0.0, equal_nan=True))
            and bool(np.all(t2 == ts)))


def latest_smoke_dir() -> Path | None:
    if not SMOKE_DIR.exists():
        return None
    ds = sorted((d for d in SMOKE_DIR.iterdir() if d.is_dir() and (d / IFACE_NAME).exists()), key=lambda d: d.name)
    return ds[-1] if ds else None


def _interface_type(status: str) -> bool:
    return any(f"fail:{c}" in status for c in INTERFACE_ERRS) or "simulate returned shape" in status


def cmd_smoke(a) -> int:
    """Re-runnable: each run writes to <out>/smoke/<RUN_TS>/ and produces no aggregate error, anchor value
    or ratio [criteria §5.9 safeguard 2], so a re-run cannot be used to pick results. Failure rules follow the criteria: a
    single anchor failure is an outcome fixed in advance (RCRPS 5, [criteria §5.9-7]) and an R2 model failing is a fallback
    fixed in advance ([criteria_round1 §3]); smoke fails only on gate failures, interface-type errors, all-fallback, or non-finite scores."""
    global SP_NONE_FIX
    header("smoke", strict_env=True)
    sdir = SMOKE_DIR / RUN_TS
    ensure_absent([sdir / n for n in SMOKE_OUTPUTS])
    selftests_must_pass()
    verify_pinned(a.parquet, CIK_PARQUET_PIN)          # both inputs verified before anything is written
    verify_pinned(a.json, N2F_JSON_PIN)
    log(f"smoke outputs -> {sdir}")
    problems, cik_problems = [], []
    prior = check_prior_inputs()
    if not all(v["ok"] for k, v in prior.items() if isinstance(v, dict)) or prior.get("results_a_strings_missing"):
        problems.append("prior-round inputs for `summary` missing or incomplete")
    write_json(sdir / "smoke_inputs.json", prior)

    # ---- CiK ----------------------------------------------------------------------------------------------------
    t0 = time.time()
    insts, g = load_cik(a.parquet)
    log_gate(g, "CiK")
    if not g["ok"]:
        cik_problems.append("CiK structure gate failed")
    smoke = dict(gate=g, load_seconds=round(time.time() - t0, 2))
    iface = dict(probe_row=None, minus1_status=None, none_status=None, fix=False)
    if g["ok"]:
        log("history length of parquet rows 0-19 (metadata only; the R2 sentinel looks at these 20 calls): "
            f"{[len(x['hist']) for x in insts[:20]]}")
        # [criteria §5.9 safeguard 2] at most 10 instances: the first 10 rows; if none of them reaches the seasonal=None branch,
        # the last one is replaced by the first row that does (so the -1 interface is probed within the 10).
        def eff_minus1(x):
            return anchor_config(len(x["hist"]), x["sp"], False)[1] is None
        rows = list(range(min(10, len(insts))))
        if not any(eff_minus1(insts[i]) for i in rows):
            cand = [i for i, x in enumerate(insts) if eff_minus1(x)]
            if cand:
                rows[-1] = cand[0]
        probe = next((i for i in rows if eff_minus1(insts[i])), None)
        if probe is not None:                                        # [criteria §5.9-3] decide the single interface fix
            x = insts[probe]
            st = {}
            for fix in (False, True):
                r_ = anchor_run(x["hist"], x["H"], x["sp"], x["seed"], (0,), fix)
                st[fix] = "ok" if (r_["fit_status"] == "ok" and r_["sim_status"][0] == "ok") else \
                    (r_["fit_status"] if r_["fit_status"] != "ok" else r_["sim_status"][0])
            iface = dict(probe_row=probe, minus1_status=st[False], none_status=st[True],
                         fix=bool(st[False] != "ok" and st[True] == "ok"))
            log(f"anchor interface probe (row {probe}): seasonal_periods=-1 -> {st[False]} | "
                f"seasonal_periods=None -> {st[True]} | interface fix [criteria §5.9-3] needed: {iface['fix']}")
            if st[False] != "ok" and st[True] != "ok":
                cik_problems.append("anchor fails on the seasonal=None branch with and without the fix")
        else:
            cik_problems.append("no instance reaches the seasonal=None branch; interface not probed")
        SP_NONE_FIX = iface["fix"]
        # json.loads (ours) vs pd.read_json (HF) on the smoke rows -- evidence only, never a failure
        raw = pd.read_parquet(a.parquet, columns=["past_time", "future_time"])
        n_dis, n_err = 0, 0
        for i in rows:
            try:
                ok_p = _readjson_agrees(raw["past_time"].iloc[i], insts[i]["past_ts"], insts[i]["past_raw"])
                ok_f = _readjson_agrees(raw["future_time"].iloc[i], insts[i]["future_ts"], insts[i]["future"])
                n_dis += int(not (ok_p and ok_f))
            except Exception:  # noqa: BLE001
                n_err += 1
        log(f"parser cross-check json.loads vs pd.read_json on {len(rows)} smoke rows: disagreements {n_dis}, "
            f"read_json errors {n_err} (evidence only)")
        smoke["parser_crosscheck"] = dict(rows=len(rows), disagreements=n_dis, errors=n_err)
        tally = R2Tally("smoke CiK", hard=False)
        cnt = Counter()
        timing = Counter()
        warn = Counter()
        an_err = []
        for i in rows:
            x = insts[i]
            t1 = time.time()
            r2 = r2_forecast(x["hist"], x["H"], x["m"], x["m2"], tally)
            timing["R2"] += time.time() - t1
            r1, m_eff = snaive(x["hist"], x["H"], x["m"])
            cnt["r1_degenerate"] += int(x["m"] > 1 and m_eff == 1)
            t1 = time.time()
            an = anchor_run(x["hist"], x["H"], x["sp"], x["seed"], (0,), SP_NONE_FIX)
            timing["anchor"] += time.time() - t1
            warn.update(an["warn"])
            ok_an = an["fit_status"] == "ok" and an["sim_status"][0] == "ok"
            cnt["anchor_ok" if ok_an else "anchor_fail"] += 1
            if not ok_an:
                st_ = an["fit_status"] if an["fit_status"] != "ok" else an["sim_status"][0]
                an_err.append(st_)
                log(f"smoke anchor failure row {i}: {st_}")
            for lab, smp in (("R1", r1), ("R2", r2["point"]), ("anchor", an["samples"][0])):
                if smp is None:
                    continue
                v = rcrps_raw(x, smp)                     # computed only to test the pipeline; value never shown
                cnt[f"{lab}_rcrps_finite"] += int(np.isfinite(v))
        tally.final_check()
        log(tally.line())
        n_rows = len(rows)
        # R2: a model failing is a fallback fixed in advance; only interface-type errors or all-fallback fail the smoke
        every = [k for k in MODEL_ORDER if tally.calls and tally.fail[k] == tally.calls]
        for k in every:
            classes = sorted({c for (m, c) in tally.first_err if m == k})
            if any(c in INTERFACE_ERRS for c in classes):
                cik_problems.append(f"R2 model {k} failed at every smoke call with an interface-type error {classes}")
            else:
                log(f"NOTE smoke: R2 model {k} failed at every one of the {tally.calls} smoke calls ({classes}); "
                    f"fallback fixed in advance, reported, not a smoke failure")
        if tally.calls and tally.allfail == tally.calls:
            cik_problems.append("all smoke R2 calls fell back to R1 (sentinel-type)")
        # anchor: single failures are RCRPS 5 by [criteria §5.9-7]; all failing or interface-type errors fail the smoke
        if n_rows and cnt["anchor_fail"] == n_rows:
            cik_problems.append("every smoke anchor fit failed")
        iface_err = [e for e in an_err if _interface_type(e)]
        if iface_err:
            cik_problems.append(f"interface-type anchor error(s): {iface_err[:3]}")
        elif an_err:
            log(f"NOTE smoke: {len(an_err)} anchor failure(s) of a non-interface type; outcome fixed in advance "
                f"(RCRPS 5, [criteria §5.9-7]), reported, not a smoke failure")
        # scores must be finite
        if cnt["R1_rcrps_finite"] < n_rows or cnt["R2_rcrps_finite"] < n_rows or \
                cnt["anchor_rcrps_finite"] < cnt["anchor_ok"]:
            cik_problems.append("non-finite RCRPS in the smoke rows")
        log(f"smoke CiK rows {rows}: counts {dict(cnt)} | warnings {dict(warn)} | seconds R2 {timing['R2']:.1f} "
            f"anchor {timing['anchor']:.1f}")
        smoke.update(rows=rows, counts=dict(cnt), warnings=dict(warn), r2_tally=tally.as_dict(),
                     anchor_errors=an_err, seconds={k: round(v, 2) for k, v in timing.items()})
    iface.update(cik_smoke_pass=bool(g["ok"] and not cik_problems), cik_problems=cik_problems, smoke_run=RUN_TS)
    log(f"smoke CiK part: {'PASS' if iface['cik_smoke_pass'] else 'FAIL -> ' + ' | '.join(cik_problems)}")
    write_json(sdir / IFACE_NAME, iface)
    write_json(sdir / "smoke_cik.json", smoke)
    problems += cik_problems

    # ---- N2F ----------------------------------------------------------------------------------------------------
    wins, fails = parse_n2f(a.json)
    log(f"N2F structure gate: windows parsed {len(wins)}, failures {len(fails)} -> {'PASS' if not fails else 'FAIL'}")
    for f_ in fails[:20]:
        log(f"N2F STOP item: {f_}")
    if fails:
        problems.append("N2F structure gate failed")
    n2 = dict(n_windows=len(wins), gate_failures=fails, regions=dict(Counter(w["region"] for w in wins)))
    if not fails:
        tl = R2Tally("smoke N2F", hard=False)
        t1 = time.time()
        for w in wins[:3]:
            r2_forecast(w["hist"], N2F_LEN, N2F_M, min(N2F_M, R2_CAP), tl)
        log(tl.line() + f" | seconds {time.time() - t1:.1f}")
        if tl.allfail == tl.calls:
            problems.append("all N2F smoke R2 calls fell back to R1")
        for k in MODEL_ORDER:
            classes = sorted({c for (m, c) in tl.first_err if m == k})
            if tl.fail[k] == tl.calls and any(c in INTERFACE_ERRS for c in classes):
                problems.append(f"N2F smoke: R2 model {k} failed every call with an interface-type error {classes}")
        n2["r2_tally"] = tl.as_dict()
    write_json(sdir / "smoke_n2f.json", n2)
    log("SMOKE RESULT: " + ("PASS" if not problems else "FAIL -> " + " | ".join(problems)))
    return 0 if not problems else 2


# ----------------------------------------------------------------------------------------------------------------------
# cik -- the formal CiK / BNP run
# ----------------------------------------------------------------------------------------------------------------------
def cmd_cik(a) -> int:
    global SP_NONE_FIX
    header("cik", strict_env=True)
    ensure_absent([OUT / n for n in CIK_OUTPUTS])
    if CIK_LOCK.exists():
        raise Stop(13, f"{CIK_LOCK} exists: a formal CiK run already reached the anchor phase. V1 counts only the "
                       f"first formal run [criteria §5.9 safeguard 1]; do not re-run in this output folder.")
    selftests_must_pass()                                           # [criteria §5.9 safeguard 3]
    sd = latest_smoke_dir()                                         # the LATEST smoke run must have passed
    if sd is None:
        raise Stop(14, "no smoke run found: run `smoke` first (it checks CiK and decides the [criteria §5.9-3] interface fix)")
    iface = json.loads((sd / IFACE_NAME).read_text(encoding="utf-8"))
    if not iface.get("cik_smoke_pass", False):
        raise Stop(14, f"the latest smoke run ({sd.name}) did not PASS for CiK ({iface.get('cik_problems')}) -- "
                       f"no formal run [criteria §5.9 safeguards]")
    SP_NONE_FIX = bool(iface.get("fix", False))
    log(f"smoke run used: {sd.name} (CiK part PASS); anchor interface fix [criteria §5.9-3] in use: {SP_NONE_FIX} ({iface})")
    pq_sha = verify_pinned(a.parquet, CIK_PARQUET_PIN)
    insts, g = load_cik(a.parquet)
    log_gate(g, "CiK")
    if not g["ok"]:                                                 # [criteria §9] structure gate: stop, no hand-picking
        write_json(OUT / "cik_primary.json", dict(status="STRUCTURE_GATE_FAILED", gate=g))
        raise Stop(2, "CiK structure gate failed [criteria §6.1] [criteria §9] -- CiK and BNP stop here")
    n = len(insts)

    # Phase 1: R2 in parquet row order, hard sentinel [criteria §5.2]
    t2 = R2Tally("CiK R2 primary", hard=True)
    r2s = []
    t0 = time.time()
    for k, x in enumerate(insts):
        r2s.append(r2_forecast(x["hist"], x["H"], x["m"], x["m2"], t2))
        if (k + 1) % 50 == 0:
            log(f"R2 progress {k + 1}/{n} ({time.time() - t0:.0f} s)")
    t2.final_check()
    log(t2.line() + f" | {time.time() - t0:.0f} s")
    # Phase 2: R1 [criteria §5.2]
    r1s = [snaive(x["hist"], x["H"], x["m"]) for x in insts]
    # score R1 / R2 now, BEFORE the lock: a non-finite score (or a scorer crash) stops here and does not
    # consume the first formal run. The values are reused below unchanged.
    pre = [(rcrps_raw(x, r1), rcrps_raw(x, r2["point"])) for x, r2, (r1, _) in zip(insts, r2s, r1s)]
    bad = [x["row"] for x, (v1_, v2_) in zip(insts, pre) if not (np.isfinite(v1_) and np.isfinite(v2_))]
    if bad:
        raise Stop(5, f"non-finite R1/R2 RCRPS in parquet rows {bad[:20]} ({len(bad)} instance(s)) -- stopping before "
                      f"the anchor phase; nothing written, no lock")

    # Phase 3: anchor. From here on the run is THE first formal run [criteria §5.9 safeguard 1].
    write_text(CIK_LOCK, f"formal CiK run reached the anchor phase at {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
    offsets = (0,) + SEED_OFFSETS
    ans = []
    t0 = time.time()
    for k, x in enumerate(insts):
        ans.append(anchor_run(x["hist"], x["H"], x["sp"], x["seed"], offsets, SP_NONE_FIX))
        if (k + 1) % 50 == 0:
            log(f"anchor progress {k + 1}/{n} ({time.time() - t0:.0f} s)")
    log(f"anchor phase done ({time.time() - t0:.0f} s)")

    # Phase 4: score
    rows, frows = [], []
    w = [x["weight"] for x in insts]
    cap = {"R1": [], "R2": [], "anchor": []}
    seed_cap = {off: [] for off in offsets}
    seed_fail = Counter()
    seed_trunc = Counter()
    warn_tot = Counter()
    samples0 = {}
    for x, r2, (r1, m_eff), an, (raw1, raw2) in zip(insts, r2s, r1s, ans, pre):
        if an["samples"][0] is not None:
            samples0[f"row_{x['row']:03d}"] = an["samples"][0]
        an_raw = {}
        for off in offsets:
            if an["samples"][off] is None:                          # [criteria §5.9-7] failure -> RCRPS 5
                an_raw[off] = None
                seed_cap[off].append(RCRPS_CAP)
                seed_fail[off] += 1
            else:
                v = rcrps_raw(x, an["samples"][off])
                if not np.isfinite(v):                              # [criteria §5.9-7] non-finite output -> 5
                    an_raw[off] = None
                    seed_cap[off].append(RCRPS_CAP)
                    seed_fail[off] += 1
                else:
                    an_raw[off] = v
                    seed_cap[off].append(cap_rcrps(v))
                    seed_trunc[off] += int(v >= RCRPS_CAP)
        warn_tot.update(an["warn"])
        cap["R1"].append(cap_rcrps(raw1))
        cap["R2"].append(cap_rcrps(raw2))
        cap["anchor"].append(seed_cap[0][-1])
        rows.append(dict(row=x["row"], name=x["name"], seed=x["seed"], weight=x["weight"], past_len=len(x["hist"]),
                         H=x["H"], seasonal_period=x["sp"], metric_scaling=x["scaling"], constraint_min=x["cmin"],
                         constraint_max=x["cmax"], m_r1=x["m"], m_r1_eff=m_eff,
                         r1_degenerate=int(x["m"] > 1 and m_eff == 1), m2=x["m2"], r2_mode=r2["mode"],
                         **{f"r2_{k_}": r2["stat"][k_] for k_ in MODEL_ORDER},
                         rcrps_raw_R1=raw1, rcrps_R1=cap["R1"][-1], rcrps_raw_R2=raw2, rcrps_R2=cap["R2"][-1],
                         anchor_trend=an["trend"], anchor_seasonal=an["seasonal"], anchor_sp_eff=an["sp_eff"],
                         anchor_sp_arg=an["sp_arg"], anchor_fit_status=an["fit_status"],
                         anchor_sim_status=an["sim_status"][0],
                         rcrps_raw_anchor=(np.nan if an_raw[0] is None else an_raw[0]),
                         rcrps_anchor=cap["anchor"][-1], anchor_failed=int(an_raw[0] is None),
                         anchor_warnings=";".join(f"{k_}:{v_}" for k_, v_ in sorted(an["warn"].items())),
                         roi_len=len(x["roi"]), vmax_len=len(x["vmax_idx"])))
        for h in range(x["H"]):
            frows.append(dict(row=x["row"], h=h + 1, y=x["future"][h], r1=r1[h], r2=r2["point"][h],
                              ets=r2["comp"]["ETS"][h], theta=r2["comp"]["Theta"][h], arima=r2["comp"]["ARIMA"][h]))
    nonfinite = {k_: int(sum(not np.isfinite(v) for v in vals)) for k_, vals in cap.items()}
    if any(nonfinite.values()):
        log(f"WARNING: non-finite per-instance RCRPS {nonfinite} (aggregates will be NaN)")
    agg = {k_: aggregate_rcrps(w, vals) for k_, vals in cap.items()}           # [criteria §5.1-6]
    inst_df = pd.DataFrame(rows)
    trunc = dict(R1=int((inst_df["rcrps_raw_R1"] >= RCRPS_CAP).sum()),
                 R2=int((inst_df["rcrps_raw_R2"] >= RCRPS_CAP).sum()),
                 anchor=int(seed_trunc[0]))
    anchor_ratio = agg["anchor"] / CIK_ANCHOR_PAPER
    v1 = bool(abs(agg["anchor"] / CIK_ANCHOR_PAPER - 1.0) <= TOL_V1)          # [criteria §5.9 decision] [criteria §5.12]
    scale_ok = bool(SCALE_GATE[0] <= anchor_ratio <= SCALE_GATE[1])           # [criteria §1.4] [criteria §5.12]
    r = dict(CiK_R2=agg["R2"] / CIK_SYSTEM, CiK_R1=agg["R1"] / CIK_SYSTEM,
             BNP_R2=agg["R2"] / BNP_SYSTEM, BNP_R1=agg["R1"] / BNP_SYSTEM)
    status = ("counted (V1 passed, M-type anchor)" if v1 else
              "protocol not verified (anchor not within 5%" + ("" if scale_ok else "; magnitude gate failed") + "), r descriptive only")
    prim = dict(status="OK", script=SCRIPT_VERSION, parquet_sha256=pq_sha, n_instances=n, gate=g,
                interface_fix_used=SP_NONE_FIX, interface_probe=iface,
                aggregate_rcrps=agg, system_values=dict(CiK=CIK_SYSTEM, BNP=BNP_SYSTEM),
                anchor_paper=CIK_ANCHOR_PAPER, anchor_ratio=anchor_ratio, anchor_rel_dev=anchor_ratio - 1.0,
                v1_pass=v1, magnitude_gate_ok=scale_ok, cik_status=status,
                bnp_status="protocol not verified (5.8); R1/R2 computed as for CiK, descriptive only",
                r=r, flags={k_: p_flags(v_) for k_, v_ in r.items()},
                diagnostics=dict(truncated_at_5=trunc, truncated_paper_expsmoothing=CIK_EXPSMOOTH_FAILURES_PAPER,
                                 anchor_failures=int(seed_fail[0]),
                                 anchor_at_5_total=int(seed_fail[0] + seed_trunc[0]),
                                 r1_degenerate=int(inst_df["r1_degenerate"].sum()),
                                 r2_tally=t2.as_dict(), anchor_warnings=dict(warn_tot), nonfinite=nonfinite))
    write_csv(OUT / "cik_instances.csv", inst_df)
    write_csv(OUT / "cik_forecasts.csv", pd.DataFrame(frows))
    # for independent re-computation: capped anchor RCRPS per instance x offset, and the offset-0 samples
    write_csv(OUT / "cik_anchor_seed_rcrps.csv", pd.DataFrame(
        [dict(row=x["row"], name=x["name"], seed=x["seed"], weight=x["weight"],
              **{f"off_{off}": seed_cap[off][k] for off in offsets}) for k, x in enumerate(insts)]))
    write_npz(OUT / "cik_anchor_samples_offset0.npz", samples0)
    write_json(OUT / "cik_primary.json", prim)
    txt = [f"CiK / BNP formal run -- {SCRIPT_VERSION}",
           f"instances {n}; interface fix [criteria §5.9-3] used: {SP_NONE_FIX}",
           f"aggregate RCRPS (unrounded): R1 {agg['R1']!r}  R2 {agg['R2']!r}  Exp-Smoothing anchor {agg['anchor']!r}",
           f"V1 [criteria §5.9]: anchor / 0.605 = {anchor_ratio!r} (rel {anchor_ratio - 1.0:+.5f}) -> "
           f"{'PASS' if v1 else 'NOT PASS'}; magnitude gate 1/3..3: {'ok' if scale_ok else 'NOT ok'}",
           f"CiK: {status}",
           f"  r(R2) = {agg['R2']!r} / 0.159 = {r['CiK_R2']!r}  P1 (>1.221): {p_flags(r['CiK_R2'])['P1']}  "
           f"P2 (>1.10): {p_flags(r['CiK_R2'])['P2']}   r(R1) = {r['CiK_R1']!r}",
           f"BNP (protocol not verified, descriptive): r(R2) = {r['BNP_R2']!r}  r(R1) = {r['BNP_R1']!r}",
           f"truncated at 5 (raw >= 5): anchor {trunc['anchor']} (paper Table 6 Exp-Smoothing: 5), R1 {trunc['R1']}, "
           f"R2 {trunc['R2']}; anchor failures (set to 5) {int(seed_fail[0])}",
           f"R1 degenerate (history < m) {int(inst_df['r1_degenerate'].sum())}; " + t2.line(),
           f"anchor warnings (ignored, counted): {dict(warn_tot)}"]
    write_text(OUT / "cik_primary.txt", "\n".join(txt) + "\n")
    for ln in txt:
        log(ln)

    # Phase 5: descriptive items -- never change V1 / K / N_comb
    seed_aggs = {off: aggregate_rcrps(w, seed_cap[off]) for off in offsets}     # [criteria §5.9 descriptive items] 21 runs
    seed_df = pd.DataFrame([dict(offset=off, aggregate_rcrps=seed_aggs[off], n_failed=int(seed_fail[off]),
                                 n_truncated=int(seed_trunc[off])) for off in offsets])
    vals21 = np.array([seed_aggs[off] for off in offsets], dtype=float)
    seeds_desc = dict(n_runs=len(offsets), median=float(np.median(vals21)), p05=float(np.percentile(vals21, 5)),
                      p95=float(np.percentile(vals21, 95)),
                      n_within_5pct=int(sum(abs(v / CIK_ANCHOR_PAPER - 1.0) <= TOL_V1 for v in vals21)))
    # [criteria §5.2 sensitivity] -1 instances re-assigned a period from the frequency table; R2 still min(m, 24)
    ts_sens = R2Tally("CiK R2 sensitivity (-1 -> frequency table)", hard=False)
    sens_rows, unmapped = [], Counter()
    cap1s, cap2s = list(cap["R1"]), list(cap["R2"])
    for k, x in enumerate(insts):
        if x["sp"] != -1:
            continue
        fq = infer_freq(x["past_ts"])
        m_new = FREQ_TABLE.get(str(fq)) if fq is not None else None
        if m_new is None:
            unmapped[str(fq)] += 1
            continue
        if m_new == 1:
            sens_rows.append(dict(row=x["row"], freq=fq, m_new=1, recomputed=0))
            continue
        r1n, me = snaive(x["hist"], x["H"], m_new)
        r2n = r2_forecast(x["hist"], x["H"], m_new, min(m_new, R2_CAP), ts_sens)
        v1n, v2n = rcrps_raw(x, r1n), rcrps_raw(x, r2n["point"])
        cap1s[k], cap2s[k] = cap_rcrps(v1n), cap_rcrps(v2n)
        sens_rows.append(dict(row=x["row"], freq=fq, m_new=m_new, recomputed=1, m_r1_eff=me,
                              r1_degenerate=int(m_new > 1 and me == 1), r2_mode=r2n["mode"], rcrps_raw_R1=v1n,
                              rcrps_raw_R2=v2n))
    ts_sens.final_check()
    log(ts_sens.line())
    if unmapped:
        log(f"NOTE: -1 instances with a frequency outside the table fixed in advance {dict(unmapped)}: the frequency-table "
            f"sensitivity is NOT computed (NOT IN CRITERIA how to map them)")
        sens = dict(computed=False, unmapped=dict(unmapped))
    else:
        a1, a2 = aggregate_rcrps(w, cap1s), aggregate_rcrps(w, cap2s)
        sens = dict(computed=True, aggregate_R1=a1, aggregate_R2=a2, r_CiK_R2=a2 / CIK_SYSTEM,
                    r_CiK_R1=a1 / CIK_SYSTEM, r_BNP_R2=a2 / BNP_SYSTEM, r_BNP_R1=a1 / BNP_SYSTEM,
                    n_recomputed=int(sum(r_["recomputed"] for r_ in sens_rows)),
                    r1_degenerate=int(sum(r_.get("r1_degenerate", 0) for r_ in sens_rows)), r2_tally=ts_sens.as_dict())
    write_csv(OUT / "cik_anchor_seeds.csv", seed_df)
    write_csv(OUT / "cik_sens_freq.csv", pd.DataFrame(sens_rows) if sens_rows else pd.DataFrame(columns=["row"]))
    write_json(OUT / "cik_descriptive.json", dict(anchor_seed_distribution=seeds_desc, freq_table_sensitivity=sens,
                                                  label="descriptive; does not change V1, K, N_comb [criteria §5.9] [criteria §5.10]"))
    log(f"anchor seed distribution (21 runs, descriptive): median {seeds_desc['median']!r} 5%-95% "
        f"[{seeds_desc['p05']!r}, {seeds_desc['p95']!r}]")
    if sens.get("computed"):
        log(f"-1 -> frequency-table sensitivity (descriptive): r_CiK(R2) {sens['r_CiK_R2']!r}  "
            f"r_BNP(R2) {sens['r_BNP_R2']!r}")
    return 0


# ----------------------------------------------------------------------------------------------------------------------
# n2f -- the formal N2F Electricity run [criteria §5.6]
# ----------------------------------------------------------------------------------------------------------------------
def cmd_n2f(a) -> int:
    header("n2f", strict_env=True)
    ensure_absent([OUT / n for n in N2F_OUTPUTS])
    selftests_must_pass()
    sha = verify_pinned(a.json, N2F_JSON_PIN)
    wins, fails = parse_n2f(a.json)
    log(f"N2F structure gate [criteria §5.6]: windows {len(wins)}, failures {len(fails)}")
    if fails:
        for f_ in fails[:20]:
            log(f"N2F STOP item: {f_}")
        write_json(OUT / "n2f_summary.json", dict(status="STRUCTURE_GATE_FAILED", gate_failures=fails))
        raise Stop(2, "N2F structure gate failed [criteria §5.6] [criteria §9]")
    tp = R2Tally("N2F R2 primary (season_length 24)", hard=True)
    tn = R2Tally("N2F R2 sensitivity (native period 48)", hard=False)
    m2 = min(N2F_M, R2_CAP)
    wrows, frows, p1, p2, pn = [], [], [], [], []
    t0 = time.time()
    for w_ in wins:
        r2 = r2_forecast(w_["hist"], N2F_LEN, N2F_M, m2, tp)       # history = the 48 window points [criteria §5.6]
        r1, me = snaive(w_["hist"], N2F_LEN, N2F_M)
        p1.append((w_["truth"], r1))
        p2.append((w_["truth"], r2["point"]))
        wrows.append(dict(window=w_["idx"], region=w_["region"], m_r1_eff=me, r2_mode=r2["mode"],
                          **{f"r2_{k}": r2["stat"][k] for k in MODEL_ORDER},
                          sse_r1=float(np.sum((w_["truth"] - r1) ** 2)),
                          sse_r2=float(np.sum((w_["truth"] - r2["point"]) ** 2))))
        for h in range(N2F_LEN):
            frows.append(dict(window=w_["idx"], h=h + 1, y=w_["truth"][h], r1=r1[h], r2=r2["point"][h],
                              ets=r2["comp"]["ETS"][h], theta=r2["comp"]["Theta"][h], arima=r2["comp"]["ARIMA"][h]))
    tp.final_check()
    log(tp.line() + f" | {time.time() - t0:.0f} s")
    for w_ in wins:                                                 # [criteria §5.10] R2 with the native period
        rn = r2_forecast(w_["hist"], N2F_LEN, N2F_M, N2F_M, tn)
        pn.append((w_["truth"], rn["point"]))
    tn.final_check()
    log(tn.line())
    rm1, rm2, rmn = pooled_rmse(p1), pooled_rmse(p2), pooled_rmse(pn)
    if not (np.isfinite(rm1) and np.isfinite(rm2)):                 # never let a NaN reach summary
        raise Stop(5, "non-finite N2F R1/R2 RMSE -- stopping before writing any N2F output")
    rr = dict(R2=rm2 / N2F_SYSTEM, R1=rm1 / N2F_SYSTEM, R2_native48=rmn / N2F_SYSTEM)
    summ = dict(status="OK", script=SCRIPT_VERSION, json_sha256=sha, n_windows=len(wins), n_points=len(wins) * N2F_LEN,
                rmse=dict(R1=rm1, R2=rm2, R2_native48=rmn), system_value=N2F_SYSTEM, r=rr,
                flags=p_flags(rr["R2"]), v1="protocol not verified (5.5), descriptive only", r2_tally=tp.as_dict(),
                r2_tally_native48=tn.as_dict(), regions=dict(Counter(w_["region"] for w_ in wins)))
    write_csv(OUT / "n2f_windows.csv", pd.DataFrame(wrows))
    write_csv(OUT / "n2f_forecasts.csv", pd.DataFrame(frows))
    write_json(OUT / "n2f_summary.json", summ)
    txt = [f"N2F Electricity (protocol not verified, descriptive) -- {SCRIPT_VERSION}",
           f"windows {len(wins)}, points {len(wins) * N2F_LEN}; pooled RMSE (unrounded): R1 {rm1!r}  R2 {rm2!r}",
           f"r(R2) = {rr['R2']!r}  (P1 {p_flags(rr['R2'])['P1']}, P2 {p_flags(rr['R2'])['P2']}; not counted)  "
           f"r(R1) = {rr['R1']!r}",
           f"sensitivity [criteria §5.10] R2 native period 48: RMSE {rmn!r}  r {rr['R2_native48']!r}",
           tp.line(), tn.line()]
    write_text(OUT / "n2f_summary.txt", "\n".join(txt) + "\n")
    for ln in txt:
        log(ln)
    return 0


# ----------------------------------------------------------------------------------------------------------------------
# nexus -- R3 read-out [criteria §5.4]
# ----------------------------------------------------------------------------------------------------------------------
def cmd_nexus(a) -> int:
    header("nexus", strict_env=False)
    ensure_absent([OUT / n for n in NEXUS_OUTPUTS])
    main = nexus_r3(NEXUS_MAIN)
    rmse = nexus_r3(NEXUS_RMSE)
    if any(v != "Nexus (Gemini-3.1-Pro)" for v in main["system_version"]):
        log("NOTE: not every column's smaller Nexus value is the Gemini version (criteria 5.4 text says all six are)")
    res = dict(script=SCRIPT_VERSION, v1="passed (class A, decided in 5.4, not re-decided later)", control="R3 best single pool model",
               metric="Weather MAE, other five columns MAPE % [criteria §5.4]", columns=list(NEXUS_COLS),
               main=main, flags=p_flags(main["r"]), rmse_descriptive=rmse,
               note="RMSE descriptive only [criteria §5.4]; per-column best descriptive only [criteria §5.4] [criteria §5.10]")
    write_json(OUT / "nexus_r3.json", res)
    rows = []
    for j, c in enumerate(NEXUS_COLS):
        rows.append(dict(column=c, system_value=main["system_values"][j], system_version=main["system_version"][j],
                         **{f"{m}": NEXUS_MAIN[m][j] for m in NEXUS_POOL},
                         **{f"ratio_{m}": NEXUS_MAIN[m][j] / main["system_values"][j] for m in NEXUS_POOL}))
    write_csv(OUT / "nexus_r3.csv", pd.DataFrame(rows))
    txt = [f"Nexus R3 read-out [criteria §5.4] -- {SCRIPT_VERSION}",
           "geometric mean of model / system over 6 columns: " +
           "  ".join(f"{m} {main['geomean_by_model'][m]!r}" for m in NEXUS_POOL),
           f"best single model: {main['best_model']} -> r = {main['r']!r}  P1 (>1.221): {p_flags(main['r'])['P1']}  "
           f"P2 (>1.10): {p_flags(main['r'])['P2']}",
           f"sensitivity, per-column best pool model (descriptive): r = {main['r_sens_per_column_best']!r} "
           f"({main['sens_per_column_best_model']})",
           f"RMSE columns, same rule (descriptive): best {rmse['best_model']} r = {rmse['r']!r}"]
    write_text(OUT / "nexus_r3.txt", "\n".join(txt) + "\n")
    for ln in txt:
        log(ln)
    return 0


# ----------------------------------------------------------------------------------------------------------------------
# compevo-check -- the 7 conditions of [criteria §5.7], mechanically and conservatively
# ----------------------------------------------------------------------------------------------------------------------
GH_REPO = "Aliiina-z/CompEvo"
GH_API = "https://api.github.com/repos/" + GH_REPO
GH_RAW = "https://raw.githubusercontent.com/" + GH_REPO
UA = "research-client"
TEXT_EXT = {".py", ".ipynb", ".sh", ".bash", ".yaml", ".yml", ".json", ".cfg", ".toml", ".ini", ".r", ".md", ".txt",
            ".rst"}
SCAN_EXT = {".py", ".ipynb", ".sh", ".bash", ".yaml", ".yml", ".json", ".cfg", ".toml", ".ini", ".r"}
DATA_EXT = {".csv", ".tsv", ".parquet", ".npy"}
TEXT_MAX, DATA_MAX = 5 * 2 ** 20, 500 * 2 ** 20
ELEC_KEYS = ("elec", "load", "aemo", "demand", "power", "aulf", "energy", "vic")
NAMES_L = (r"seq_len|seq_length|lookback|look_back|lookback_len|lookback_length|lookback_window|input_len|"
           r"input_length|context_len|context_length|history_len|history_length|hist_len|window_len|window_length")
NAMES_TEST = (r"test_start|test_end|test_begin|test_start_date|test_end_date|test_size|test_ratio|test_len|"
              r"test_length|n_test|num_test|test_num|test_split|test_days|test_points|test_windows|n_test_windows")
NAMES_STRIDE = r"stride|window_stride|test_stride|eval_stride|step_size|slide_step|sliding_step|roll_step|rolling_step"
NAMES_H = (r"pred_len|pred_length|prediction_length|horizon|forecast_horizon|output_len|output_length|forecast_len|"
           r"forecast_length|n_ahead|steps_ahead|pred_steps")
NAMES_TGT = r"target|target_col|target_column|target_name|target_var|target_variable"
NUMV = r"(-?\d+(?:\.\d+)?)"
DATEV = r"([0-9]{4}-[0-9]{2}-[0-9]{2}[^\"',\n]{0,12}|-?\d+(?:\.\d+)?)"


def _http(url: str, timeout: int = 60) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/vnd.github+json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


class LocalSaveError(Exception):
    """The local file could not be created (name / length / case clash), as opposed to a network error."""


def _safe_name(path: str) -> str:
    return re.sub(r'[<>:"|?*\\]', "_", path.replace("/", "__"))


def _download(url: str, dest: Path, cap: int) -> int:
    try:
        f = open(dest, "xb")
    except OSError as exc:
        raise LocalSaveError(f"{type(exc).__name__}: {exc}") from exc
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    n = 0
    with f, urllib.request.urlopen(req, timeout=180) as r:
        while True:
            chunk = r.read(1 << 20)
            if not chunk:
                break
            n += len(chunk)
            if n > cap:
                raise ValueError("size cap exceeded")
            f.write(chunk)
    return n


def _scan(texts, names: str, value: str):
    pats = [re.compile(rf"(?i)[\"']?\b({names})\b[\"']?\s*[:=]\s*[\"']?{value}"),
            re.compile(rf"(?i)--({names})\b[^\n]{{0,160}}?default\s*=\s*[\"']?{value}"),
            re.compile(rf"(?i)--({names})(?:\s+|=){value}")]
    hits = []
    for fname, text in texts:
        for ln, line in enumerate(text.splitlines(), 1):
            for p in pats:
                for mm in p.finditer(line):
                    hits.append((fname, ln, mm.group(1).lower(), mm.group(2).strip(), line.strip()[:200]))
    return hits


def _norm_num(s: str):
    try:
        v = float(s)
        return int(v) if v.is_integer() else v
    except ValueError:
        return s


def cmd_compevo_check(a) -> int:
    """[criteria §5.7] text-only reading of the repository at the head of its default branch on the day of execution.
    Each condition is operationalised mechanically (NOT IN CRITERIA: the regexes / file rules below); anything not
    mechanically certain counts as NOT met ("unclear means not met"). Any condition not met -> "window or data
    undetermined", nothing is computed. If all seven were met the script still computes nothing and stops (the
    "matches" branch is not pre-implemented)."""
    header("compevo-check", strict_env=False)
    ensure_absent([OUT / n for n in COMPEVO_OUTPUTS])
    rec = dict(repo=f"github.com/{GH_REPO}", fetched_at=time.strftime("%Y-%m-%d %H:%M:%S %z"),
               method="mechanical decision (regexes and file rules; operationalisation NOT IN CRITERIA); condition 2 reads only the repository README, the paper is not used (the paper gives no L)")
    crit = {}

    def net_fail(msg: str):
        """A network failure is recorded in a time-stamped file (a retry stays possible) and `summary`
        then reports CompEvo as "undetermined (network)" ([criteria §5.7] default; [criteria §9] data not obtainable)."""
        write_json(OUT / f"compevo_check_network_fail_{RUN_TS}.json",
                   dict(rec, status="undetermined (network)", reason=msg))
        raise Stop(4, msg + " -- recorded as undetermined (network); one retry allowed, then continue")

    try:
        meta = json.loads(_http(GH_API).decode("utf-8"))
    except urllib.error.HTTPError as exc:
        if exc.code == 404:                                          # repository not available -> data not available
            rec.update(status="undetermined", reason="repository not available (HTTP 404)", criteria={
                str(i): dict(met=False, reason="repository not available") for i in range(1, 8)})
            write_json(OUT / "compevo_check.json", rec)
            write_text(OUT / "compevo_check.txt", "CompEvo: repository not available (HTTP 404) -> window or data undetermined; nothing is computed\n")
            write_csv(OUT / "compevo_tree.csv", pd.DataFrame(columns=["path"]))
            write_text(OUT / "compevo_evidence.txt", "(no repository)\n")
            log("CompEvo VERDICT: window or data undetermined (repository 404)")
            return 0
        net_fail(f"GitHub API error {exc.code}: {exc}")
    except Exception as exc:  # noqa: BLE001
        net_fail(f"network error {type(exc).__name__}: {exc}")
    branch = meta.get("default_branch", "")
    try:
        c1 = json.loads(_http(f"{GH_API}/commits/{urllib.parse.quote(branch)}").decode("utf-8"))
        sha = c1["sha"]
        tree = json.loads(_http(f"{GH_API}/git/trees/{sha}?recursive=1").decode("utf-8"))
    except Exception as exc:  # noqa: BLE001
        net_fail(f"could not read commit / tree: {type(exc).__name__}: {exc}")
    rec.update(default_branch=branch, commit=sha, commit_date=c1.get("commit", {}).get("committer", {}).get("date"),
               license=(meta.get("license") or {}).get("spdx_id"), tree_truncated=bool(tree.get("truncated")))
    log(f"CompEvo head of default branch '{branch}': {sha} ({rec['commit_date']}); tree truncated {rec['tree_truncated']}")
    dest = Path(a.ext_root) / f"compevo_{sha[:7]}"
    if dest.exists():
        raise Stop(12, f"{dest} already exists; downloads go to a new empty folder only")
    (dest / "code_text").mkdir(parents=True)
    (dest / "data").mkdir(parents=True)
    trows, texts, readmes, data_files = [], [], [], []
    dl_fail = Counter()                                              # network vs local-save failures

    def fail_kind(exc) -> str:
        return "local" if isinstance(exc, LocalSaveError) else "network"

    for it in tree.get("tree", []):
        if it.get("type") != "blob":
            continue
        path, size = it["path"], int(it.get("size", 0))
        ext = Path(path).suffix.lower()
        base = Path(path).name.lower()
        low = path.lower()
        cat, local, status = "other", "", "listed"
        url = f"{GH_RAW}/{sha}/{urllib.parse.quote(path)}"
        if ext in TEXT_EXT or base.startswith("readme"):
            cat = "text"
            if size <= TEXT_MAX:
                local = dest / "code_text" / (_safe_name(path) + ".txt")   # code saved as .txt, never run
                try:
                    _download(url, local, TEXT_MAX)
                    status = "downloaded"
                    txt = local.read_text(encoding="utf-8", errors="replace")
                    if base.startswith("readme"):
                        readmes.append((path, txt))
                    elif ext in SCAN_EXT:
                        texts.append((path, txt))
                except Exception as exc:  # noqa: BLE001
                    status = f"{fail_kind(exc)} failure: {type(exc).__name__}"
                    dl_fail[fail_kind(exc)] += 1
            else:
                status = "too large for text, listed only"
        elif ext in DATA_EXT and any(k in low for k in ELEC_KEYS):
            cat = "data_candidate"
            if size <= DATA_MAX:
                local = dest / "data" / _safe_name(path)
                try:
                    _download(url, local, DATA_MAX)
                    status = "downloaded"
                    data_files.append((path, local))
                except Exception as exc:  # noqa: BLE001
                    status = f"{fail_kind(exc)} failure: {type(exc).__name__}"
                    dl_fail[fail_kind(exc)] += 1
            else:
                status = "too large, listed only"
        elif ext in DATA_EXT or ext in {".pkl", ".pickle", ".pt", ".pth", ".h5", ".hdf5", ".npz", ".xlsx", ".xls",
                                         ".feather", ".zip", ".gz", ".tar", ".7z"}:
            cat = "data_other"
        trows.append(dict(path=path, size=size, category=cat, status=status, local=str(local),
                          sha256=(sha256_file(Path(local)) if status == "downloaded" else "")))
    log(f"tree blobs {len(trows)}; text scanned {len(texts)}; READMEs {len(readmes)}; electricity data candidates "
        f"downloaded {len(data_files)}; failures network {dl_fail['network']} / local save {dl_fail['local']}")
    ev = []

    def evid(tag, hits):
        for h in hits[:60]:
            ev.append(f"[{tag}] {h[0]}:{h[1]}: {h[4]}")

    # Condition 1: data with exactly 52,560 points, 19 variables, region VIC
    cands = []
    for path, local in data_files:
        info = dict(path=path)
        try:
            head = Path(local).read_bytes()[:200]
            if head.startswith(b"version https://git-lfs"):
                info.update(ok=False, why="git-lfs pointer, data not in repository")
                cands.append(info)
                continue
            ext = Path(local).suffix.lower()
            if ext == ".npy":
                arr = np.load(local, allow_pickle=False)
                pts = int(arr.shape[0]) if arr.ndim >= 1 else 0
                nv = int(arr.shape[1]) if arr.ndim == 2 else (1 if arr.ndim == 1 else -1)
                reg = bool(re.search(r"(?i)(^|[^a-z])vic([^a-z]|$)", path))
            else:
                df = pd.read_parquet(local) if ext == ".parquet" else pd.read_csv(local, sep="\t" if ext == ".tsv"
                                                                                    else ",")
                rcol = [c for c in df.columns if str(c).strip().lower() in ("state", "region", "regionid",
                                                                              "region_id", "area", "zone")]
                if rcol:
                    sub = df[df[rcol[0]].astype(str).str.strip().str.upper().isin(["VIC", "VIC1"])]
                    reg = len(sub) > 0
                else:
                    sub = df
                    reg = bool(re.search(r"(?i)(^|[^a-z])vic([^a-z]|$)", path))
                pts = int(len(sub))
                nv = int(sum(1 for c in sub.columns if c not in rcol and not str(c).startswith("Unnamed")
                             and (pd.api.types.is_numeric_dtype(sub[c]) or pd.api.types.is_bool_dtype(sub[c]))))
            info.update(points=pts, variables=nv, region_vic=reg, ok=bool(pts == 52560 and nv == 19 and reg))
        except Exception as exc:  # noqa: BLE001
            info.update(ok=False, why=f"not readable as data: {type(exc).__name__}")
        cands.append(info)
    good = [c for c in cands if c.get("ok")]
    crit["1"] = dict(met=len(good) == 1, candidates=cands,
                     reason=("exactly one file with 52,560 points, 19 numeric variables, VIC" if len(good) == 1 else
                             f"{len(good)} qualifying file(s) among {len(cands)} electricity data candidate(s)"))
    # Condition 2: look-back L unique (code / config; README decides between several values)
    hl = _scan(texts, NAMES_L, NUMV)
    evid("L", hl)
    lv = sorted({_norm_num(h[3]) for h in hl}, key=str)
    if len(lv) == 1:
        crit["2"] = dict(met=True, values=lv, reason="one value in scripts/configs")
    elif len(lv) > 1:
        hr = _scan(readmes, NAMES_L, NUMV)
        rv = sorted({_norm_num(h[3]) for h in hr}, key=str)
        evid("L-README", hr)
        ok2 = len(rv) == 1 and rv[0] in lv
        crit["2"] = dict(met=ok2, values=lv, readme_values=rv,
                         reason="README names one of the values" if ok2 else "several values, README does not single one out")
    else:
        crit["2"] = dict(met=False, values=[], reason="no look-back setting found")
    # Condition 3: test segment / windows unique, including the stride
    ht = _scan(texts, NAMES_TEST, DATEV)
    hs = _scan(texts, NAMES_STRIDE, NUMV)
    evid("test", ht)
    evid("stride", hs)
    per = {}
    for h in ht:
        per.setdefault(h[2], set()).add(str(_norm_num(h[3])))
    sv = sorted({str(_norm_num(h[3])) for h in hs})
    ok3 = bool(per) and all(len(v) == 1 for v in per.values()) and len(sv) == 1
    crit["3"] = dict(met=ok3, test_settings={k: sorted(v) for k, v in per.items()}, stride_values=sv,
                     reason="each test-split setting and the stride have one value" if ok3 else
                     "test split and/or stride missing or not unique")
    # Condition 4: target column unique
    tg_pats = [re.compile(rf"(?i)[\"']?\b({NAMES_TGT})\b[\"']?\s*[:=]\s*[\"']([^\"'\n]{{1,80}})[\"']"),
               re.compile(rf"(?i)--({NAMES_TGT})\b[^\n]{{0,160}}?default\s*=\s*[\"']([^\"'\n]{{1,80}})[\"']")]
    htg = []
    for fname, text in texts:
        for ln, line in enumerate(text.splitlines(), 1):
            for p in tg_pats:
                for mm in p.finditer(line):
                    htg.append((fname, ln, mm.group(1).lower(), mm.group(2).strip(), line.strip()[:200]))
    evid("target", htg)
    tv = sorted({h[3] for h in htg})
    crit["4"] = dict(met=len(tv) == 1, values=tv, reason="one target name" if len(tv) == 1 else
                     f"{len(tv)} distinct target settings")
    # Condition 5: prediction length 48
    hh = _scan(texts, NAMES_H, NUMV)
    evid("horizon", hh)
    hv = sorted({_norm_num(h[3]) for h in hh}, key=str)
    crit["5"] = dict(met=(hv == [48]), values=hv, reason="all horizon settings are 48" if hv == [48] else
                     "horizon setting missing or not uniquely 48")
    # Condition 6: error computed on the original scale
    rx_s = re.compile(r"(?i)(StandardScaler|MinMaxScaler|RobustScaler|normaliz|standardiz|z_?score|\bscaler\b)")
    rx_i = re.compile(r"(?i)(inverse_transform|denormaliz|de_normaliz|inverse_normaliz|unnormaliz|unscale)")
    rx_m = re.compile(r"(?i)(rmse|mean_squared_error|\bmse\b)")
    hs6 = [(f, i, "", "", l.strip()[:200]) for f, t in texts for i, l in enumerate(t.splitlines(), 1) if rx_s.search(l)]
    hi6 = [(f, i, "", "", l.strip()[:200]) for f, t in texts for i, l in enumerate(t.splitlines(), 1) if rx_i.search(l)]
    hm6 = [(f, i, "", "", l.strip()[:200]) for f, t in texts for i, l in enumerate(t.splitlines(), 1) if rx_m.search(l)]
    evid("scaling", hs6)
    evid("inverse", hi6)
    evid("metric", hm6)
    # conservative: "original scale" only if an error metric is computed and NO scaler / normalisation
    # appears anywhere; any scaler (with or without an inverse_transform somewhere) counts as "unclear" -> not met.
    ok6 = bool(hm6) and not hs6
    crit["6"] = dict(met=ok6, n_scaling=len(hs6), n_inverse=len(hi6), n_metric=len(hm6),
                     reason="metric found and no scaler / normalisation anywhere" if ok6 else
                     ("no error metric found" if not hm6 else
                      "a scaler / normalisation appears; scale of the error not mechanically certain"))
    # Condition 7: everything from one recorded commit
    try:
        sha2 = json.loads(_http(f"{GH_API}/commits/{urllib.parse.quote(branch)}").decode("utf-8"))["sha"]
    except Exception as exc:  # noqa: BLE001
        sha2 = f"re-check failed: {type(exc).__name__}"
    ok7 = sha2 == sha and not rec["tree_truncated"] and sum(dl_fail.values()) == 0
    why7 = []
    if sha2 != sha:
        why7.append(f"head moved or re-check failed ({sha2})")
    if rec["tree_truncated"]:
        why7.append("tree truncated")
    if dl_fail["network"]:
        why7.append(f"{dl_fail['network']} network download failure(s)")
    if dl_fail["local"]:
        why7.append(f"{dl_fail['local']} local save failure(s)")
    crit["7"] = dict(met=ok7, commit=sha, commit_recheck=sha2, download_failures=dict(dl_fail),
                     reason="all files from the recorded commit" if ok7 else "; ".join(why7))
    all_met = all(c["met"] for c in crit.values())
    rec.update(criteria=crit, download_folder=str(dest),
               status=("all 7 mechanical conditions met: stop and report (the 5.7 'matches' branch is not pre-implemented in ur_c.py)"
                       if all_met else "undetermined"),
               reason=("" if all_met else "not met: " + ", ".join(k for k, c in crit.items() if not c["met"])))
    write_json(OUT / "compevo_check.json", rec)
    write_csv(OUT / "compevo_tree.csv", pd.DataFrame(trows) if trows else pd.DataFrame(columns=["path"]))
    write_text(OUT / "compevo_evidence.txt", "\n".join(ev) + "\n")
    lines = [f"CompEvo [criteria §5.7] at {sha} ({branch}, {rec['commit_date']})",
             "decision method: mechanical (regexes and file rules); condition 2 reads only the repository README, the paper is not used (5.7-2 allows the README or the paper; "
             "the paper gives no L). Any later judgement of the evidence must be labelled 'post hoc'."]
    for k in sorted(crit):
        lines.append(f"  condition {k}: {'met' if crit[k]['met'] else 'NOT met'} -- {crit[k]['reason']}")
    lines.append(f"VERDICT: {rec['status']} {rec['reason']}")
    write_text(OUT / "compevo_check.txt", "\n".join(lines) + "\n")
    for ln in lines:
        log(ln)
    return 0 if not all_met else 2


# ----------------------------------------------------------------------------------------------------------------------
# summary [criteria §7] [criteria §8] [criteria §10]
# ----------------------------------------------------------------------------------------------------------------------
def _truthy(x) -> bool:
    return str(x).strip().lower() == "true"


def counts_and_tiers(rs: list, n: int) -> dict:
    if len(rs) != n or not all(isinstance(r, (int, float)) and np.isfinite(r) for r in rs):
        raise Stop(14, f"count input not {n} finite ratios: {rs} -- a NaN must never be counted")
    c = [int(sum(1 for r in rs if r <= t)) for t in THRESHOLDS]           # [criteria_round1 §6] [criteria §5.12] unrounded
    tiers = [tier(n, k) for k in c]
    return dict(N=n, ceil_half=math.ceil(n / 2), floor_quarter=math.floor(n / 4), counts=c, tiers=tiers,
                overall=overall_tier(tiers))


def cmd_summary(a) -> int:
    header("summary", strict_env=False)
    ensure_absent([OUT / n for n in SUMMARY_OUTPUTS])
    need = [OUT / "cik_primary.json", OUT / "n2f_summary.json", OUT / "nexus_r3.json"]
    miss = [str(p) for p in need if not p.exists()]
    if miss:
        raise Stop(14, "missing inputs (run the earlier steps first): " + "; ".join(miss))

    def load_checked(p: Path) -> dict:
        rel = str(p.relative_to(OUT))
        log(f"input {rel}")
        return json.loads(p.read_text(encoding="utf-8"))

    cik = load_checked(OUT / "cik_primary.json")
    desc = load_checked(OUT / "cik_descriptive.json") if (OUT / "cik_descriptive.json").exists() else {}
    if cik.get("status") == "OK" and not desc:
        raise Stop(14, "cik_descriptive.json missing although the CiK run finished its primary part -- report")
    n2f = load_checked(OUT / "n2f_summary.json")
    nex = load_checked(OUT / "nexus_r3.json")
    if (OUT / "compevo_check.json").exists():
        cev = load_checked(OUT / "compevo_check.json")
    else:
        nf = sorted(OUT.glob("compevo_check_network_fail_*.json"))
        if not nf:
            raise Stop(14, "neither compevo_check.json nor a compevo_check_network_fail_*.json record: run compevo-check first")
        recs = [load_checked(p) for p in nf]
        cev = dict(status="undetermined (network)",
                   reason=f"repository check not completed because of network failures ({len(nf)} attempt(s), last: {recs[-1].get('reason', '')[:160]}); "
                          f"treated as the 5.7 default, section 9 data not obtainable")
    for p in (UR_B_SUMMARY, RESULTS_A):
        if not p.exists():
            raise Stop(14, f"prior-round input not found: {p}")
    ub = pd.read_csv(UR_B_SUMMARY)
    bpass = {str(r["system"]): float(r["r_system"]) for _, r in ub.iterrows() if _truthy(r["v1_pass"])}
    if tuple(sorted(bpass)) != tuple(sorted(B_PASSING_EXPECTED)):
        raise Stop(14, f"ur_b_summary.csv V1 passers {sorted(bpass)} differ from {B_PASSING_EXPECTED}")
    txt_a = RESULTS_A.read_text(encoding="utf-8", errors="replace")
    orig = {}
    for s, (lit, num, den) in A_READINGS.items():
        if lit not in txt_a:
            raise Stop(14, f"{RESULTS_A.name} does not contain the reading '{lit}' for {s}")
        orig[s] = num / den
    orig.update(bpass)
    orig_excl = {k: v for k, v in orig.items() if k != "LSTPrompt"}
    ci8, ci7 = counts_and_tiers(list(orig.values()), 8), counts_and_tiers(list(orig_excl.values()), 7)
    chk = tuple(ci8["counts"]) == ORIG_COUNTS_EXPECTED["incl"] and tuple(ci7["counts"]) == ORIG_COUNTS_EXPECTED["excl"]
    log(f"original re-check reproduced: N=8 counts {ci8['counts']} {ci8['tiers']}; N=7 counts {ci7['counts']} "
        f"{ci7['tiers']} -> {'matches' if chk else 'DOES NOT MATCH'} the phase A+B reading")
    if not chk:
        raise Stop(14, "original counts do not reproduce the accepted reading -- report")

    # ---- per-system status [criteria §10] --------------------------------------------------------------------------------
    sysrows = []
    cik_ok = cik.get("status") == "OK"
    if cik_ok:
        r_cik, r_bnp = cik["r"]["CiK_R2"], cik["r"]["BNP_R2"]
        v1_cik = bool(cik["v1_pass"])
        sysrows.append(dict(id="S07", system="CiK", status=cik["cik_status"], control="R2", metric="RCRPS",
                            system_value="0.159 (Direct Prompt (ours), Llama-3.1-405B-Inst, Table 1/3)",
                            control_value=cik["aggregate_rcrps"]["R2"], r=r_cik, r_R1=cik["r"]["CiK_R1"],
                            v1=("passed" if v1_cik else "not passed") + f" (Exp-Smoothing {cik['aggregate_rcrps']['anchor']:.4f}"
                               f" vs 0.605, rel {cik['anchor_rel_dev']:+.4f}"
                               + ("" if cik["magnitude_gate_ok"] else "; magnitude gate failed") + ")",
                            counted=v1_cik, known=KNOWN_BEFORE_CRITERIA["CiK"], **p_flags(r_cik)))
        sysrows.append(dict(id="S21", system="BNP", status=cik["bnp_status"], control="R2", metric="RCRPS",
                            system_value="0.110 (SampleWise-CorDP(Chronos Large), Claude-Sonnet-4.5 / Gemini-2.5-Pro tied)",
                            control_value=cik["aggregate_rcrps"]["R2"], r=r_bnp, r_R1=cik["r"]["BNP_R1"],
                            v1="protocol not verified (5.8)", counted=False, known=KNOWN_BEFORE_CRITERIA["BNP"], **p_flags(r_bnp)))
    else:
        v1_cik, r_cik, r_bnp = False, float("nan"), float("nan")
        for sid, s in (("S07", "CiK"), ("S21", "BNP")):
            sysrows.append(dict(id=sid, system=s, status="structure gate failed, stopped (section 9)", control="R2", metric="RCRPS",
                                system_value="", control_value=float("nan"), r=float("nan"), r_R1=float("nan"),
                                v1="-", counted=False, known=KNOWN_BEFORE_CRITERIA[s], **p_flags(float("nan"))))
    r_nex = float(nex["main"]["r"])
    sysrows.append(dict(id="S10", system="Nexus", status="counted (V1 class A already passed, 5.4)", control="R3",
                        metric="Weather MAE + 5 MAPE columns (geometric mean)",
                        system_value="per column the smaller of the two Nexus versions (Table 1)",
                        control_value=f"best single model {nex['main']['best_model']}", r=r_nex, r_R1=float("nan"),
                        v1="passed (class A)", counted=True, known=KNOWN_BEFORE_CRITERIA["Nexus"], **p_flags(r_nex)))
    n2f_ok = n2f.get("status") == "OK"
    r_n2f = float(n2f["r"]["R2"]) if n2f_ok else float("nan")
    sysrows.append(dict(id="S11", system="N2F", status=("protocol not verified (5.5), Electricity descriptive only" if n2f_ok else
                                                          "structure gate failed, stopped (section 9)"),
                        control="R2", metric="RMSE (original scale, 4,800 points pooled)", system_value="280.39 (Table 1 Filtered News)",
                        control_value=(n2f["rmse"]["R2"] if n2f_ok else float("nan")), r=r_n2f,
                        r_R1=(float(n2f["r"]["R1"]) if n2f_ok else float("nan")), v1="protocol not verified", counted=False,
                        known=KNOWN_BEFORE_CRITERIA["N2F"], **p_flags(r_n2f)))
    ce_undet = str(cev.get("status", "")).startswith("undetermined")
    ce_status = ("window or data undetermined" + (" (network)" if "network" in str(cev.get("status")) else "")) if ce_undet else \
        str(cev.get("status"))
    sysrows.append(dict(id="S16", system="CompEvo", status=f"{ce_status} ({cev.get('reason', '')})", control="(R2)",
                        metric="RMSE", system_value="354.18 (used only if the 5.7 conditions hold)", control_value=float("nan"),
                        r=float("nan"), r_R1=float("nan"), v1="- (5.7)", counted=False,
                        known=KNOWN_BEFORE_CRITERIA["CompEvo"], **p_flags(float("nan"))))
    # ---- section 7 [criteria §7.2] -----------------------------------------------------------------------------------------
    passers = {r_["system"]: r_["r"] for r_ in sysrows if r_["counted"]}     # all five arms are tier S [criteria §3]
    if any(not np.isfinite(v) for v in passers.values()):
        raise Stop(14, f"a counted system has a non-finite r: {passers} -- report, nothing is counted")
    k_ = len(passers)
    a_ = sum(1 for v in passers.values() if v > P1)
    b_ = sum(1 for v in passers.values() if v > P2)
    v72 = verdict_72(k_, a_, b_)
    # ---- section 8 [criteria §8] -------------------------------------------------------------------------------------------
    comb_incl = list(orig.values()) + list(passers.values())
    comb_excl = list(orig_excl.values()) + list(passers.values())
    m_incl = counts_and_tiers(comb_incl, 8 + k_)
    m_excl = counts_and_tiers(comb_excl, 7 + k_)
    if m_incl["overall"] != "close":
        abstract = f"main calibre (incl. LSTPrompt, N={8 + k_}) has all three thresholds in one tier; the abstract states this tier in one sentence: {m_incl['overall']}"
        if m_excl["overall"] != m_incl["overall"]:
            abstract += f"; the other calibre (excl. LSTPrompt, N={7 + k_}) is {m_excl['overall']}, stated in the same sentence"
    else:
        abstract = "the three thresholds of the main calibre fall in different tiers (close): the abstract adds no combined reading; the main reading N=8 'close' stands"
    # ---- 7.3 descriptive [criteria §7.3] -----------------------------------------------------------------------------------
    sn = None
    if cik_ok:
        sn = min((("CiK", r_cik), ("BNP", r_bnp)), key=lambda t: t[1])
    all_new_r = {r_["system"]: r_["r"] for r_ in sysrows if np.isfinite(r_["r"])}
    gt1405_pass = sorted(s for s, v in passers.items() if v > LST_ANCHOR_R)
    gt1405_all = sorted(s for s, v in all_new_r.items() if v > LST_ANCHOR_R)
    sq = {s: math.sqrt(orig[s]) for s in SQUARED_METRIC_ORIG}
    orig_sq = {s: (sq[s] if s in sq else v) for s, v in orig.items()}
    sq8 = counts_and_tiers(list(orig_sq.values()), 8)
    sq7 = counts_and_tiers([v for s, v in orig_sq.items() if s != "LSTPrompt"], 7)

    L = ["Supplementary re-check (5 systems), mechanical summary -- " + SCRIPT_VERSION,
         "all decisions use unrounded values (5.12); three decimals below are for display only", "",
         "== Per-system status (section 10) =="]
    for r_ in sysrows:
        L.append(f"{r_['id']} {r_['system']}: {r_['status']} | control {r_['control']} | main metric {r_['metric']} | "
                 f"system value {r_['system_value']} | control value {r_['control_value'] if isinstance(r_['control_value'], str) else fmt(r_['control_value'], 4)}"
                 f" | r {fmt(r_['r'])} (R1 {fmt(r_['r_R1'])}) | V1 {r_['v1']} | expectation 1 (r > 1.221) {r_['P1']}, "
                 f"expectation 2 (r > 1.10) {r_['P2']} | counted (number of counted systems K / systems in the combined "
                 f"reading N_comb) {r_['counted']}")
        L.append(f"     read before the criteria were written: {r_['known']}")
    if cik_ok:
        d = cik["diagnostics"]
        L += ["", "== CiK diagnostics (section 10) ==",
              f"anchor value {cik['aggregate_rcrps']['anchor']!r} (/0.605 = {cik['anchor_ratio']!r}); interface fix (5.9-3): "
              f"{'used' if cik['interface_fix_used'] else 'not used'}",
              f"truncated at 5: anchor {d['truncated_at_5']['anchor']} (paper Table 6 Exp-Smoothing 5), R1 {d['truncated_at_5']['R1']}, "
              f"R2 {d['truncated_at_5']['R2']}; anchor failures (set to 5) {d['anchor_failures']}",
              f"R1 degenerate {d['r1_degenerate']}; R2 failures ETS/Theta/ARIMA {d['r2_tally']['fail_ETS']}/"
              f"{d['r2_tally']['fail_Theta']}/{d['r2_tally']['fail_ARIMA']}, fallbacks median2 {d['r2_tally']['mode_median2']}, "
              f"single {d['r2_tally']['mode_single']}, R1 {d['r2_tally']['allfail_to_R1']}"]
        if desc:
            sd = desc["anchor_seed_distribution"]
            L.append(f"anchor seed distribution (21 runs, descriptive): median {fmt(sd['median'], 4)}, 5%-95% [{fmt(sd['p05'], 4)}, "
                     f"{fmt(sd['p95'], 4)}], within 5% {sd['n_within_5pct']}/21")
    L += ["", "== Section 7 (7.2) ==",
          f"K = {k_} ({', '.join(f'{s} r={fmt(v)}' for s, v in passers.items())}); a (r>1.221) = {a_}; b (r>1.10) = {b_}",
          f"reading: {v72}" + (" (report only the per-system r and whether P1, P2 are met; if met, write only 'meets the threshold ... but is not a test')"
                           if v72 == "insufficient test" else ""),
          "CompEvo not counted; the 'with / without CompEvo' calibres do not apply (5.7)" if ce_undet else
          "CompEvo: see status above (not counted in K)",
          "", "== Section 8: combined reading (secondary, pre-specified) =="]
    for lab, m in (("main calibre (incl. LSTPrompt)", m_incl), ("other calibre (excl. LSTPrompt)", m_excl)):
        L.append(f"{lab}: N_comb = {m['N']}, ceil(N/2) = {m['ceil_half']}, floor(N/4) = {m['floor_quarter']}")
        for t, c, ti in zip(THRESHOLDS, m["counts"], m["tiers"]):
            L.append(f"    r <= {t:.2f}: {c} -> {ti}")
        L.append(f"    three thresholds: {m['overall']}")
    L += [f"abstract rule (section 8): {abstract}", "",
          "== 7.3 descriptive (does not change the 7.2 reading) ==",
          (f"1. ServiceNow combined (CiK and BNP as one unit, smaller r): {sn[0]} r = {fmt(sn[1])}" if sn else
           "1. ServiceNow combined: CiK/BNP have no r (structure gate failed)"),
          f"2. N2F (Electricity) r = {fmt(r_n2f)}, P1 {p_flags(r_n2f)['P1']}, P2 {p_flags(r_n2f)['P2']}; "
          f"BNP r = {fmt(r_bnp)}, P1 {p_flags(r_bnp)['P1']}, P2 {p_flags(r_bnp)['P2']}; both 'protocol not verified, not counted'. "
          f"CompEvo: {ce_status} ({cev.get('reason', '')})",
          f"3. r > 1.405 (criteria wording 'among the new tier-S systems'; all 5 new systems are tier S): literal reading, all new systems with an r: "
          f"{len(gt1405_all)} {gt1405_all} (incl. systems with unverified protocol); supplementary reading, new systems passing V1: "
          f"{len(gt1405_pass)} {gt1405_pass}",
          "4. sensitivity (5.10, descriptive only):"]

    def tally_note(t: dict) -> str:
        return (f"[R2 fallback to R1 {t.get('allfail_to_R1')}/{t.get('calls')}, first-20-all-failed sentinel "
                f"{'tripped' if t.get('sentinel_tripped') else 'not tripped'}, models failing at every call {t.get('every_call_failed')}]")

    if n2f_ok:
        L.append(f"   N2F R2 with native period 48: r = {fmt(n2f['r']['R2_native48'])} "
                 + tally_note(n2f.get("r2_tally_native48", {})))
    if desc:
        fs = desc.get("freq_table_sensitivity", {})
        L.append("   CiK -1 re-assigned by the frequency table: " + (f"r_CiK(R2) = {fmt(fs['r_CiK_R2'])}, r_BNP(R2) = {fmt(fs['r_BNP_R2'])} "
                                          + tally_note(fs.get("r2_tally", {}))
                                          if fs.get("computed") else f"not computed (frequencies outside the table {fs.get('unmapped')})"))
    L.append(f"   Nexus per-column best pool model: r = {fmt(nex['main']['r_sens_per_column_best'])}")
    L.append("   sqrt(r) (post hoc, descriptive; only the squared-error metrics among the original 8 systems: " + ", ".join(
        f"{s} {fmt(orig[s])}->{fmt(sq[s])}" for s in sq) + f"): N=8 counts {sq8['counts']} {sq8['overall']}; "
             f"N=7 counts {sq7['counts']} {sq7['overall']}")
    L += ["", "original 8 systems (from read_values.md and ur_b_summary.csv): " +
          ", ".join(f"{s} {fmt(v)}" for s, v in orig.items())]
    write_text(OUT / "ur_c_summary.txt", "\n".join(L) + "\n")
    write_csv(OUT / "ur_c_status.csv", pd.DataFrame(sysrows))
    write_json(OUT / "ur_c_summary.json", dict(
        script=SCRIPT_VERSION, systems=sysrows, original=orig,
        original_counts=dict(incl=ci8, excl=ci7), section7=dict(K=k_, a=a_, b=b_, verdict=v72, passers=passers),
        section8=dict(incl=m_incl, excl=m_excl, abstract_rule=abstract),
        desc73=dict(servicenow_min=sn, gt1405_passers=gt1405_pass, gt1405_all=gt1405_all,
                    sqrt_r_post_hoc=dict(values=sq, incl=sq8, excl=sq7))))
    for ln in L:
        log(ln)
    return 0


# ----------------------------------------------------------------------------------------------------------------------
def main() -> int:
    global OUT, SMOKE_DIR, LOG_DIR, CIK_LOCK, UR_B_SUMMARY, RESULTS_A
    try:  # never crash on a console code page
        sys.stdout.reconfigure(errors="replace")
    except Exception:  # noqa: BLE001
        pass
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--out-dir", type=Path, default=OUT, help="output folder (default: recheck/round2/out)")
    common.add_argument("--ur-b-summary", type=Path, default=UR_B_SUMMARY,
                        help="phase-B summary (default: recheck/round1/out/ur_b_summary.csv)")
    common.add_argument("--round1-readings", type=Path, default=RESULTS_A,
                        help="phase-A readings (default: recheck/round1/read_values.md)")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("selftest", parents=[common]).set_defaults(fn=cmd_selftest)
    p = sub.add_parser("smoke", parents=[common])
    p.add_argument("--parquet", type=Path, required=True, help="CiK ICML2025-00000-of-00001.parquet")
    p.add_argument("--json", type=Path, required=True, help="N2F AULF_test_data_2021.json")
    p.set_defaults(fn=cmd_smoke)
    p = sub.add_parser("compevo-check", parents=[common])
    p.add_argument("--ext-root", type=Path, required=True,
                   help="root folder for untrusted downloads (a new sub-folder compevo_<commit> is created)")
    p.set_defaults(fn=cmd_compevo_check)
    p = sub.add_parser("cik", parents=[common])
    p.add_argument("--parquet", type=Path, required=True, help="CiK ICML2025-00000-of-00001.parquet")
    p.set_defaults(fn=cmd_cik)
    p = sub.add_parser("n2f", parents=[common])
    p.add_argument("--json", type=Path, required=True, help="N2F AULF_test_data_2021.json")
    p.set_defaults(fn=cmd_n2f)
    sub.add_parser("nexus", parents=[common]).set_defaults(fn=cmd_nexus)
    sub.add_parser("summary", parents=[common]).set_defaults(fn=cmd_summary)
    a = ap.parse_args()
    OUT = a.out_dir.resolve()
    SMOKE_DIR, LOG_DIR, CIK_LOCK = OUT / "smoke", OUT / "logs", OUT / "cik_FIRST_RUN.lock"
    UR_B_SUMMARY, RESULTS_A = a.ur_b_summary.resolve(), a.round1_readings.resolve()
    OUT.mkdir(parents=True, exist_ok=True)
    open_log(a.cmd)
    try:
        rc = a.fn(a)
    except Stop as s:
        log(f"STOP: {s.msg}")
        rc = s.code
    except Exception as exc:  # noqa: BLE001  (unexpected: keep the traceback in the log)
        import traceback
        log("UNEXPECTED ERROR -- full traceback:\n" + traceback.format_exc())
        rc = 99
    finish(a.cmd, rc)
    return rc


if __name__ == "__main__":
    sys.exit(main())
