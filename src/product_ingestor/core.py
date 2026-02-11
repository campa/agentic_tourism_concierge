"""
Product Ingestor - ingests OCTO specification JSON into LanceDB.

Flattens the hierarchical OCTO structure (Product -> Option -> Unit) into
a searchable table with vector embeddings for semantic search.
"""

import json
import os
from typing import Optional

import lancedb
from lancedb.embeddings import get_registry
from lancedb.pydantic import LanceModel, Vector

from common.config import DB_PATH, EMBEDDING_MODEL_NAME, TABLE_NAME
from common.logging_config import get_logger

logger = get_logger("product_ingestor")

# Initialize embedding model
embedding_func = get_registry().get("sentence-transformers").create(name=EMBEDDING_MODEL_NAME)


class ProductCatalog(LanceModel):
    """
    LanceDB schema for product catalog with automatic embedding generation.

    Note: Many fields are Optional to handle real-world OCTO data where
    suppliers may not provide all fields.
    """

    # Product-level fields
    product_id: str
    title: str
    description: Optional[str] = None
    country: Optional[str] = None
    location: Optional[str] = None
    address: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    tags: Optional[str] = None
    highlights: Optional[str] = None
    faq_text: Optional[str] = None

    # Option-level fields
    option_id: str
    option_name: Optional[str] = None
    max_pax: Optional[int] = None
    min_pax: Optional[int] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None

    # Unit-level fields
    unit_id: str
    unit_type: Optional[str] = None  # Supplier-defined
    min_age: Optional[int] = None
    max_age: Optional[int] = None
    price_amount: Optional[int] = None
    currency: Optional[str] = None

    # Search fields with embedding
    search_text: str = embedding_func.SourceField()
    vector: Vector(embedding_func.ndims()) = embedding_func.VectorField()


def _extract_faq_text(faqs: list[dict] | None) -> str:
    """Extract and flatten FAQ content into a searchable text field."""
    if not faqs:
        return ""
    faq_parts = []
    for faq in faqs:
        question = faq.get("question", "")
        answer = faq.get("answer", "")
        if question or answer:
            faq_parts.append(f"{question} {answer}")
    return " ".join(faq_parts)



def run_ingestion(json_file_path: str) -> None:
    """
    Ingest OCTO specification JSON into a flattened LanceDB table.

    Args:
        json_file_path: Path to the OCTO JSON file containing product data
    """
    db_path = os.path.join(os.getcwd(), DB_PATH)
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    db = lancedb.connect(db_path)

    with open(json_file_path, "r", encoding="utf-8") as f:
        products = json.load(f)

    flattened_rows = []

    for p in products:
        product_id = p.get("id")
        title = p.get("title")
        if not product_id or not title:
            logger.warning(f"Skipping product with missing id or title: {product_id}")
            continue

        faq_text = _extract_faq_text(p.get("faqs"))

        parent_info = {
            "product_id": product_id,
            "title": title,
            "description": p.get("description") or None,
            "country": p.get("country") or None,
            "location": p.get("location") or None,
            "address": p.get("address") or None,
            "latitude": p.get("latitude"),
            "longitude": p.get("longitude"),
            "tags": " ".join(p.get("tags", [])) if p.get("tags") else None,
            "highlights": " ".join(p.get("highlights", [])) if p.get("highlights") else None,
            "faq_text": faq_text or None,
        }

        for opt in p.get("options", []):
            restrictions = opt.get("restrictions") or {}
            option_base = {
                **parent_info,
                "option_id": opt.get("id"),
                "option_name": opt.get("internalName") or None,
                "max_pax": restrictions.get("maxPaxCount"),
                "min_pax": restrictions.get("minPaxCount"),
                "start_date": opt.get("availabilityLocalDateStart"),
                "end_date": opt.get("availabilityLocalDateEnd"),
            }

            for unit in opt.get("units", []):
                pricing_list = unit.get("pricingFrom") or []
                pricing = pricing_list[0] if pricing_list else {}
                unit_restrictions = unit.get("restrictions") or {}

                final_row = {
                    **option_base,
                    "unit_id": unit.get("id"),
                    "unit_type": unit.get("type"),
                    "min_age": unit_restrictions.get("minAge"),
                    "max_age": unit_restrictions.get("maxAge"),
                    "price_amount": pricing.get("retail"),
                    "currency": pricing.get("currency"),
                }

                final_row["search_text"] = " ".join(
                    filter(
                        None,
                        [
                            final_row["title"],
                            final_row["description"],
                            final_row["option_name"],
                            final_row["tags"],
                            final_row["highlights"],
                            final_row["faq_text"],
                        ],
                    )
                )
                flattened_rows.append(final_row)

    tbl = db.create_table(TABLE_NAME, schema=ProductCatalog, mode="overwrite")

    logger.info(f"Generating embeddings for {len(flattened_rows)} products...")
    tbl.add(flattened_rows)

    tbl.create_fts_index("search_text", use_tantivy=True, replace=True)
    logger.info(f"Ingested {len(flattened_rows)} bookable units into {db_path}")


if __name__ == "__main__":
    json_path = os.path.join("data", "products_screener", "mock_products.json")
    run_ingestion(json_path)
