"""
Product Soft Screener Agent

Ranks products using soft preferences:
- Semantic similarity to preference text
- Interest matching

Input: 
- List of (product_id, option_id, unit_id) tuples from hard screener
- SoftPreferences from synthesizer

Output: Ranked list of products with relevance scores
"""

from dataclasses import dataclass
import os

import lancedb
import numpy as np
import pandas as pd

from common.config import (
    DB_PATH,
    EMBEDDING_MODEL_NAME,
    TABLE_NAME,
    TOP_RESULTS_COUNT,
)
from common.logging_config import get_logger
from product_synthesizer.types import SoftPreferences

logger = get_logger("product_soft_screener")

# Cache for embedding model
_embedding_model = None


def _get_embedding_model():
    """Get or create the embedding model (cached)."""
    global _embedding_model
    if _embedding_model is None:
        from lancedb.embeddings import get_registry
        _embedding_model = get_registry().get("sentence-transformers").create(name=EMBEDDING_MODEL_NAME)
    return _embedding_model


def _cosine_similarity(vec1: np.ndarray, vec2: np.ndarray) -> float:
    """Compute cosine similarity between two vectors."""
    dot_product = np.dot(vec1, vec2)
    norm1 = np.linalg.norm(vec1)
    norm2 = np.linalg.norm(vec2)
    if norm1 == 0 or norm2 == 0:
        return 0.0
    return dot_product / (norm1 * norm2)


@dataclass
class SoftScreeningResult:
    """Result from soft screening containing ranked products."""
    
    # List of product dicts with relevance scores, ordered by score descending
    products: list[dict]
    
    # Metadata
    input_count: int
    output_count: int


def load_products_by_ids(
    filtered_ids: list[tuple[str, str, str]]
) -> pd.DataFrame:
    """
    Load products from database by their (product_id, option_id, unit_id) tuples.
    
    Args:
        filtered_ids: List of (product_id, option_id, unit_id) tuples
        
    Returns:
        DataFrame with matching products
    """
    if not filtered_ids:
        return pd.DataFrame()
    
    db_path = os.path.join(os.getcwd(), DB_PATH)
    db = lancedb.connect(db_path)
    table = db.open_table(TABLE_NAME)
    
    # Load all data and filter in pandas (more efficient for multiple IDs)
    all_products = table.to_pandas()
    
    # Create a set of tuples for fast lookup
    id_set = set(filtered_ids)
    
    # Filter to matching rows
    mask = all_products.apply(
        lambda row: (row["product_id"], row["option_id"], row["unit_id"]) in id_set,
        axis=1
    )
    
    return all_products[mask].copy()


def rank_by_preferences(
    products: pd.DataFrame,
    soft_preferences: SoftPreferences,
    top_n: int = TOP_RESULTS_COUNT,
) -> pd.DataFrame:
    """
    Rank products by semantic similarity to soft preferences.
    
    Args:
        products: DataFrame containing product data with 'vector' column
        soft_preferences: SoftPreferences dict with preference_text, interests, etc.
        top_n: Number of top results to return
        
    Returns:
        DataFrame containing top N products ordered by relevance_score,
        deduplicated by product_id (keeping highest score)
    """
    if products.empty:
        logger.info("Soft ranking: no products to rank")
        return products

    # Build preference text
    preference_text = soft_preferences.get("preference_text", "")

    if not preference_text.strip():
        parts = []
        interests = soft_preferences.get("interests", [])
        if interests:
            parts.append(" ".join(interests))
        activity_level = soft_preferences.get("activity_level")
        if activity_level:
            parts.append(activity_level)
        notes = soft_preferences.get("notes")
        if notes:
            parts.append(notes)
        preference_text = " ".join(parts)

    # If no preferences, return with neutral scores
    if not preference_text.strip():
        logger.info("Soft ranking: no preferences provided, returning with neutral scores")
        result = products.copy()
        result["relevance_score"] = 0.5
        return result.head(top_n)

    # Generate embedding for preference text
    try:
        model = _get_embedding_model()
        preference_embedding = model.generate_embeddings([preference_text])[0]
        preference_vec = np.array(preference_embedding)
        use_semantic_ranking = True
    except Exception as e:
        logger.warning(f"Embedding generation failed: {e}. Using neutral scores.")
        use_semantic_ranking = False

    # Compute semantic scores
    semantic_scores = []
    for _, row in products.iterrows():
        if use_semantic_ranking:
            product_vector = row.get("vector")
            if product_vector is None or (
                isinstance(product_vector, (list, np.ndarray)) and len(product_vector) == 0
            ):
                semantic_scores.append(0.0)
            else:
                product_vec = np.array(product_vector)
                similarity = _cosine_similarity(product_vec, preference_vec)
                # Normalize from [-1, 1] to [0, 1]
                normalized_similarity = (similarity + 1) / 2
                semantic_scores.append(normalized_similarity)
        else:
            semantic_scores.append(0.5)

    result = products.copy()
    result["relevance_score"] = semantic_scores
    result["relevance_score"] = result["relevance_score"].clip(0.0, 1.0)

    # Sort by relevance and deduplicate by product_id
    result = result.sort_values("relevance_score", ascending=False)
    result = result.drop_duplicates(subset=["product_id"], keep="first")

    result = result.head(top_n)

    logger.info(f"Soft ranking: {len(products)} -> {len(result)} products (top {top_n})")
    return result


def screen_soft(
    filtered_ids: list[tuple[str, str, str]],
    soft_preferences: SoftPreferences,
    top_n: int = TOP_RESULTS_COUNT,
) -> SoftScreeningResult:
    """
    Apply soft ranking to pre-filtered products.
    
    Args:
        filtered_ids: List of (product_id, option_id, unit_id) from hard screener
        soft_preferences: SoftPreferences dict with ranking criteria
        top_n: Number of top results to return
        
    Returns:
        SoftScreeningResult with ranked products
    """
    input_count = len(filtered_ids)
    logger.info(f"Soft screening input: {input_count} product/option/unit combinations")
    
    if not filtered_ids:
        return SoftScreeningResult(
            products=[],
            input_count=0,
            output_count=0,
        )
    
    # Load products from database
    products_df = load_products_by_ids(filtered_ids)
    logger.info(f"Loaded {len(products_df)} products from database")
    
    if products_df.empty:
        return SoftScreeningResult(
            products=[],
            input_count=input_count,
            output_count=0,
        )
    
    # Apply soft ranking
    ranked_df = rank_by_preferences(products_df, soft_preferences, top_n)
    
    # Convert to list of dicts
    products = ranked_df.to_dict(orient="records")
    
    # Clean up vector field (not needed in output)
    for p in products:
        if "vector" in p:
            del p["vector"]
    
    logger.info(f"Soft screening complete: {len(products)} ranked products")
    
    return SoftScreeningResult(
        products=products,
        input_count=input_count,
        output_count=len(products),
    )
