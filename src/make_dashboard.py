import base64, pandas as pd
S = pd.read_csv('reports/main_results.csv'); SE = pd.read_csv('reports/sensitivity.csv')
img = lambda f: 'data:image/png;base64,' + base64.b64encode(open(f'figures/{f}', 'rb').read()).decode()
g = SE.groupby('kappa').gain_pct.mean()
cards = ''.join(f'<div class=c><b>{v:+.1f}%</b><span>mean optimiser gain (5 cost seeds) at {k}x budget</span></div>' for k, v in g.items())
figs = ''.join(f'<a class=w href="figures/{f}" target=_blank><img src="{img(f)}"><span>Tap to open full size</span></a>' for f in ['03_profit.png','04_sensitivity.png','05_cumulative.png','02_forecast.png','01_demand.png','06_pareto.png'])
open('dashboard.html', 'w').write(f"""<!doctype html><meta charset=utf-8><meta name=viewport content="width=device-width,initial-scale=1"><title>Demand &amp; Inventory Decision Lab</title>
<style>body{{background:#0f1419;color:#e6edf3;font:16px system-ui;margin:0;padding:24px;max-width:1100px;margin:auto}}h1{{margin:0}}.s{{color:#94a3b8}}
.g{{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:12px;margin:20px 0}}.c{{background:#161d26;border-radius:12px;padding:16px}}.c b{{font-size:30px;color:#2dd4bf;display:block}}
img{{width:100%;height:auto;display:block;border-radius:12px}}.w{{display:block;margin:12px 0;color:#94a3b8;font-size:13px;text-decoration:none}}.n{{background:#1c1917;border-left:4px solid #f59e0b;padding:12px;border-radius:8px}}</style>
<h1>Demand &amp; Inventory Decision Lab</h1><p class=s>Real UCI Online Retail II sales, simulated costs/storage/lead time. 26 out-of-sample weeks.</p>
<div class=g>{cards}</div>
<p class=n>Units sold are a demand proxy, revenue is not profit, and costs, capacity and lead times are simulated assumptions. UK gift wholesaler, not tea or Egypt. At the default budget the gain (+1.1%) is not statistically proven: a block bootstrap interval includes zero. Larger gains appear only when the budget is tight.</p>{figs}""")
