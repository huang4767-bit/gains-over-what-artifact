"""Weak references on the MemCast test protocol, version 2 of the script. Changes relative to the first version, all decided before running version 2:
  1. --test-stride / --n-test: test windows at t0 = E + test_stride * i (memory windows keep stride 24).
     Reason: on the code protocol (30 consecutive days from E) every naive error is an order of magnitude below
     MemCast's Table 2 on BE/FR; 30 windows spread over the whole test segment (stride 96) matches the paper's error
     scale on all 5 markets (seasonal-naive-1d MSE NP 43 / PJM 40 / BE 558 / FR 783 / DE 448). CastFSR (same first
     author) describes 60 sampled EPF windows with stride 48, which also spans the test segment.
  2. SameInfo: a same-information linear model chosen WITHOUT test data: LEAR-s and Ridge-s are both fitted on the
     first 90% of the training windows, the one with the lower MSE on the last 10% is refitted on all training
     windows. Reason: in the first version the static LEAR-s blew up on DE (MSE 1733 vs Ridge-s 284); the choice now uses
     training data only. LEAR-s and Ridge-s are still reported.
Everything else is identical to the first version.

Docstring of the first version:
LLM-free controls on MemCast's EPF test protocol. No LLM, no API, CPU only.

Question
    MemCast (arXiv 2602.03164, ICML 2026) reports large gains on 5 EPF markets (its Table 2, raw-scale MSE, GPT-5):
    NP 36.871, PJM 30.238, BE 756.308, FR 756.981, DE 210.445. Its LLM receives (i) the 168-h price history,
    (ii) the day-ahead load / generation forecasts for the 24 target hours, (iii) the futures of the top-3
    retrieved training windows. On the same test windows we evaluate predictors that use the same information
    WITHOUT an LLM:
      R-k      mean of the next-24-h prices of the top-k retrieved memory windows. Retrieval is MemCast's
               retrieve_similar_examples (10 hand-crafted features of the 168-h history, StandardScaler fitted on
               the memory, cosine similarity) with confidence = 0 (no LLM-built memory). k = 3 is primary.
      SN-1d    seasonal naive: the last 24 h of the history.
      SN-7d    seasonal naive: the same hours one week earlier (first 24 h of the 168-h history).
      LEAR-s   LEAR-style linear model (Lago et al., Applied Energy 2021): per target hour, LassoLarsIC(aic) on
               asinh(median/MAD)-scaled prices of the 24-h blocks D-1, D-2, D-3, D-7, the two day-ahead exogenous
               forecasts for D, D-1, D-7, and 7 day-of-week dummies. Fitted once on the training windows
               (static; no daily recalibration). Ridge (RidgeCV) is reported as a sensitivity.

Reconstruction (MemCast's EPF CSVs are not in its public data bundle)
    Each market = the LAST 14,496 hourly rows of the public epftoolbox file (Zenodo record 4624805). MemCast's
    Table 7 gives 14,496 rows (10147/1450/2899) for each of NP, PJM, BE, FR, DE. Windows follow MemCast's code
    (main/EPF/EPF_main_few_shot_reasoning.py, lines 1105-1241):
      E = int(0.8 * N);  test window i = 0..29: history rows [E-168+24i, E+24i), target rows [E+24i, E+24i+24)
      memory window k: history rows [24k, 24k+168), future rows [24k+168, 24k+192)
      training memory (primary): k < len(range(0, E - 192 + 1, 24))
      online memory (sensitivity): also later k, keeping only windows whose future ends <= E + 24i
    Metrics: MSE and MAE of the price on the raw scale over 30 x 24 points (MemCast: "evaluated on raw time series").

Usage (Python environment of environment/requirements.txt, plus scikit-learn):
    python -I memcast_controls_v2.py --csv NP=<data>/NP.csv --csv PJM=<data>/PJM.csv --csv BE=<data>/BE.csv --csv FR=<data>/FR.csv --csv DE=<data>/DE.csv --test-stride 96 --n-test 30 --out <repo>/electricity/memcast/weak_references/out_spread96
Outputs: <out>/memcast_controls.json, <out>/memcast_controls.txt, <out>/per_window.csv
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.linear_model import LassoLarsIC, RidgeCV
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.preprocessing import StandardScaler

N_ROWS, LB, H, STRIDE, N_TEST = 14496, 168, 24, 24, 30
TEST_STRIDE = 24  # set from --test-stride
BOOT, SEED = 2000, 0

# MemCast arXiv 2602.03164v2, Table 2, MSE / MAE as printed (verified verbatim 2026-11-13)
PAPER = {
    "MemCast":     {"NP": (36.871, 3.567), "PJM": (30.238, 3.575), "BE": (756.308, 12.534), "FR": (756.981, 12.142), "DE": (210.445, 9.195)},
    "ARIMA":       {"NP": (78.944, 5.722), "PJM": (181.141, 9.944), "BE": (6813.559, 20.889), "FR": (3072.651, 16.878), "DE": (414.126, 14.568)},
    "Prophet":     {"NP": (58.424, 5.311), "PJM": (63.342, 6.102), "BE": (1055.918, 18.334), "FR": (999.577, 14.887), "DE": (515.070, 15.759)},
    "PatchTST":    {"NP": (59.305, 5.326), "PJM": (124.575, 8.686), "BE": (1120.463, 18.449), "FR": (1339.507, 15.768), "DE": (290.971, 11.974)},
    "iTransformer": {"NP": (64.080, 5.622), "PJM": (116.768, 8.455), "BE": (1236.950, 19.406), "FR": (1374.755, 17.980), "DE": (345.994, 13.304)},
    "TimeXer":     {"NP": (59.529, 5.220), "PJM": (84.743, 6.918), "BE": (887.125, 14.463), "FR": (876.179, 10.686), "DE": (296.232, 11.827)},
    "ConvTimeNet": {"NP": (55.857, 5.111), "PJM": (108.312, 7.935), "BE": (1146.507, 18.191), "FR": (1175.164, 15.096), "DE": (327.377, 12.727)},
    "DLinear":     {"NP": (68.723, 5.798), "PJM": (122.269, 8.800), "BE": (1074.966, 18.459), "FR": (1134.095, 16.237), "DE": (442.229, 15.299)},
}
NON_LLM = ["ARIMA", "Prophet", "PatchTST", "iTransformer", "TimeXer", "ConvTimeNet", "DLinear"]


def load_market(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    df.columns = [str(c).strip() for c in df.columns]
    date_col = df.columns[0]
    price = [c for c in df.columns[1:] if "price" in c.lower()]
    if len(price) != 1:
        raise SystemExit(f"{path}: expected exactly one price column, got {price} in {list(df.columns)}")
    exog = [c for c in df.columns[1:] if c != price[0]]
    if len(exog) != 2:
        raise SystemExit(f"{path}: expected two exogenous columns, got {exog}")
    out = pd.DataFrame({"date": pd.to_datetime(df[date_col]), "y": df[price[0]].astype(float),
                        "x1": df[exog[0]].astype(float), "x2": df[exog[1]].astype(float)})
    if len(out) < N_ROWS:
        raise SystemExit(f"{path}: {len(out)} rows < {N_ROWS}")
    out = out.iloc[-N_ROWS:].reset_index(drop=True)
    if out[["y", "x1", "x2"]].isna().any().any():
        raise SystemExit(f"{path}: NaN in the last {N_ROWS} rows")
    out.attrs["columns"] = {"price": price[0], "x1": exog[0], "x2": exog[1]}
    return out


def memcast_features(series: np.ndarray) -> np.ndarray:
    """Port of MemCast extract_time_series_features (main/EPF/EPF_main_few_shot_reasoning.py lines 26-89)."""
    s = np.asarray(series, dtype=float)
    f = [np.mean(s), np.std(s), np.min(s), np.max(s), np.median(s)]
    f.append(np.polyfit(range(len(s)), s, 1)[0])
    daily = [np.std(s[i:i + 24]) for i in range(0, len(s), 24) if i + 24 <= len(s)]
    f.append(np.mean(daily) if daily else 0.0)
    c = np.corrcoef(s[:-1], s[1:])[0, 1]
    f.append(0.0 if np.isnan(c) else c)
    d = np.diff(s)
    f.extend([np.mean(np.abs(d)), np.std(d)])
    return np.array(f)


def retrieve_topk(cur: np.ndarray, mem_hist: np.ndarray, k: int) -> np.ndarray:
    """MemCast retrieve_similar_examples with confidence = 0: scaler fit on memory, cosine, top-k."""
    hf = np.array([memcast_features(h) for h in mem_hist])
    sc = StandardScaler().fit(hf)
    sim = cosine_similarity(sc.transform(memcast_features(cur).reshape(1, -1)), sc.transform(hf))[0]
    return np.argsort(sim)[::-1][:k]


class AsinhScaler:
    """LEAR's 'Invariant' transform: asinh((x - median) / (MAD / 0.6745)), fitted on training rows."""

    def fit(self, x: np.ndarray):
        self.m = float(np.median(x))
        mad = float(np.median(np.abs(x - self.m))) / 0.6745
        self.s = mad if mad > 0 else 1.0
        return self

    def tf(self, x):
        return np.arcsinh((np.asarray(x, dtype=float) - self.m) / self.s)

    def inv(self, z):
        return np.sinh(np.asarray(z, dtype=float)) * self.s + self.m


def lear_design(df: pd.DataFrame, t0: int, sy: AsinhScaler, s1: AsinhScaler, s2: AsinhScaler) -> np.ndarray:
    """Features for a target block starting at row t0 (uses rows < t0 for prices, and the day-ahead exog of [t0, t0+24))."""
    y, x1, x2 = df["y"].to_numpy(), df["x1"].to_numpy(), df["x2"].to_numpy()
    blk = lambda a, d: a[t0 - 24 * d:t0 - 24 * d + 24]
    parts = [sy.tf(blk(y, d)) for d in (1, 2, 3, 7)]
    for a, s in ((x1, s1), (x2, s2)):
        parts.append(s.tf(a[t0:t0 + 24]))
        parts.append(s.tf(blk(a, 1)))
        parts.append(s.tf(blk(a, 7)))
    dow = np.zeros(7)
    dow[df["date"].iloc[t0].dayofweek] = 1.0
    parts.append(dow)
    return np.concatenate(parts)


def metrics(pred: np.ndarray, true: np.ndarray) -> tuple[float, float]:
    e = pred - true
    return float(np.mean(e ** 2)), float(np.mean(np.abs(e)))


def boot_ci(per_win_sq: np.ndarray, block: int, rng: np.random.Generator) -> list[float]:
    n = len(per_win_sq)
    vals = []
    for _ in range(BOOT):
        idx = []
        while len(idx) < n:
            s = int(rng.integers(n))
            idx.extend((s + j) % n for j in range(block))
        vals.append(float(np.mean(per_win_sq[idx[:n]])))
    vals.sort()
    return [vals[int(0.025 * BOOT)], vals[int(0.975 * BOOT) - 1]]


def run_market(name: str, df: pd.DataFrame, rng: np.random.Generator) -> tuple[dict, list[dict]]:
    N = len(df)
    E = int(0.8 * N)
    max_tv = len(range(0, E - (LB + H) + 1, STRIDE))
    y = df["y"].to_numpy()
    all_k = [k for k in range((N - LB - H) // STRIDE + 1)]
    hist_of = lambda k: y[STRIDE * k:STRIDE * k + LB]
    fut_of = lambda k: y[STRIDE * k + LB:STRIDE * k + LB + H]
    train_k = [k for k in all_k if k < max_tv]
    assert all(STRIDE * k + LB + H <= E for k in train_k), "training memory overlaps the test region"

    # LEAR-s fit on the training windows (targets inside [0, E), all lags available)
    sy, s1, s2 = AsinhScaler().fit(y[:E]), AsinhScaler().fit(df["x1"].to_numpy()[:E]), AsinhScaler().fit(df["x2"].to_numpy()[:E])
    lear_t0 = [STRIDE * k + LB for k in train_k if STRIDE * k + LB - 24 * 7 >= 0]
    Xtr = np.array([lear_design(df, t, sy, s1, s2) for t in lear_t0])
    Ytr = np.array([sy.tf(y[t:t + H]) for t in lear_t0])
    # SameInfo selection on training data only: fit on the first 90% of training windows, validate on the last 10%
    n_fit = int(0.9 * len(Xtr))
    xs_v = StandardScaler().fit(Xtr[:n_fit])
    las_v = [LassoLarsIC(criterion="aic").fit(xs_v.transform(Xtr[:n_fit]), Ytr[:n_fit, h]) for h in range(H)]
    rid_v = RidgeCV(alphas=np.logspace(-3, 3, 13)).fit(xs_v.transform(Xtr[:n_fit]), Ytr[:n_fit])
    Zv, Yv = xs_v.transform(Xtr[n_fit:]), sy.inv(Ytr[n_fit:])
    val_mse = {"LEAR-s": float(np.mean((sy.inv(np.column_stack([m.predict(Zv) for m in las_v])) - Yv) ** 2)),
               "Ridge-s": float(np.mean((sy.inv(rid_v.predict(Zv)) - Yv) ** 2))}
    same_info_choice = min(val_mse, key=val_mse.get)

    xs = StandardScaler().fit(Xtr)
    lasso = [LassoLarsIC(criterion="aic").fit(xs.transform(Xtr), Ytr[:, h]) for h in range(H)]
    ridge = RidgeCV(alphas=np.logspace(-3, 3, 13)).fit(xs.transform(Xtr), Ytr)

    preds = {m: [] for m in ("R-1", "R-3", "R-5", "R-10", "R-3-online", "SN-1d", "SN-7d", "LEAR-s", "Ridge-s", "SameInfo")}
    trues, rows = [], []
    for i in range(N_TEST):
        t0 = E + TEST_STRIDE * i
        if t0 + H > N:
            raise SystemExit(f"{name}: test window {i} at row {t0} runs past the end ({N})")
        cur, true = y[t0 - LB:t0], y[t0:t0 + H]
        th = np.array([hist_of(k) for k in train_k])
        tf = np.array([fut_of(k) for k in train_k])
        for k in (1, 3, 5, 10):
            preds[f"R-{k}"].append(tf[retrieve_topk(cur, th, k)].mean(axis=0))
        on_k = [k for k in all_k if STRIDE * k + LB + H <= t0]
        oh, of = np.array([hist_of(k) for k in on_k]), np.array([fut_of(k) for k in on_k])
        preds["R-3-online"].append(of[retrieve_topk(cur, oh, 3)].mean(axis=0))
        preds["SN-1d"].append(cur[-24:])
        preds["SN-7d"].append(cur[:24])
        z = xs.transform(lear_design(df, t0, sy, s1, s2).reshape(1, -1))
        preds["LEAR-s"].append(sy.inv(np.array([m.predict(z)[0] for m in lasso])))
        preds["Ridge-s"].append(sy.inv(ridge.predict(z)[0]))
        preds["SameInfo"].append(preds[same_info_choice][-1])
        trues.append(true)
        rows.append({"market": name, "window": i, "target_start": str(df["date"].iloc[t0]), **{
            f"mse_{m}": float(np.mean((preds[m][-1] - true) ** 2)) for m in preds}})

    T = np.array(trues)
    res = {"market": name, "n_rows": N, "E": E, "n_train_memory": len(train_k), "n_lear_train": len(lear_t0),
           "columns": df.attrs["columns"], "test_first_target": str(df["date"].iloc[E]),
           "test_last_target": str(df["date"].iloc[E + TEST_STRIDE * (N_TEST - 1) + H - 1]),
           "test_stride": TEST_STRIDE, "n_test": N_TEST,
           "same_info_validation_mse": val_mse, "same_info_choice": same_info_choice,
           "lasso_nonzero_per_hour": [int(np.count_nonzero(m.coef_)) for m in lasso], "controls": {}}
    for m, p in preds.items():
        P = np.array(p)
        mse, mae = metrics(P, T)
        per_win = np.mean((P - T) ** 2, axis=1)
        res["controls"][m] = {"mse": mse, "mae": mae, "mse_ci95_iid": boot_ci(per_win, 1, rng),
                              "mse_ci95_block7": boot_ci(per_win, 7, rng),
                              "ratio_to_MemCast_mse": mse / PAPER["MemCast"][name][0]}
    best = min(NON_LLM, key=lambda b: PAPER[b][name][0])
    res["paper"] = {"MemCast": PAPER["MemCast"][name], "best_non_llm": [best, PAPER[best][name]]}
    return res, rows


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--csv", action="append", required=True, metavar="MARKET=PATH")
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--test-stride", type=int, default=24, help="hours between test windows (memory stride stays 24)")
    ap.add_argument("--n-test", type=int, default=30)
    a = ap.parse_args()
    global TEST_STRIDE, N_TEST
    TEST_STRIDE, N_TEST = a.test_stride, a.n_test
    a.out.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(SEED)
    results, all_rows, lines = [], [], []
    for spec in a.csv:
        name, _, path = spec.partition("=")
        if name not in PAPER["MemCast"]:
            raise SystemExit(f"unknown market {name}")
        r, rows = run_market(name, load_market(Path(path)), rng)
        results.append(r)
        all_rows.extend(rows)
        pm, (bn, bv) = r["paper"]["MemCast"], r["paper"]["best_non_llm"]
        lines.append(f"== {name}: test targets {r['test_first_target']} .. {r['test_last_target']} "
                     f"({r['n_test']} windows, stride {r['test_stride']} h); "
                     f"train memory {r['n_train_memory']} windows; LEAR train {r['n_lear_train']}; columns {r['columns']}")
        lines.append(f"   SameInfo chose {r['same_info_choice']} on training-only validation MSE {r['same_info_validation_mse']}")
        lines.append(f"   paper: MemCast MSE {pm[0]:.3f} MAE {pm[1]:.3f} | best non-LLM baseline in paper: {bn} MSE {bv[0]:.3f} MAE {bv[1]:.3f}")
        for m, c in r["controls"].items():
            lines.append(f"   {m:11s} MSE {c['mse']:10.3f}  iid({c['mse_ci95_iid'][0]:.1f},{c['mse_ci95_iid'][1]:.1f}) "
                         f"block7({c['mse_ci95_block7'][0]:.1f},{c['mse_ci95_block7'][1]:.1f})  MAE {c['mae']:8.3f}  "
                         f"MSE/MemCast {c['ratio_to_MemCast_mse']:.3f}  MSE/best-non-LLM {c['mse'] / bv[0]:.3f}")
    (a.out / "memcast_controls.json").write_text(json.dumps(results, indent=2), encoding="utf-8")
    pd.DataFrame(all_rows).to_csv(a.out / "per_window.csv", index=False)
    (a.out / "memcast_controls.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    sys.exit(main())
