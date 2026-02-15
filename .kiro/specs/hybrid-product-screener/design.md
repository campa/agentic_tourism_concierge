# Design Document: Hybrid Product Screener

## Overview

This design transforms the existing keyword-based Full-Text Search (FTS) product screener into a hybrid multi-phase screening system. The new architecture separates hard constraints (feasibility filters) from soft preferences (semantic ranking) to eliminate semantic mismatches like returning "Colosseum tour in Rome" when the user wants "boat tour in Venice".

The hybrid approach uses:
- **Phase 1**: SQL WHERE clauses for exact-match constraints (country, dates, age, group size)
- **Phase 1b**: Haversine distance calculation for proximity filtering
- **Phase 1c**: Vector similarity for semantic exclusion (accessibility, diet, medical, fears)
- **Phase 2**: Vector similarity for semantic ranking by soft preferences

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              INPUT LAYER                                     │
│  ┌──────────────────┐    ┌──────────────────┐                               │
│  │   Personal Info  │    │   Holiday Info   │                               │
│  │  - accessibility │    │  - location      │                               │
│  │  - diet/medical  │    │  - dates         │                               │
│  │  - fears         │    │  - accommodation │                               │
│  │  - interests     │    │  - budget        │                               │
│  └────────┬─────────┘    └────────┬─────────┘                               │
└───────────┼───────────────────────┼─────────────────────────────────────────┘
            │                       │
            ▼                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                            SYNTHESIZER                                       │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │  LLM (Llama 3.1:8b) + Geocoding Service                              │   │
│  │  Outputs: hard_constraints + soft_preferences                        │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
            │
            ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  PHASE 1: SQL FILTER (Exact Match)                                          │
│  WHERE country='IT' AND start_date <= '2025-10-27' AND ...                  │
│  ───────────────────────────────────────────────────────────────────────    │
│  Products: 1000 → 150                                                        │
└─────────────────────────────────────────────────────────────────────────────┘
            │
            ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  PHASE 1b: PROXIMITY FILTER (Haversine Distance)                            │
│  distance(product, target) <= PROXIMITY_RADIUS_KM (20km)                    │
│  ───────────────────────────────────────────────────────────────────────    │
│  Products: 150 → 45                                                          │
└─────────────────────────────────────────────────────────────────────────────┘
            │
            ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  PHASE 1c: SEMANTIC EXCLUSION FILTER (Vector Similarity)                    │
│  Exclude products similar to: "stairs, heights, smoke, gluten..."           │
│  ───────────────────────────────────────────────────────────────────────    │
│  Products: 45 → 30                                                           │
└─────────────────────────────────────────────────────────────────────────────┘
            │
            ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  PHASE 2: SEMANTIC RANKING (Vector Similarity)                              │
│  Rank by similarity to: "romantic boat tour history art relaxing"           │
│  ───────────────────────────────────────────────────────────────────────    │
│  Products: 30 → Top 5 (ordered by relevance_score)                          │
└─────────────────────────────────────────────────────────────────────────────┘
            │
            ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              OUTPUT                                          │
│  Top 5 Products with relevance_score (0.0 - 1.0)                            │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Data Flow Diagram

```
User Input ──► Synthesizer ──┬──► hard_constraints ──► Phase 1: SQL ──► Phase 1b: Proximity ──► Phase 1c: Exclusion ──┐
                             │                                                                                         │
                             └──► soft_preferences ─────────────────────────────────────────► Phase 2: Ranking ◄───────┘
                                                                                                      │
                                                                                                      ▼
                                                                                               Top 5 Results
```

## Components and Interfaces

### 0. Configuration (`config.py`)

Centralized configuration for all tunable values. Allows easy adjustment across environments without changing core logic.

```python
"""
Centralized configuration for the hybrid product screener.
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
```

### 1. Synthesizer (`synthesizer.py`)

Transforms user input into structured search profile with separate hard_constraints and soft_preferences.

```python
class SynthesizerOutput(TypedDict):
    hard_constraints: HardConstraints
    soft_preferences: SoftPreferences

class HardConstraints(TypedDict):
    country: str                          # 2-letter ISO code
    target_latitude: float | None         # City center coordinates
    target_longitude: float | None
    accommodation_latitude: float | None  # Accommodation coordinates (priority)
    accommodation_longitude: float | None
    holiday_begin_date: str | None        # YYYY-MM-DD
    holiday_end_date: str | None          # YYYY-MM-DD
    not_available_date_times: list[str]   # ISO datetime strings
    age: int | None
    max_pax: int | None
    semantic_exclusions: SemanticExclusions

class SemanticExclusions(TypedDict):
    accessibility: list[str]  # e.g., ["stairs", "steps", "climbing", "steep"]
    diet: list[str]           # e.g., ["wheat", "bread", "pasta", "gluten"]
    medical: list[str]        # e.g., ["smoke", "dust", "fumes", "pollution"]
    fears: list[str]          # e.g., ["tower", "rooftop", "cliff", "heights"]

class SoftPreferences(TypedDict):
    preference_text: str      # Combined text for embedding
    interests: list[str]      # e.g., ["history", "art", "architecture"]
    activity_level: str       # e.g., "sedentary", "moderate", "active"
    sports: list[str]         # e.g., ["golf", "tennis"]
    languages: list[str]      # e.g., ["English", "Italian"]
    price_max: int | None     # Budget in cents
    notes: str | None         # Free-form notes for semantic matching
```

**Interface:**
```python
def synthesize_profile(personal_info: dict, holiday_info: dict) -> SynthesizerOutput:
    """
    Transform user input into structured search profile.
    Uses LLM to extract and categorize constraints/preferences.
    Uses geocoding to resolve locations to coordinates.
    """
    pass
```

### 2. Geocoding Service (`geocoding.py`)

Resolves city/address names to latitude/longitude coordinates using the local lookup table from `config.py`.

```python
from config import CITY_COORDINATES

class Coordinates(TypedDict):
    latitude: float
    longitude: float

# Module-level cache for runtime lookups
_geocode_cache: dict[str, Coordinates] = {}

def geocode(location: str) -> Coordinates | None:
    """
    Resolve location string to coordinates.
    Uses local CITY_COORDINATES lookup table from config.
    Caches results to avoid repeated string parsing.
    Falls back to None if city not in lookup table.
    """
    pass

def clear_cache() -> None:
    """Clear the geocode cache."""
    pass
```

### 3. Feasibility Filter (`matcher.py`)

Applies Phase 1, 1b, and 1c filtering. Uses constants from `config.py`.

```python
from config import PROXIMITY_RADIUS_KM, SEMANTIC_EXCLUSION_THRESHOLD

def build_sql_where(hard_constraints: HardConstraints) -> str:
    """
    Build SQL WHERE clause from hard constraints.
    Handles: country, dates, age, max_pax.
    """
    pass

def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate distance in km between two coordinates using Haversine formula.
    """
    pass

def filter_by_proximity(
    products: pd.DataFrame,
    target_lat: float,
    target_lon: float,
    radius_km: float = PROXIMITY_RADIUS_KM
) -> pd.DataFrame:
    """
    Filter products within radius of target location.
    Geocodes product locations if coordinates missing.
    """
    pass

def filter_by_semantic_exclusion(
    products: pd.DataFrame,
    exclusion_embedding: list[float],
    threshold: float = SEMANTIC_EXCLUSION_THRESHOLD
) -> pd.DataFrame:
    """
    Filter products semantically similar to exclusion terms.
    Products with similarity > threshold are excluded.
    """
    pass
```

### 4. Semantic Ranker (`matcher.py`)

Applies Phase 2 semantic ranking.

```python
def rank_by_preferences(
    products: pd.DataFrame,
    preference_embedding: list[float],
    soft_preferences: SoftPreferences
) -> pd.DataFrame:
    """
    Rank products by semantic similarity to preferences.
    Combines vector similarity with price scoring.
    Returns top 5 products ordered by combined score.
    """
    pass

def compute_price_score(price: int, budget: int | None) -> float:
    """
    Compute price score (0-1).
    Higher score for lower price relative to budget.
    Returns 1.0 if no budget specified.
    """
    pass
```

### 5. Ingestor (`ingestor.py`)

Enhanced to capture all OCTO fields and generate embeddings. Uses model name from `config.py`.

```python
from lancedb.embeddings import get_registry
from config import EMBEDDING_MODEL_NAME, DB_PATH, TABLE_NAME

# Use sentence-transformers for embeddings
embedding_model = get_registry().get("sentence-transformers").create(
    name=EMBEDDING_MODEL_NAME
)

class ProductRow(TypedDict):
    # Product-level
    product_id: str
    title: str
    description: str
    country: str
    location: str
    address: str | None
    latitude: float | None
    longitude: float | None
    tags: str
    highlights: str
    
    # Option-level
    option_id: str
    option_name: str
    max_pax: int
    min_pax: int
    start_date: str | None
    end_date: str | None
    
    # Unit-level
    unit_id: str
    unit_type: str
    min_age: int
    max_age: int
    price_amount: int
    currency: str
    
    # Search fields
    search_text: str
    faq_text: str
    vector: list[float]  # Auto-generated embedding

def run_ingestion(json_file_path: str) -> None:
    """
    Ingest OCTO products into LanceDB with embeddings.
    Flattens Product → Options → Units structure.
    Generates vector embeddings for search_text.
    """
    pass
```

### 6. Hybrid Matcher (`matcher.py`)

Orchestrates the multi-phase screening process.

```python
class ScreeningResult(TypedDict):
    products: list[dict]
    message: str | None
    phases_applied: list[str]

def screen_products(profile: SynthesizerOutput) -> ScreeningResult:
    """
    Execute hybrid multi-phase screening.
    
    Phase 1: SQL WHERE filtering (country, dates, age, pax)
    Phase 1b: Proximity filtering (within PROXIMITY_RADIUS_KM)
    Phase 1c: Semantic exclusion filtering (accessibility, diet, medical, fears)
    Phase 2: Semantic ranking by soft preferences
    
    Returns top 5 products or empty result with message.
    """
    pass
```

## Data Models

### LanceDB Schema

```python
import lancedb
from lancedb.pydantic import LanceModel, Vector
from lancedb.embeddings import get_registry

embedding_func = get_registry().get("sentence-transformers").create(
    name="all-MiniLM-L6-v2"
)

class ProductCatalog(LanceModel):
    # Product-level fields
    product_id: str
    title: str
    description: str
    country: str
    location: str
    address: str | None
    latitude: float | None
    longitude: float | None
    tags: str
    highlights: str
    
    # Option-level fields
    option_id: str
    option_name: str
    max_pax: int
    min_pax: int
    start_date: str | None
    end_date: str | None
    
    # Unit-level fields
    unit_id: str
    unit_type: str
    min_age: int
    max_age: int
    price_amount: int
    currency: str
    
    # Search fields
    search_text: str = embedding_func.SourceField()
    faq_text: str
    vector: Vector(embedding_func.ndims()) = embedding_func.VectorField()
```

### Synthesizer Output Schema

```json
{
  "hard_constraints": {
    "country": "IT",
    "target_latitude": 45.4408,
    "target_longitude": 12.3155,
    "accommodation_latitude": 45.4371,
    "accommodation_longitude": 12.3326,
    "holiday_begin_date": "2025-10-20",
    "holiday_end_date": "2025-10-27",
    "not_available_date_times": ["2025-10-22T10:00"],
    "age": 35,
    "max_pax": 2,
    "semantic_exclusions": {
      "accessibility": ["stairs", "steps", "climbing"],
      "diet": [],
      "medical": ["smoke", "dust"],
      "fears": ["heights", "tower", "rooftop"]
    }
  },
  "soft_preferences": {
    "preference_text": "romantic boat tour history art relaxing",
    "interests": ["history", "art", "architecture"],
    "activity_level": "sedentary",
    "sports": [],
    "languages": ["English"],
    "price_max": 15000,
    "notes": "romantic anniversary trip"
  }
}
```

## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system—essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

### Property 1: Synthesizer Output Schema Validity

*For any* valid personal_info and holiday_info input, the Synthesizer SHALL output a JSON object containing both `hard_constraints` and `soft_preferences` as separate top-level keys with the correct nested structure.

**Validates: Requirements 1.1**

### Property 2: Constraint-to-Exclusion Mapping

*For any* personal_info containing accessibility, dietary, medical, or fear constraints, the Synthesizer SHALL include corresponding expanded exclusion terms in `hard_constraints.semantic_exclusions`.

**Validates: Requirements 1.2, 1.3, 1.4, 1.5, 4.5, 4.6, 4.7, 4.8**

### Property 3: Location-to-Coordinates Resolution

*For any* holiday_info containing a valid city name or accommodation address, the Synthesizer SHALL resolve it to latitude/longitude coordinates within the expected geographic bounds for that location.

**Validates: Requirements 1.7, 1.8, 3.1, 3.2**

### Property 4: Haversine Distance Calculation

*For any* two geographic coordinates, the Haversine distance calculation SHALL produce a result within 0.5% of the known geodesic distance between those points.

**Validates: Requirements 3.5, 3.11**

### Property 5: Proximity Filtering Correctness

*For any* set of products and a target location with radius R, the Proximity Filter SHALL include all products within R km and exclude all products beyond R km of the target.

**Validates: Requirements 3.6, 3.7, 3.8**

### Property 6: Semantic Exclusion Filtering

*For any* product with embedding similarity to exclusion terms exceeding the threshold, the Semantic Exclusion Filter SHALL exclude that product from results.

**Validates: Requirements 4.2, 4.3**

### Property 7: Semantic Ranking Score Validity

*For any* set of ranked products, all relevance scores SHALL be in the range [0.0, 1.0] and SHALL be ordered in descending order.

**Validates: Requirements 5.2, 5.7**

### Property 8: Result Count and Deduplication

*For any* screening result, the Matcher SHALL return at most 5 products with no duplicate product_ids.

**Validates: Requirements 5.7, 7.5**

### Property 9: Phase Precedence

*For any* product excluded by Phase 1 (SQL), Phase 1b (Proximity), or Phase 1c (Semantic Exclusion), that product SHALL NOT appear in the final results regardless of its semantic similarity score.

**Validates: Requirements 7.1, 7.2, 7.3, 7.4**

### Property 10: Ingestor Field Completeness

*For any* OCTO product ingested, the resulting LanceDB row SHALL contain all required fields (product_id, title, description, country, location, option_id, unit_id, price_amount, search_text, vector).

**Validates: Requirements 6.1, 6.2, 6.3, 6.4, 6.8**

### Property 11: Embedding Generation Completeness

*For any* ingested product, the vector column SHALL contain a non-empty embedding of the expected dimensionality.

**Validates: Requirements 6.6, 6.8**

### Property 12: Geocode Cache Consistency

*For any* location string, repeated calls to the geocoding service SHALL return identical coordinates (cache hit).

**Validates: Requirements 3.12**

## Error Handling

### Synthesizer Errors

| Error Condition | Handling Strategy |
|----------------|-------------------|
| LLM fails to return valid JSON | Return structured error with raw response for debugging |
| Geocoding service unavailable | Fall back to country-only filtering, log warning |
| Unknown city name | Return None for coordinates, fall back to country filter |
| Missing required fields in input | Return error indicating which fields are missing |

### Matcher Errors

| Error Condition | Handling Strategy |
|----------------|-------------------|
| Database connection failure | Return error response with retry guidance |
| Empty hard_constraints | Apply default country filter only |
| Empty soft_preferences | Skip semantic ranking, return filtered results ordered by proximity |
| Embedding generation failure | Fall back to FTS-based ranking |
| Zero products after filtering | Return empty list with message "No feasible products found" |

### Ingestor Errors

| Error Condition | Handling Strategy |
|----------------|-------------------|
| Invalid JSON file | Raise exception with file path and parse error |
| Missing required OCTO fields | Skip product, log warning with product ID |
| Embedding generation failure | Skip product, log warning |
| Database write failure | Raise exception, do not partially commit |

## Testing Strategy

### Dual Testing Approach

This feature requires both unit tests and property-based tests for comprehensive coverage:

- **Unit tests**: Verify specific examples, edge cases, and error conditions
- **Property tests**: Verify universal properties across randomly generated inputs

### Property-Based Testing Configuration

- **Library**: `hypothesis` for Python property-based testing
- **Minimum iterations**: 100 per property test
- **Tag format**: `# Feature: hybrid-product-screener, Property N: [property_text]`

### Test Categories

#### Unit Tests

1. **Synthesizer Unit Tests**
   - Test known city → coordinates mapping (Venice → ~45.44, ~12.32)
   - Test accessibility term expansion ("no stairs" → ["stairs", "steps", "climbing"])
   - Test date extraction from holiday_info
   - Test error handling for malformed input

2. **Matcher Unit Tests**
   - Test SQL WHERE clause generation with various constraint combinations
   - Test Haversine calculation with known distances (Rome to Venice ≈ 394 km)
   - Test empty result handling
   - Test fallback behavior when geocoding fails

3. **Ingestor Unit Tests**
   - Test OCTO flattening produces expected row count
   - Test FAQ extraction into search_text
   - Test embedding column is populated

#### Property Tests

Each correctness property (1-12) SHALL be implemented as a property-based test with:
- Random input generation using Hypothesis strategies
- Minimum 100 iterations
- Clear property assertion matching the design document

#### Integration Tests

1. **End-to-End Pipeline Test**
   - Input: Sample personal_info (accessibility: "no stairs", fears: "heights") + holiday_info (Venice, Oct 2025)
   - Expected: No products with stairs/towers in results
   - Verify: Phase counts logged, top 5 returned

2. **Venice Boat Tour Test**
   - Input: "boat tour in Venice" preference
   - Expected: Venice boat tours rank higher than Rome walking tours
   - Verify: Semantic ranking improves over FTS baseline

### Test File Structure

```
tests/
├── products_screener/
│   ├── test_synthesizer.py      # Unit + property tests for synthesizer
│   ├── test_matcher.py          # Unit + property tests for matcher
│   ├── test_ingestor.py         # Unit + property tests for ingestor
│   ├── test_geocoding.py        # Unit tests for geocoding service
│   └── test_integration.py      # E2E integration tests
```

