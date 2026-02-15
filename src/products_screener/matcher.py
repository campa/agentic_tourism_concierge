import os

import lancedb

from common.logging_config import get_logger

logger = get_logger("products_screener_matcher")
DB_PATH = os.path.join(os.getcwd(), "data", "products_screener", "products.db")


def screen_products(profile):
    db = lancedb.connect(DB_PATH)
    table = db.open_table("product_catalog")

    # 1. Safely Build SQL constraints
    constraints = [
        f"country = '{profile['sql_constraints']['country']}'",
        f"min_age <= {profile['sql_constraints']['age']}",
        f"max_age >= {profile['sql_constraints']['age']}",
        f"price_amount <= {profile['sql_constraints']['price_max']}",
    ]

    # Handle max_pax only if it is a valid number
    pax = profile["sql_constraints"].get("max_pax")
    if pax is not None and isinstance(pax, int):
        constraints.append(f"max_pax >= {pax}")

    # Add the safety filters
    for term in profile["sql_constraints"].get("excluded_terms", []):
        if term:  # Ensure term is not empty
            constraints.append(f"search_text NOT LIKE '%{term}%'")

    where_clause = " AND ".join(constraints)

    # 2. Execute FTS Search
    # Note: Ensure duckdb is installed via 'uv add duckdb'
    results = (
        table.search(profile["vector_intent"], query_type="fts")
        .where(where_clause)
        .limit(10)
        .to_pandas()
    )

    if not results.empty:
        # Sort by score and drop duplicates of the same product
        results = results.sort_values("_score", ascending=False).drop_duplicates(
            subset=["product_id"]
        )

    return results
