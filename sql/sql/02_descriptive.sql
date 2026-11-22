CREATE OR REPLACE TABLE monthly AS
SELECT date_trunc('month', ts) AS month, SUM(qty*price) AS gross_revenue, COUNT(DISTINCT invoice) AS invoices, COUNT(DISTINCT sku) AS active_skus
FROM sales GROUP BY 1 ORDER BY 1;
CREATE OR REPLACE TABLE return_rate AS
SELECT s.month, s.gross, COALESCE(r.ret,0) AS returned, COALESCE(r.ret,0)/s.gross AS return_value_share FROM
 (SELECT date_trunc('month', ts) AS month, SUM(qty*price) AS gross FROM sales GROUP BY 1) s
 LEFT JOIN (SELECT date_trunc('month', ts) AS month, SUM(-qty*price) AS ret FROM returns GROUP BY 1) r USING (month) ORDER BY 1;
CREATE OR REPLACE TABLE sku_pareto AS
SELECT sku, rev, SUM(rev) OVER (ORDER BY rev DESC) / SUM(rev) OVER () AS cum_share, ROW_NUMBER() OVER (ORDER BY rev DESC) AS rnk
FROM (SELECT sku, SUM(qty*price) AS rev FROM sales GROUP BY 1);
CREATE OR REPLACE TABLE intermittency AS
SELECT sku, COUNT(DISTINCT week) AS active_weeks, SUM(units) AS units FROM weekly GROUP BY 1;
CREATE OR REPLACE TABLE country_mix AS
SELECT country, SUM(qty*price) AS rev FROM sales GROUP BY 1 ORDER BY rev DESC;
