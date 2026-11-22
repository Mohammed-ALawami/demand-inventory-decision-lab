-- Raw -> clean line items. Rules are counted in reports/cleaning_audit.csv
CREATE OR REPLACE TABLE raw AS SELECT * FROM read_csv_auto('data/raw/online_retail_II.csv', header=true);
CREATE OR REPLACE TABLE lines AS
SELECT "Invoice" AS invoice, "StockCode" AS sku, "Description" AS description,
       "Quantity" AS qty, CAST("InvoiceDate" AS TIMESTAMP) AS ts, "Price" AS price,
       "Customer ID" AS customer, "Country" AS country,
       CAST("Invoice" AS VARCHAR) LIKE 'C%' AS is_cancel,
       CAST("StockCode" AS VARCHAR) ~ '^[0-9]{5}' AS is_product_code
FROM raw;
-- Product sales only: positive qty, positive price, real product stock code
CREATE OR REPLACE TABLE sales AS
SELECT *, date_trunc('week', ts) AS week FROM lines
WHERE NOT is_cancel AND qty>0 AND price>0 AND is_product_code;
CREATE OR REPLACE TABLE returns AS
SELECT *, date_trunc('week', ts) AS week FROM lines
WHERE is_cancel AND qty<0 AND is_product_code;
-- Weekly SKU demand = units sold (a sales proxy, not true demand: no stockout data)
CREATE OR REPLACE TABLE weekly AS
SELECT sku, week, SUM(qty) AS units, SUM(qty*price) AS revenue, COUNT(DISTINCT invoice) AS orders
FROM sales GROUP BY 1,2;
CREATE OR REPLACE TABLE sku_price AS
SELECT sku, median(price) AS med_price, arg_max(description, ts) AS description FROM sales GROUP BY 1;
