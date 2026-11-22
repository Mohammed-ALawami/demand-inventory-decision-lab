#!/usr/bin/env bash
set -euo pipefail
mkdir -p data/raw reports figures powerbi
if [ ! -f data/raw/online_retail_II.csv ]; then
  python3 - <<'PY'
import urllib.request, zipfile
urllib.request.urlretrieve("https://archive.ics.uci.edu/static/public/502/online+retail+ii.zip", "data/raw/oro.zip")
zipfile.ZipFile("data/raw/oro.zip").extractall("data/raw")
PY
  python3 -c "import pandas as pd; x=pd.read_excel('data/raw/online_retail_II.xlsx',sheet_name=None); pd.concat(x.values()).to_csv('data/raw/online_retail_II.csv',index=False)"
fi
python3 - <<'PY'
import duckdb, csv
c=duckdb.connect('data/lab.duckdb'); c.execute(open('sql/01_clean.sql').read())
a=c.execute("""select 'raw rows',count(*) from lines union all select 'cancellation invoices (C*)',count(*) from lines where is_cancel union all
select 'non-product stock codes',count(*) from lines where not is_product_code union all select 'qty<=0 non-cancel',count(*) from lines where not is_cancel and qty<=0 union all
select 'price<=0',count(*) from lines where price<=0 union all select 'missing customer',count(*) from lines where customer is null union all select 'kept sales lines',count(*) from sales""").fetchall()
csv.writer(open('reports/cleaning_audit.csv','w')).writerows([('rule','rows')]+a)
PY
python3 src/run_experiments.py
python3 src/make_figures.py
python3 src/export_powerbi.py
python3 src/make_dashboard.py
python3 tests/test_lab.py
