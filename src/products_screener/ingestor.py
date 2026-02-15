import json
import os

import lancedb

from common.logging_config import get_logger

# Init - Module level vars
logger = get_logger("products_screener_ingestor")

# Pointing to the root 'data' directory
DB_PATH = os.path.join(os.getcwd(), "data", "products_screener", "products.db")


def run_ingestion(json_file_path):
    """
    Ingest OCTO specification JSON (https://www.octo.travel/specification) into a flattened LanceDB table.

    What is currently flattened:
        - Product Level: title, description, country, location, tags
        - Option Level: option_name, max_pax, min_pax, availability dates
        - Unit Level: unit_type (Adult/Child), age_restrictions, price_amount

    What is NOT flattened (and why):
        - Full Pricing Schedules: Only the retail price from the first pricing tier is used
          to keep the "Screener" fast
        - Contact Info/Voucher Details: These are "Post-Booking" details not needed for search
        - Deep Redemption Instructions: Kept in description or search_text for keyword matching
          but not given their own columns

    Args:
        json_file_path: Path to the OCTO JSON file containing product data
    """
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    db = lancedb.connect(DB_PATH)

    with open(json_file_path, "r", encoding="utf-8") as f:
        products = json.load(f)

    flattened_rows = []

    for p in products:
        # Common Parent Data (Top-level info)
        parent_info = {
            "product_id": p.get("id"),
            "title": p.get("title"),
            "description": p.get("description", "") or "",
            "country": p.get("country"),
            "location": p.get("location", ""),
            "tags": " ".join(p.get("tags", [])) if isinstance(p.get("tags"), list) else "",
            "highlights": " ".join(p.get("highlights", []))
            if isinstance(p.get("highlights"), list)
            else "",
        }

        # Iterate through every Option (Variants)
        for opt in p.get("options", []):
            option_base = {
                **parent_info,
                "option_id": opt.get("id"),
                "option_name": opt.get("internalName", ""),
                "max_pax": opt.get("restrictions", {}).get("maxPaxCount", 99),
                "min_pax": opt.get("restrictions", {}).get("minPaxCount", 1),
                "start_date": opt.get("availabilityLocalDateStart"),
                "end_date": opt.get("availabilityLocalDateEnd"),
            }

            # Iterate through every Unit (Pricing/Age Categories)
            for unit in opt.get("units", []):
                # Grab price from the first pricing tier found
                pricing = unit.get("pricingFrom", [{}])[0]

                final_row = {
                    **option_base,
                    "unit_id": unit.get("id"),
                    "unit_type": unit.get("type"),  # ADULT, CHILD, etc.
                    "min_age": unit.get("restrictions", {}).get("minAge", 0),
                    "max_age": unit.get("restrictions", {}).get("maxAge", 99),
                    "price_amount": pricing.get("retail", 0),
                    "currency": pricing.get("currency", "EUR"),
                }

                # Create a single blob for Full-Text Search
                final_row["search_text"] = (
                    f"{final_row['title']} {final_row['description']} {final_row['option_name']} {final_row['tags']}"
                )
                flattened_rows.append(final_row)

    table_name = "product_catalog"
    tbl = db.create_table(table_name, data=flattened_rows, mode="overwrite")

    # Index the flattened text
    tbl.create_fts_index("search_text", use_tantivy=True, replace=True)
    logger.info(f"✅ Ingested {len(flattened_rows)} bookable units into {DB_PATH}")


if __name__ == "__main__":
    json_path = os.path.join("data", "products_screener", "mock_products.json")
    run_ingestion(json_path)
