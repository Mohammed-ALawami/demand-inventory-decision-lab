"""Weekly inventory simulation: policies compared on identical demand, forecasts, budget, storage and costs."""
import time, numpy as np, pandas as pd
from scipy.optimize import milp, LinearConstraint, Bounds
from scipy.sparse import lil_matrix

QS = np.array([.1, .3, .5, .7, .9])

def make_params(M, pr, t0, cfg, cost_seed=None):
    rng = np.random.default_rng(cfg['seed'] if cost_seed is None else cost_seed)
    n = M.shape[1]; price = pr.med_price.values.astype(float)
    cost = price * rng.uniform(*cfg['cost_ratio_range'], n)
    tr = M.iloc[:t0].iloc[-52:].mean().values
    packs = np.where(tr >= 200, cfg['pack_sizes'][2], np.where(tr >= 50, cfg['pack_sizes'][1], cfg['pack_sizes'][0]))
    vol = np.clip(0.5 + price/10, .5, 2.0)
    budget = cfg['budget_kappa'] * (tr*cost).sum()
    cap = cfg['storage_lambda'] * 2 * (tr*vol).sum()
    return dict(price=price, cost=cost, pack=packs.astype(float), vol=vol, budget=budget, cap=cap, h=cfg['holding_rate'])

def err_scen(M, F, t, win=26):
    """Scenario demands from the SKU's own recent one-step errors (only errors already observed at time t)."""
    X = M.values; a = max(9, t-win+1)
    E = X[a:t+1] - F[a-1:t]                      # errors of forecasts made at a-1..t-1 for weeks a..t
    q = np.quantile(E, QS, axis=0)               # (5, n)
    return np.maximum(F[t][None, :] + q, 0.0)

def order_base_stock(f, sd, inv, P, z):
    S = f + z*sd
    need = np.maximum(S - inv, 0.0)
    cases = np.ceil(need / P['pack'])
    for _ in range(60):                          # pro-rata shrink until budget and storage hold (documented fairness rule)
        spend = (cases*P['pack']*P['cost']).sum(); space = ((inv + cases*P['pack'])*P['vol']).sum()
        r = min(P['budget']/max(spend, 1e-9), (P['cap']-(inv*P['vol']).sum())/max((cases*P['pack']*P['vol']).sum(), 1e-9), 1.0)
        if r >= 1.0 - 1e-12: break
        cases = np.floor(cases * r)
    return cases

def order_milp(D, p, inv, P, tl=10):
    """Max expected next-week margin - holding on leftover, integer cases, budget + storage. D: (S,n) scenario demands."""
    S, n = D.shape; nv = n + S*n                   # x_i cases, then y_si sales
    c = np.zeros(nv)
    marg = P['price'] - P['cost']
    for s in range(S):
        c[n+s*n:n+(s+1)*n] = -p[s]*(marg + P['h']*P['cost'])   # sold units earn margin and avoid holding
    # leftover holding = h*cost*(inv + pack*x - y): the pack*x term is a cost on x
    c[:n] = P['h']*P['cost']*P['pack']
    A = lil_matrix((2 + S*n, nv)); lo = []; hi = []
    A[0, :n] = P['pack']*P['cost']; lo.append(-np.inf); hi.append(P['budget'])
    A[1, :n] = P['pack']*P['vol']; lo.append(-np.inf); hi.append(P['cap']-(inv*P['vol']).sum())
    r = 2
    for s in range(S):
        for i in range(n):                         # y_si - pack_i x_i <= inv_i
            A[r, n+s*n+i] = 1; A[r, i] = -P['pack'][i]; lo.append(-np.inf); hi.append(inv[i]); r += 1
    ub = np.concatenate([np.full(n, 1e4), D.ravel()])
    integ = np.concatenate([np.ones(n), np.zeros(S*n)])
    res = milp(c, constraints=LinearConstraint(A.tocsr(), lo, hi), integrality=integ, bounds=Bounds(0, ub),
               options=dict(time_limit=tl, mip_rel_gap=1e-3))
    if res.x is None: return np.zeros(n), res.status
    return np.round(res.x[:n]), res.status

def simulate(M, F, P, t0, policy, z=0.0, t_end=None):
    """policy: 'base_stock' | 'milp' | 'oracle'. F: forecast matrix. Order after week t arrives before week t+1."""
    X = M.values; T, n = X.shape; T = t_end or T
    inv = np.ceil(M.iloc[t0-8:t0].mean().values / P['pack']) * P['pack']      # same opening stock for all policies
    rows = []; stat = []; times = []
    for t in range(t0-1, T-1):
        # decision at end of week t, demand realised in week t+1
        f = F[t]; dem_next = X[t+1]
        E = X[max(9,t-25):t+1] - F[max(9,t-25)-1:t]; sd = E.std(0)
        if policy == 'base_stock': cs = order_base_stock(f, sd, inv, P, z)
        elif policy == 'milp':
            D = err_scen(M, F, t); t_ = time.time(); cs, st = order_milp(D, np.full(len(QS), 1/len(QS)), inv, P); times.append(time.time()-t_); stat.append(st)
        elif policy == 'oracle':
            t_ = time.time(); cs, st = order_milp(dem_next[None, :], np.ones(1), inv, P); times.append(time.time()-t_); stat.append(st)
        inv = inv + cs*P['pack']
        sold = np.minimum(inv, dem_next); left = inv - sold
        rev = (sold*P['price']).sum(); cogs = (sold*P['cost']).sum(); hold = (left*P['cost']*P['h']).sum()
        rows.append(dict(week=M.index[t+1], profit=rev-cogs-hold, revenue=rev, cogs=cogs, holding=hold,
                         purchased=(cs*P['pack']*P['cost']).sum(), demand_units=dem_next.sum(), sold_units=sold.sum(),
                         stockout_skus=int(((dem_next > inv)).sum()), inv_value=(left*P['cost']).sum(),
                         lost_margin=(((dem_next-sold)*(P['price']-P['cost'])).sum())))
        inv = left
    df = pd.DataFrame(rows); df.attrs['solve_s'] = times; df.attrs['open_inv_value'] = float((np.ceil(M.iloc[t0-8:t0].mean().values / P['pack']) * P['pack'] * P['cost']).sum())
    return df, stat

def summarize(df, name):
    return dict(policy=name, profit=df.profit.sum(), revenue=df.revenue.sum(),
                fill_rate=df.sold_units.sum()/df.demand_units.sum(), avg_inventory_value=df.inv_value.mean(),
                stockout_sku_weeks=int(df.stockout_skus.sum()), lost_margin=df.lost_margin.sum(),
                avg_weekly_purchase=df.purchased.mean(), terminal_inv_value=df.inv_value.iloc[-1], total_purchased=df.purchased.sum(), holding=df.holding.sum(),
                max_solve_s=max(df.attrs.get('solve_s', [0]) or [0]))
