"""One-step-ahead rolling-origin forecasts. Forecast for week t+1 uses data up to week t only."""
import numpy as np, pandas as pd

def season_factor(agg, t):
    """Aggregate (all-SKU) seasonality: last year's level at t+1 vs last year's trailing 8-wk mean. 1.0 if no history."""
    if t + 1 - 52 < 8: return 1.0
    base = agg.iloc[t-52-7:t-52+1].mean()
    return float(agg.iloc[t+1-52] / base) if base > 0 else 1.0

def rolling(M, agg, model, alpha=0.3):
    T, n = M.shape; F = np.full((T, n), np.nan)   # F[t] = forecast made after week t for week t+1
    X = M.values
    for t in range(8, T - 1):
        if model == 'naive':   f = X[t]
        elif model == 'ma4':   f = X[t-3:t+1].mean(0)
        elif model == 'ma8':   f = X[t-7:t+1].mean(0)
        elif model == 'ma8_seasonal':
            f = X[t-7:t+1].mean(0) * np.clip(season_factor(agg, t), .3, 3)
        elif model == 'ses':
            lvl = X[max(0, t-25)]
            for k in range(max(0, t-24), t+1): lvl = alpha*X[k] + (1-alpha)*lvl
            f = lvl
        F[t] = f
    return F

MODELS = ['naive', 'ma4', 'ma8', 'ses', 'ma8_seasonal']

def wape(actual, fc): return np.abs(actual-fc).sum() / max(actual.sum(), 1e-9)

def backtest(M, agg, v_start, t0):
    X = M.values; rows = []; allF = {m: rolling(M, agg, m) for m in MODELS}
    for m, F in allF.items():
        for name, a, b in [('validation', v_start, t0), ('test', t0, len(M))]:
            idx = np.arange(a, b)                      # target weeks
            fc = F[idx-1]; ac = X[idx]
            rows.append(dict(model=m, split=name, WAPE=wape(ac, fc), bias_pct=100*(fc.sum()-ac.sum())/ac.sum()))
    return pd.DataFrame(rows), allF
