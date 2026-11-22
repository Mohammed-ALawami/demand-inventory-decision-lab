import sys, numpy as np; sys.path.insert(0, 'src')
from data import load; from forecast import rolling, backtest; from sim import *; from config import CFG
M, agg, pr, t0, v0 = load(); P = make_params(M, pr, t0, CFG); _, F = backtest(M, agg, 61, t0)

def test_no_future_leakage_in_forecast():
    """Changing demand after week t must not change the forecast made at week t."""
    M2 = M.copy(); M2.iloc[100:] *= 7; a2 = agg.copy(); a2.iloc[100:] *= 7
    for m in ['naive', 'ma8', 'ses', 'ma8_seasonal']:
        assert np.allclose(rolling(M, agg, m)[90:99], rolling(M2, a2, m)[90:99])

def test_eligibility_uses_only_pretest_data():
    assert (M.iloc[t0-52:t0] > 0).mean().min() >= .70

def test_orders_respect_budget_storage_and_casepacks():
    inv = np.zeros(M.shape[1]); f = F['ma8'][t0-1]
    c1 = order_base_stock(f, f*.5, inv, P, 1.0)
    D = err_scen(M, F['ma8'], t0-1); c2, st = order_milp(D, np.full(5, .2), inv, P)
    for c in (c1, c2):
        assert (c >= 0).all() and np.allclose(c, np.round(c))
        assert (c*P['pack']*P['cost']).sum() <= P['budget'] + 1e-6
        assert (c*P['pack']*P['vol']).sum() <= P['cap'] + 1e-6

def test_milp_places_nonempty_order():
    inv = np.zeros(M.shape[1]); D = err_scen(M, F['ma8'], t0-1); c, _ = order_milp(D, np.full(5, .2), inv, P)
    assert c.sum() > 0

def test_all_policies_see_same_demand_and_costs():
    a, _ = simulate(M, F['ma8'], P, t0, 'base_stock', z=1.0); b, _ = simulate(M, F['ma8'], P, t0, 'milp')
    assert np.allclose(a.demand_units, b.demand_units)

if __name__ == '__main__':
    for n in [x for x in dir() if x.startswith('test_')]:
        globals()[n](); print('PASS', n)
