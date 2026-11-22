import sys, duckdb, pandas as pd
sys.path.insert(0,'src'); from data import load
M, agg, pr, t0, v0 = load()
M.rename_axis('week').reset_index().melt(id_vars='week', var_name='sku', value_name='units').to_csv('powerbi/weekly_demand_eligible.csv', index=False)
pr.reset_index()[['sku','description','med_price']].to_csv('powerbi/sku_dim.csv', index=False)
for f in ['main_results','weekly_results','sensitivity','forecast_backtest']: pd.read_csv(f'reports/{f}.csv').to_csv(f'powerbi/{f}.csv', index=False)
c = duckdb.connect('data/lab.duckdb')
for t in ['monthly','return_rate','country_mix']: c.execute(f'select * from {t}').df().to_csv(f'powerbi/{t}.csv', index=False)
