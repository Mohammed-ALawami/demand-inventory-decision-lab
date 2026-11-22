"""All SIMULATED operating assumptions live here. None come from the UCI data."""
CFG = dict(
    n_skus=80,                 # eligible SKUs kept
    test_weeks=26,             # final weeks used for out-of-sample evaluation
    valid_weeks=26,            # weeks before test used to choose the forecast model / tune z
    cost_ratio_range=(0.50, 0.75),  # unit cost = ratio * median selling price (ASSUMED, per-SKU, seeded)
    holding_rate=0.03,         # per week, fraction of unit cost on leftover stock (capital + obsolescence, ASSUMED)
    pack_sizes=(6, 12, 24),    # case-pack by training demand level (ASSUMED)
    budget_kappa=1.0,          # weekly purchasing budget = kappa * mean weekly COGS in training
    storage_lambda=1.0,        # capacity = lambda * 2 weeks of mean demand volume
    n_scen=5, lead_weeks=1, seed=7,
)
