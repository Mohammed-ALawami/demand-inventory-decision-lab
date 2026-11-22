import duckdb, numpy as np, pandas as pd
from config import CFG

def load(cfg=CFG, db='data/lab.duckdb'):
    c = duckdb.connect(db, read_only=True)
    w = c.execute("select sku,week,units from weekly").df()
    pr = c.execute("select * from sku_price").df().set_index('sku')
    weeks = pd.date_range(w.week.min(), w.week.max(), freq='W-MON')[:-1]  # drop final partial week (data ends Fri 2011-12-09)
    M = w.pivot_table(index='week', columns='sku', values='units', aggfunc='sum').reindex(weeks).fillna(0.0)
    M = M.clip(lower=0)
    T = len(M); test0 = T - cfg['test_weeks']; val0 = test0 - cfg['valid_weeks']
    # eligibility uses ONLY pre-test data: active in >=70% of the 52 weeks before test, top by units
    pre = M.iloc[test0-52:test0]
    act = (pre > 0).mean()
    elig = act[act >= .70].index
    top = pre[elig].sum().sort_values(ascending=False).head(cfg['n_skus']).index
    return M[top], M.sum(axis=1), pr.loc[top], test0, val0
