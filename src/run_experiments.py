import sys, json, copy, numpy as np, pandas as pd
sys.path.insert(0, 'src')
from data import load; from forecast import *; from sim import *; from config import CFG

M, agg, pr, t0, v0 = load(); VS = 61
bt, F = backtest(M, agg, VS, t0); bt.to_csv('reports/forecast_backtest.csv', index=False)
best = bt[bt.split == 'validation'].sort_values('WAPE').model.iloc[0]
print('forecast chosen on validation:', best)
ZS = np.arange(0, 3.01, .25)

def tune_z(P, Fm):
    r = [(z, simulate(M, Fm, P, VS, 'base_stock', z=z, t_end=t0)[0].profit.sum()) for z in ZS]
    return max(r, key=lambda a: a[1])[0]

def run_grid(P, fnames):
    out = {}; sums = []
    for fn in fnames:
        z = tune_z(P, F[fn])
        d, _ = simulate(M, F[fn], P, t0, 'base_stock', z=z); out[f'base_stock|{fn}'] = d
        sums.append({**summarize(d, f'base_stock|{fn}'), 'z': z})
        d, st = simulate(M, F[fn], P, t0, 'milp'); out[f'milp|{fn}'] = d
        sums.append({**summarize(d, f'milp|{fn}'), 'z': np.nan, 'solver_nonoptimal': int(sum(s not in (0,) for s in st))})
    return out, sums

P = make_params(M, pr, t0, CFG)
out, sums = run_grid(P, ['naive', best])
d, st = simulate(M, F[best], P, t0, 'oracle'); out['oracle'] = d
sums.append({**summarize(d, 'myopic perfect-information benchmark'), 'z': np.nan})
S = pd.DataFrame(sums); S.to_csv('reports/main_results.csv', index=False); print(S.round(3).to_string())
pd.concat({k: v for k, v in out.items()}, names=['policy']).reset_index(level=0).to_csv('reports/weekly_results.csv', index=False)

# accounting identity per policy: cash basis (revenue - purchases + closing stock at cost - opening stock at cost) = revenue - COGS
acct = {}
for k, d in out.items():
    cash = d.revenue.sum() - d.purchased.sum() + d.inv_value.iloc[-1] - d.attrs['open_inv_value']
    acct[k] = dict(cash_basis_margin=float(cash), revenue_minus_cogs=float((d.revenue - d.cogs).sum()), gap=float(cash - (d.revenue - d.cogs).sum()),
                   terminal_inv_value=float(d.inv_value.iloc[-1]))
print(acct)
# paired bootstrap of weekly profit differences. Weeks are NOT independent (inventory carries over, demand is autocorrelated),
# so use a moving-block bootstrap (block=4) as well as the naive i.i.d. one.
rng = np.random.default_rng(1)
diff = out[f'milp|{best}'].profit.values - out[f'base_stock|{best}'].profit.values; n = len(diff)
iid = [rng.choice(diff, n).sum() for _ in range(5000)]
def block(d, L=4):
    k = int(np.ceil(len(d)/L)); st = rng.integers(0, len(d)-L+1, k)
    return np.concatenate([d[s:s+L] for s in st])[:len(d)].sum()
blk = [block(diff) for _ in range(5000)]
ci = dict(total_diff=float(diff.sum()), ci95_iid=[float(np.percentile(iid, 2.5)), float(np.percentile(iid, 97.5))],
          ci95_block4=[float(np.percentile(blk, 2.5)), float(np.percentile(blk, 97.5))],
          weeks_milp_better=int((diff > 0).sum()), weeks=n, diff_last4_weeks=float(diff[-4:].sum()), diff_first22_weeks=float(diff[:-4].sum()),
          worst_week_diff=float(diff.min()))
print(ci)
# dict(statuses={int(a): int(b) for a, b in zip(*np.unique(v.attrs.get('solve_s') and [0]*0 or [0], return_counts=True))}) for k, v in out.items()}

# sensitivity: budget tightness x 5 cost-assumption seeds (best forecast only)
rows = []
for kap in [0.6, 0.8, 1.0, 1.3]:
    for seed in [7, 8, 9, 10, 11]:
        c2 = dict(CFG, budget_kappa=kap); P2 = make_params(M, pr, t0, c2, cost_seed=seed)
        z = tune_z(P2, F[best])
        b, _ = simulate(M, F[best], P2, t0, 'base_stock', z=z); m, mst = simulate(M, F[best], P2, t0, 'milp')
        sb, sm = summarize(b, 'b'), summarize(m, 'm')
        rows.append(dict(kappa=kap, seed=seed, z=z, base_profit=sb['profit'], milp_profit=sm['profit'],
                         gain_pct=100*(sm['profit']/sb['profit']-1), base_fill=sb['fill_rate'], milp_fill=sm['fill_rate'],
                         base_inv=sb['avg_inventory_value'], milp_inv=sm['avg_inventory_value'], milp_nonoptimal=int(sum(x != 0 for x in mst)), milp_max_solve_s=sm['max_solve_s']))
SE = pd.DataFrame(rows); SE.to_csv('reports/sensitivity.csv', index=False)
print(SE.groupby('kappa')[['gain_pct']].agg(['mean', 'min', 'max']).round(2))
print('worst sensitivity gain', SE.gain_pct.min(), 'nonoptimal solves', SE.milp_nonoptimal.sum(), 'max solve s', SE.milp_max_solve_s.max())
json.dump(dict(best_forecast=best, bootstrap=ci, accounting=acct, z_grid=list(ZS), sens_worst_gain_pct=float(SE.gain_pct.min()), sens_nonoptimal=int(SE.milp_nonoptimal.sum()), sens_max_solve_s=float(SE.milp_max_solve_s.max())), open('reports/summary.json', 'w'), indent=1)
