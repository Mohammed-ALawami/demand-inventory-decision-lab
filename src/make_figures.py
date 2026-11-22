import sys, json, duckdb, numpy as np, pandas as pd, matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
sys.path.insert(0, 'src'); from data import load
BG, FG, A, B, C, D = '#0f1419', '#e6edf3', '#2dd4bf', '#f59e0b', '#a78bfa', '#94a3b8'
plt.rcParams.update({'figure.facecolor': BG, 'axes.facecolor': BG, 'axes.edgecolor': '#334155', 'axes.labelcolor': FG, 'text.color': FG,
  'xtick.color': D, 'ytick.color': D, 'axes.grid': True, 'grid.color': '#1e293b', 'font.size': 11, 'axes.spines.top': False, 'axes.spines.right': False})
M, agg, pr, t0, v0 = load()
c = duckdb.connect('data/lab.duckdb'); c.execute(open('sql/02_descriptive.sql').read())
S = pd.read_csv('reports/main_results.csv'); W = pd.read_csv('reports/weekly_results.csv', parse_dates=['week'])
SE = pd.read_csv('reports/sensitivity.csv'); bt = pd.read_csv('reports/forecast_backtest.csv')
best = json.load(open('reports/summary.json'))['best_forecast']

# 1 demand + split
f, ax = plt.subplots(figsize=(11, 4.5)); ax.plot(agg.index, agg.values/1000, color=D, lw=1.4, label='All products')
ax.plot(M.index, M.sum(1).values/1000, color=A, lw=2, label='80 eligible SKUs (modelled)')
ax.axvspan(M.index[61], M.index[t0], color=B, alpha=.12, label='Validation'); ax.axvspan(M.index[t0], M.index[-1], color=C, alpha=.15, label='Out-of-sample test')
ax.set_ylabel('Units per week (thousands)'); ax.set_title('Weekly units sold: strong Q4 peak, zero weeks at year end', loc='left', fontweight='bold'); ax.legend(frameon=False, ncol=4, loc='upper left')
f.tight_layout(); f.savefig('figures/01_demand.png', dpi=160); plt.close()

# 2 forecast
f, ax = plt.subplots(figsize=(8, 4.5)); p = bt.pivot(index='model', columns='split', values='WAPE').sort_values('validation')
x = np.arange(len(p)); ax.bar(x-.2, p.validation, .4, color=B, label='Validation'); ax.bar(x+.2, p.test, .4, color=C, label='Test')
ax.set_xticks(x); ax.set_xticklabels(p.index); ax.set_ylabel('WAPE (lower is better)')
ax.set_title(f'Forecast backtest: moving average wins on validation ({best})', loc='left', fontweight='bold'); ax.legend(frameon=False)
for i, (a, b) in enumerate(zip(p.validation, p.test)): ax.text(i-.2, a+.01, f'{a:.2f}', ha='center', fontsize=9); ax.text(i+.2, b+.01, f'{b:.2f}', ha='center', fontsize=9)
f.tight_layout(); f.savefig('figures/02_forecast.png', dpi=160); plt.close()

# 3 profit
lab = {f'base_stock|naive': 'Reorder rule\n+ naive fcst', 'milp|naive': 'Optimiser\n+ naive fcst', f'base_stock|{best}': f'Reorder rule\n+ {best}', f'milp|{best}': f'Optimiser\n+ {best}', 'myopic perfect-information benchmark': 'One-week perfect-\ninformation benchmark'}
S['lab'] = S.policy.map(lab); cols = [D, A, D, A, B]
f, ax = plt.subplots(figsize=(10, 4.8)); ax.bar(S.lab, S.profit/1000, color=cols)
for i, v in enumerate(S.profit/1000): ax.text(i, v+2, f'{v:,.0f}k', ha='center')
ax.set_ylim(0, S.profit.max()/1000*1.12); ax.set_ylabel('Simulated profit, 26 test weeks (k, model currency)')
ax.set_title('Same demand, budget, storage and forecast: optimiser vs simple reorder rule', loc='left', fontweight='bold')
f.tight_layout(); f.savefig('figures/03_profit.png', dpi=160); plt.close()

# 4 sensitivity
f, ax = plt.subplots(figsize=(9, 4.8)); g = SE.groupby('kappa').gain_pct
ax.fill_between(g.min().index, g.min(), g.max(), color=A, alpha=.2, label='Min to max across 5 cost-assumption seeds')
ax.plot(g.mean().index, g.mean(), 'o-', color=A, lw=2.4, label='Mean of 5 seeds')
ax.scatter(SE.kappa, SE.gain_pct, color=FG, s=12, zorder=3, label='Individual seed (random unit-cost draw)'); ax.legend(frameon=False); ax.set_xlabel('Weekly budget as multiple of typical COGS'); ax.set_ylabel('Optimiser profit gain vs reorder rule (%)')
ax.set_title('Tested scenarios only: optimiser gain grew as the budget tightened', loc='left', fontweight='bold'); f.tight_layout(); f.savefig('figures/04_sensitivity.png', dpi=160); plt.close()

# 5 cumulative diff
a = W[W.policy == f'milp|{best}'].set_index('week').profit; b = W[W.policy == f'base_stock|{best}'].set_index('week').profit
f, ax = plt.subplots(figsize=(10, 4.2)); ax.plot((a-b).cumsum().index, (a-b).cumsum(), color=A, lw=2.4); ax.axhline(0, color=D, lw=1)
ax.set_ylabel('Cumulative profit difference'); ax.set_title('Optimiser minus reorder rule, cumulative by test week (gain arrives in the Nov peak)', loc='left', fontweight='bold')
f.tight_layout(); f.savefig('figures/05_cumulative.png', dpi=160); plt.close()

# 6 pareto
pa = c.execute("select rnk, cum_share from sku_pareto order by rnk").df(); it = c.execute("select * from intermittency").df()
f, ax = plt.subplots(figsize=(8, 4.5)); ax.plot(pa.rnk, pa.cum_share*100, color=C, lw=2.4); ax.set_xlabel('SKUs ranked by revenue'); ax.set_ylabel('Cumulative revenue share (%)')
ax.set_title('Revenue concentration across products', loc='left', fontweight='bold'); f.tight_layout(); f.savefig('figures/06_pareto.png', dpi=160); plt.close()
rr = c.execute("select sum(returned)/sum(gross) from return_rate").fetchone()[0]
cm = c.execute("select sum(rev) filter (where country='United Kingdom')/sum(rev) from country_mix").fetchone()[0]
print(dict(return_value_share=rr, uk_share=cm, top100_share=float(pa.cum_share[99]), n_skus=len(pa), eligible_unit_share=float(M.iloc[:].sum().sum()/agg.sum())))
