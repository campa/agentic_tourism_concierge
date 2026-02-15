"""
Product Hard Screener Agent

Filters products using hard constraints:
- SQL filtering (country, dates, age, pax)
- Proximity filtering (distance from target location)
- Semantic exclusion filtering (accessibility, diet, medical, fears)

Input: HardConstraints from synthesizer
Output: List of (product_id, option_id, unit_id) tuples that pass all filters
"""

from dataclasses import dataclass

import lancedb
import numpy as np
import pandas as pd

from common.config import (
    DB_PATH,
    EMBEDDING_MODEL_NAME,
    PROXIMITY_RADIUS_KM,
    SEMANTIC_EXCLUSION_THRESHOLD,
    TABLE_NAME,
)
from common.geocoding import geocode
from common.logging_config import get_logger
from product_synthesizer.types import HardConstraints, SemanticExclusions

logger = get_logger("product_hard_screener")

# Cache for embedding model
_embedding_model = None


def _get_embedding_model():
    """Get or create the embedding model (cached)."""
    global _embedding_model
    if _embedding_model is None:
        from lancedb.embeddings import get_registry
        _embedding_model = get_registry().get("sentence-transformers").create(name=EMBEDDING_MODEL_NAME)
    return _embedding_model


@dataclass
class HardScreeningResult:
    """Result from hard screening containing filtered product references."""

    # List of (product_id, option_id, unit_id) tuples
    filtered_ids: list[tuple[str, str, str]]

    # Metadata about filtering
    initial_count: int
    after_sql_count: int
    after_proximity_count: int
    after_exclusion_count: int


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate the great-circle distance between two points in kilometers."""
    R = 6371  # Earth's radius in kilometers

    lat1_rad = np.radians(lat1)
    lat2_rad = np.radians(lat2)
    delta_lat = np.radians(lat2 - lat1)
    delta_lon = np.radians(lon2 - lon1)

    a = np.sin(delta_lat / 2) ** 2 + np.cos(lat1_rad) * np.cos(lat2_rad) * np.sin(delta_lon / 2) ** 2
    c = 2 * np.arctan2(np.sqrt(a), np.sqrt(1 - a))

    return R * c


def build_sql_where(hard_constraints: HardConstraints) -> str:
    """Build SQL WHERE clause from hard constraints."""
    conditions: list[str] = []

    # Country filter
    country = hard_constraints.get("country")
    if country:
        safe_country = country.replace("'", "''")
        conditions.append(f"country = '{safe_country}'")

    # Date overlap filter
    holiday_begin = hard_constraints.get("holiday_begin_date")
    holiday_end = hard_constraints.get("holiday_end_date")

    if holiday_begin and holiday_end:
        conditions.append(f"(start_date IS NULL OR start_date <= '{holiday_end}')")
        conditions.append(f"(end_date IS NULL OR end_date >= '{holiday_begin}')")
    elif holiday_begin:
        conditions.append(f"(end_date IS NULL OR end_date >= '{holiday_begin}')")
    elif holiday_end:
        conditions.append(f"(start_date IS NULL OR start_date <= '{holiday_end}')")

    # Age filter
    age = hard_constraints.get("age")
    if age is not None and isinstance(age, int):
        conditions.append(f"(min_age IS NULL OR min_age <= {age})")
        conditions.append(f"(max_age IS NULL OR max_age >= {age})")

    # Max pax filter
    max_pax = hard_constraints.get("max_pax")
    if max_pax is not None and isinstance(max_pax, int):
        conditions.append(f"(max_pax IS NULL OR max_pax >= {max_pax})")

    if conditions:
        return " AND ".join(conditions)
    return "1=1"


def filter_by_proximity(
    products: pd.DataFrame,
    target_lat: float,
    target_lon: float,
    radius_km: float = PROXIMITY_RADIUS_KM,
) -> pd.DataFrame:
    """Filter products within a specified radius of the target location."""
    if products.empty:
        return products

    distances = []
    for _, row in products.iterrows():
        product_lat = row.get("latitude")
        product_lon = row.get("longitude")

        if pd.isna(product_lat) or pd.isna(product_lon):
            location = row.get("location")
            if location and isinstance(location, str) and location.strip():
                coords = geocode(location)
            else:
                coords = None
            if coords:
                product_lat = coords["latitude"]
                product_lon = coords["longitude"]
            else:
                distances.append(float("inf"))
                continue

        dist = haversine_distance(target_lat, target_lon, product_lat, product_lon)
        distances.append(dist)

    result = products.copy()
    result["distance_km"] = distances
    result = result[result["distance_km"] <= radius_km]

    logger.info(f"Proximity filter: {len(products)} -> {len(result)} products (within {radius_km}km)")
    return result


def _cosine_similarity(vec1: np.ndarray, vec2: np.ndarray) -> float:
    """Compute cosine similarity between two vectors."""
    dot_product = np.dot(vec1, vec2)
    norm1 = np.linalg.norm(vec1)
    norm2 = np.linalg.norm(vec2)
    if norm1 == 0 or norm2 == 0:
        return 0.0
    return dot_product / (norm1 * norm2)


def _combine_exclusion_terms(semantic_exclusions: SemanticExclusions) -> str:
    """Combine all semantic exclusion terms into a single text string."""
    all_terms = []
    for terms in semantic_exclusions.values():
        if terms and isinstance(terms, list):
            all_terms.extend(terms)
    return " ".join(all_terms)


def filter_by_semantic_exclusion(
    products: pd.DataFrame,
    semantic_exclusions: SemanticExclusions,
    threshold: float = SEMANTIC_EXCLUSION_THRESHOLD,
) -> pd.DataFrame:
    """Filter out products that match semantic exclusion terms."""
    if products.empty:
        return products

    exclusion_text = _combine_exclusion_terms(semantic_exclusions)
    if not exclusion_text.strip():
        result = products.copy()
        result["exclusion_similarity"] = 0.0
        return result

    try:
        model = _get_embedding_model()
        exclusion_embedding = model.generate_embeddings([exclusion_text])[0]
        exclusion_vec = np.array(exclusion_embedding)
    except Exception as e:
        logger.warning(f"Embedding generation failed: {e}. Skipping semantic exclusion.")
        result = products.copy()
        result["exclusion_similarity"] = 0.0
        return result

    similarities = []
    for _, row in products.iterrows():
        product_vector = row.get("vector")
        if product_vector is None or (isinstance(product_vector, (list, np.ndarray)) and len(product_vector) == 0):
            similarities.append(0.0)
            continue

        product_vec = np.array(product_vector)
        similarity = _cosine_similarity(product_vec, exclusion_vec)
        similarities.append(similarity)

    result = products.copy()
    result["exclusion_similarity"] = similarities
    result = result[result["exclusion_similarity"] < threshold]

    excluded_count = len(products) - len(result)
    logger.info(f"Semantic exclusion: {len(products)} -> {len(result)} products ({excluded_count} excluded)")
    return result


def screen_hard(hard_constraints: HardConstraints) -> HardScreeningResult:
    """
    Apply hard filtering to products and return matching IDs.

    Args:
        hard_constraints: HardConstraints dict with filtering criteria

    Returns:
        HardScreeningResult with filtered (product_id, option_id, unit_id) tuples
    """
    import os

    # Connect to database
    db_path = os.path.join(os.getcwd(), DB_PATH)
    db = lancedb.connect(db_path)
    table = db.open_table(TABLE_NAME)

    # Phase 1: SQL filtering
    where_clause = build_sql_where(hard_constraints)
    logger.info(f"Hard screening SQL WHERE: {where_clause}")

    products_df = table.search().where(where_clause).to_pandas()
    initial_count = len(table.to_pandas())
    after_sql_count = len(products_df)
    logger.info(f"Phase 1 (SQL Filter): {initial_count} -> {after_sql_count} products")

    if products_df.empty:
        return HardScreeningResult(
            filtered_ids=[],
            initial_count=initial_count,
            after_sql_count=0,
            after_proximity_count=0,
            after_exclusion_count=0,
        )

    # Phase 2: Proximity filtering
    target_lat = hard_constraints.get("target_latitude")
    target_lon = hard_constraints.get("target_longitude")

    # Fall back to accommodation coordinates if target not specified
    if target_lat is None or target_lon is None:
        target_lat = hard_constraints.get("accommodation_latitude")
        target_lon = hard_constraints.get("accommodation_longitude")

    if target_lat is not None and target_lon is not None:
        products_df = filter_by_proximity(products_df, target_lat, target_lon)
        after_proximity_count = len(products_df)
        logger.info(f"Phase 2 (Proximity Filter): {after_sql_count} -> {after_proximity_count} products")
    else:
        after_proximity_count = after_sql_count
        logger.info("Phase 2 skipped: no target coordinates")

    if products_df.empty:
        return HardScreeningResult(
            filtered_ids=[],
            initial_count=initial_count,
            after_sql_count=after_sql_count,
            after_proximity_count=0,
            after_exclusion_count=0,
        )

    # Phase 3: Semantic exclusion filtering
    semantic_exclusions = hard_constraints.get("semantic_exclusions", {})
    has_exclusions = any(
        terms for terms in semantic_exclusions.values()
        if terms and isinstance(terms, list)
    )

    if has_exclusions:
        products_df = filter_by_semantic_exclusion(products_df, semantic_exclusions)
        after_exclusion_count = len(products_df)
        logger.info(f"Phase 3 (Semantic Exclusion): {after_proximity_count} -> {after_exclusion_count} products")
    else:
        after_exclusion_count = after_proximity_count
        logger.info("Phase 3 skipped: no semantic exclusions")

    # Extract unique (product_id, option_id, unit_id) tuples
    if products_df.empty:
        filtered_ids = []
    else:
        filtered_ids = [
            (row["product_id"], row["option_id"], row["unit_id"])
            for _, row in products_df.iterrows()
        ]

    logger.info(f"Hard screening complete: {len(filtered_ids)} product/option/unit combinations")

    return HardScreeningResult(
        filtered_ids=filtered_ids,
        initial_count=initial_count,
        after_sql_count=after_sql_count,
        after_proximity_count=after_proximity_count,
        after_exclusion_count=after_exclusion_count,
    )
