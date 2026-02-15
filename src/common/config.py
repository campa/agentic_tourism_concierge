"""
Centralized configuration for the product screening system.
All tunable constants and settings are defined here.
"""

# Proximity filtering
PROXIMITY_RADIUS_KM: float = 20.0

# Semantic exclusion filtering
SEMANTIC_EXCLUSION_THRESHOLD: float = 0.7

# Semantic ranking
TOP_RESULTS_COUNT: int = 5

# Embedding model
EMBEDDING_MODEL_NAME: str = "all-MiniLM-L6-v2"

# LLM settings
LLM_MODEL: str = "llama3.1:8b"

# Database paths
DB_PATH: str = "data/products_screener/products.db"
TABLE_NAME: str = "product_catalog"

# Geocoding - Local lookup table for common tourism cities
CITY_COORDINATES: dict[str, tuple[float, float]] = {
    "venice": (45.4408, 12.3155),
    "rome": (41.9028, 12.4964),
    "florence": (43.7696, 11.2558),
    "milan": (45.4642, 9.1900),
    "naples": (40.8518, 14.2681),
    "barcelona": (41.3851, 2.1734),
    "madrid": (40.4168, -3.7038),
    "paris": (48.8566, 2.3522),
    "london": (51.5074, -0.1278),
    "amsterdam": (52.3676, 4.9041),
    "berlin": (52.5200, 13.4050),
    "vienna": (48.2082, 16.3738),
    "prague": (50.0755, 14.4378),
    "lisbon": (38.7223, -9.1393),
    "athens": (37.9838, 23.7275),
}
