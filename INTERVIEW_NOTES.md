# Interview notes

**30-second pitch.** "I took two years of real wholesale invoices, cleaned them in SQL, forecast weekly demand for 80 products, then built an integer optimisation that chooses how many cases to order under a budget and storage limit. I tested it on 26 weeks it never saw against a fair reorder-point rule. The gain was small and statistically unproven with a loose budget (+1%) and larger when cash was tight (+8%). Costs and lead times are simulated, and I say so."

**Likely questions**
- *Why not just use the better forecast?* Naive and MA8 give nearly the same profit. Error is dominated by lumpy wholesale orders. The forecast only matters if the decision uses it.
- *Is the optimiser really better?* Slightly at default budget; a block-bootstrap interval includes zero. Clear when budget binds. I report both.
- *What would you change with real company data?* Replace simulated cost, lead time, capacity; use uncensored demand (stockout flags); multi-week horizon; supplier MOQs and price breaks.
- *Data leakage?* Eligibility, model choice and `z` use only pre-test data; a test checks forecasts ignore future values.
- *Why not LP?* Case packs are integers; HiGHS MILP solves each week in well under a second.
- *Why does the perfect-foresight bound matter?* It is a one-week perfect-information reference, not a proven upper bound; it shows roughly how much is lost to demand uncertainty.
- *What is wrong with revenue as demand?* Sold units hide lost sales, so demand is understated when stock ran out.
