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
LLM_MODEL: str = "qwen3:8b"

# LLM model parameters (Ollama options)
# Context window size - lower values reduce TTFT (time to first token)
LLM_NUM_CTX: int = 4096

# Temperature - lower values = more deterministic, faster responses
LLM_TEMPERATURE: float = 0.3

# Repeat penalty - Qwen 3 is sensitive to this; 1.1+ slows it down
LLM_REPEAT_PENALTY: float = 1.0

# Top-p (nucleus sampling) - lower values can speed up generation
LLM_TOP_P: float = 0.9

# Top-k sampling - limits token choices
LLM_TOP_K: int = 40

# Number of tokens to predict (-1 = infinite, -2 = fill context)
LLM_NUM_PREDICT: int = -1

# System prompt for speed optimization (optional, set to None to disable)
LLM_SYSTEM_PROMPT: str | None = None

# Qwen 3 "Thinking" Mode Optimization
# Qwen 3 has an integrated Chain-of-Thought (CoT) mode that adds ~200-400ms latency
# Setting this to True forces "Direct Response" mode, skipping internal reasoning
# Requires Ollama 0.16.1+ which supports the /no_think flag
LLM_DISABLE_THINKING: bool = False

# Alternative: Use a system prompt to disable thinking (for older Ollama versions)
# This is used when LLM_DISABLE_THINKING is True but /no_think flag isn't available
LLM_NO_THINK_PROMPT: str = (
    "Respond directly. Do not use internal reasoning tokens unless calculating complex JSON logic."
)

# KV Cache Quantization (Ollama environment variable)
# Options: None (default f16), "q4_0" (fastest, slight quality loss), "q8_0" (balanced)
# IMPORTANT: This requires setting OLLAMA_KV_CACHE_TYPE env var before starting Ollama
LLM_KV_CACHE_TYPE: str | None = None

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
