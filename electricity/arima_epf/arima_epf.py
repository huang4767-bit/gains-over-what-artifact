"""C1: ARIMA(2,1,2) on CastFSR's 60 EPF windows, to pin the z-score scale.

Criteria written in advance (section C1; the wind diagnostic in electricity/wind_diagnostic/ is section C2).
Usage:
  python -I arima_epf.py --raw-dir <data-root> --out <out-dir>

Inputs:
  <raw-dir>/<M>/<M>.csv for M in BE, DE, FR, NP, PJM (column 0 = timestamp, column 1 = price), i.e. the
  epftoolbox day-ahead price files, one sub-folder per market.
Outputs (in <out>):
  arima_epf_windows.csv, arima_epf_summary.json, arima_epf_summary.txt
"""
import argparse
import json
import os
import sys
import time
import warnings

import numpy as np
import pandas as pd

N_SLICE, N_TRAIN, N_TRVAL = 14496, 10224, 11640
N_WIN, HORIZON, STRIDE, LOOKBACK = 60, 24, 48, 168
EXPECTED = {
    "BE": ("2015-05-08 00:00:00", "2016-07-07 00:00:00", "2016-09-04 00:00:00", "2016-12-31 23:00:00"),
    "FR": ("2015-05-08 00:00:00", "2016-07-07 00:00:00", "2016-09-04 00:00:00", "2016-12-31 23:00:00"),
    "DE": ("2016-05-07 00:00:00", "2017-07-07 00:00:00", "2017-09-04 00:00:00", "2017-12-31 23:00:00"),
    "NP": ("2017-04-30 00:00:00", "2018-06-30 00:00:00", "2018-08-28 00:00:00", "2018-12-24 23:00:00"),
    "PJM": ("2017-04-30 00:00:00", "2018-06-30 00:00:00", "2018-08-28 00:00:00", "2018-12-24 23:00:00"),
}
PAPER_ARIMA_MSE = {"BE": 1.973, "DE": 1.519, "FR": 6.369, "NP": 0.727, "PJM": 0.991}


def fit_forecast(history):
    from statsmodels.tsa.arima.model import ARIMA

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        result = ARIMA(np.asarray(history, dtype=np.float64), order=(2, 1, 2)).fit()
        fc = np.asarray(result.forecast(HORIZON), dtype=np.float64)
    conv = [str(w.message) for w in caught if "converg" in str(w.message).lower()]
    return fc, conv


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--raw-dir", required=True, help="data root with <M>/<M>.csv per market")
    ap.add_argument("--out", required=True, help="output folder (created if missing)")
    ap.add_argument("--markets", default="BE,DE,FR,NP,PJM")
    ap.add_argument("--max-windows", type=int, default=N_WIN, help="smoke test: fewer windows")
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)

    import statsmodels

    lines = [f"python {sys.version.split()[0]}  numpy {np.__version__}  pandas {pd.__version__}  statsmodels {statsmodels.__version__}"]
    rows = []
    summary = {}
    for mkt in args.markets.split(","):
        frame = pd.read_csv(os.path.join(args.raw_dir, mkt, f"{mkt}.csv"))
        frame = frame.iloc[-N_SLICE:].reset_index(drop=True)
        stamps = frame.iloc[:, 0].astype(str).tolist()
        price = frame.iloc[:, 1].to_numpy(dtype=np.float64)
        got = (stamps[0], stamps[N_TRAIN], stamps[N_TRVAL], stamps[-1])
        gate_split = got == EXPECTED[mkt]
        sd_train = float(np.std(price[:N_TRAIN]))
        sd_trval = float(np.std(price[:N_TRVAL]))
        sd_full = float(np.std(price))
        sq_err, abs_err, n_fail, n_conv = [], [], 0, 0
        t0 = time.time()
        for k in range(min(args.max_windows, N_WIN)):
            origin = N_TRVAL + STRIDE * k
            truth = price[origin:origin + HORIZON]
            try:
                fc, conv = fit_forecast(price[origin - LOOKBACK:origin])
                n_conv += 1 if conv else 0
                if not np.all(np.isfinite(fc)):
                    raise ValueError("non-finite forecast")
            except Exception as exc:  # record and continue
                n_fail += 1
                rows.append({"market": mkt, "window": k, "origin": stamps[origin], "status": f"fail: {exc}"})
                continue
            err = fc - truth
            sq_err.extend((err ** 2).tolist())
            abs_err.extend(np.abs(err).tolist())
            rows.append({"market": mkt, "window": k, "origin": stamps[origin], "status": "ok",
                         "raw_mse": float(np.mean(err ** 2)), "raw_mae": float(np.mean(np.abs(err))),
                         "converge_warning": bool(conv)})
        raw_mse = float(np.mean(sq_err)) if sq_err else float("nan")
        raw_mae = float(np.mean(abs_err)) if abs_err else float("nan")
        paper = PAPER_ARIMA_MSE[mkt]
        res = {
            "gate_split": gate_split, "split_stamps": got, "first_origin": stamps[N_TRVAL],
            "windows_ok": len(sq_err) // HORIZON, "windows_failed": n_fail, "windows_with_convergence_warning": n_conv,
            "sd_train": sd_train, "sd_trval": sd_trval, "sd_full": sd_full,
            "raw_mse": raw_mse, "raw_mae": raw_mae,
            "zmse_train": raw_mse / sd_train ** 2, "zmse_trval": raw_mse / sd_trval ** 2, "zmse_full": raw_mse / sd_full ** 2,
            "paper_arima_mse": paper,
            "q_train": raw_mse / sd_train ** 2 / paper, "q_trval": raw_mse / sd_trval ** 2 / paper, "q_full": raw_mse / sd_full ** 2 / paper,
            "implied_sd": float(np.sqrt(raw_mse / paper)),
            "seconds": round(time.time() - t0, 1),
        }
        res["implied_sd_over_train"] = res["implied_sd"] / sd_train
        res["implied_sd_over_full"] = res["implied_sd"] / sd_full
        summary[mkt] = res
        lines.append(f"{mkt}: gate_split={gate_split} ok={res['windows_ok']} fail={n_fail} convwarn={n_conv} "
                     f"sd(train/trval/full)={sd_train:.4f}/{sd_trval:.4f}/{sd_full:.4f} raw_mse={raw_mse:.4f} "
                     f"zmse(train/trval/full)={res['zmse_train']:.4f}/{res['zmse_trval']:.4f}/{res['zmse_full']:.4f} "
                     f"paper={paper} q(train/trval/full)={res['q_train']:.3f}/{res['q_trval']:.3f}/{res['q_full']:.3f} "
                     f"implied_sd={res['implied_sd']:.4f} ({res['seconds']} s)")
        print(lines[-1], flush=True)
    pd.DataFrame(rows).to_csv(os.path.join(args.out, "arima_epf_windows.csv"), index=False)
    with open(os.path.join(args.out, "arima_epf_summary.json"), "w", encoding="utf-8") as fh:
        json.dump(summary, fh, indent=2, ensure_ascii=False)
    with open(os.path.join(args.out, "arima_epf_summary.txt"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")


if __name__ == "__main__":
    main()
