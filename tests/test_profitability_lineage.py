import pandas as pd

from enterprise_finance.reporting import (
    entity_product_profitability,
    profitability,
    validate_entity_product_profitability,
)


def test_entity_product_profitability_reconciles_to_product_view():
    rows = []
    for month in ["2026-07", "2026-08"]:
        for entity, scale in [("DE01", 1.0), ("US01", 1.5)]:
            rows.append({
                "month": month,
                "entity": entity,
                "division": "Hardware",
                "product": "HW-1",
                "customer": "C1",
                "customer_segment": "Enterprise",
                "revenue": 100 * scale,
                "variable_production_cost": 45 * scale,
                "variable_selling_cost": 5 * scale,
                "fixed_production_cost": 10 * scale,
                "marginal_contribution": 50 * scale,
                "gross_profit": 40 * scale,
                "opex": 8 * scale,
                "quantity": 2 * scale,
            })
    operations = pd.DataFrame(rows)
    product, _ = profitability(operations, "2026-08")
    entity_product = entity_product_profitability(operations, "2026-08")
    additive = ["revenue", "marginal_contribution", "gross_profit", "opex", "operating_contribution"]
    rolled = entity_product.groupby(["division", "product"], as_index=False)[additive].sum()
    pd.testing.assert_frame_equal(product[["division", "product", *additive]], rolled)
    assert not entity_product.duplicated(["entity", "division", "product"]).any()
    assert set(entity_product.entity) == {"DE01", "US01"}
    checks = validate_entity_product_profitability(product, entity_product)
    assert checks["passed"]
    assert checks["entity_product_profitability_max_gap"] == 0.0


def test_entity_product_validation_rejects_a_hidden_gap():
    operations = pd.DataFrame([{
        "month": "2026-08", "entity": "DE01", "division": "Software", "product": "SW-1",
        "customer": "C1", "customer_segment": "Enterprise", "revenue": 100.0,
        "variable_production_cost": 20.0, "variable_selling_cost": 5.0, "fixed_production_cost": 10.0,
        "marginal_contribution": 75.0, "gross_profit": 65.0, "opex": 15.0, "quantity": 1.0,
    }])
    product, _ = profitability(operations, "2026-08")
    entity_product = entity_product_profitability(operations, "2026-08")
    entity_product.loc[0, "revenue"] += 1.0
    checks = validate_entity_product_profitability(product, entity_product)
    assert not checks["passed"]
    assert checks["entity_product_profitability_max_gap"] == 1.0
