# Architecture

## Pipeline Flow

```
User ──► Personal Collector ──► holiday Collector ──► Synthesizer ──► Hard Screener ──► Soft Screener ──► Results
              │                       │                    │                │                 │
              ▼                       ▼                    ▼                ▼                 ▼
         personal_info          holiday_info      hard_constraints    filtered_ids      top 5 products
                                                  soft_preferences
```

## Agents

### 1. Personal Information Collector
Conversational agent collecting user profile:
- Demographics (age, languages)
- Physical constraints (accessibility, activity level)
- Safety concerns (medical conditions, fears, diet)
- Interests and preferences

Uses schema-driven dialogue with review/correction phases.

### 2. Holiday Information Collector
Collects trip logistics:
- Dates (start/end, availability windows)
- Location (destination, accommodation)
- Special requests

### 3. Synthesizer
LLM transforms collected info into structured search profile:

```python
{
  "hard_constraints": {
    "country": "IT",
    "target_latitude": 45.44,
    "target_longitude": 12.31,
    "holiday_begin_date": "2025-06-01",
    "age": 35,
    "semantic_exclusions": {
      "accessibility": ["stairs", "steps", "climbing"],
      "medical": ["smoke", "dust"],
      "fears": ["heights", "tower", "rooftop"]
    }
  },
  "soft_preferences": {
    "preference_text": "romantic boat tour history art",
    "interests": ["history", "art"],
    "activity_level": "moderate"
  }
}
```

Key feature: expands constraint terms to related exclusions (e.g., "asthma" → ["smoke", "dust", "fumes"]).

### 4. Hard Screener
Three-phase filtering:

| Phase | Method | Purpose |
|-------|--------|---------|
| 1 | SQL WHERE | Country, dates, age, group size |
| 1b | Haversine | Products within 20km of target |
| 1c | Vector similarity | Exclude products matching fears/medical/accessibility |

Output: `list[tuple[product_id, option_id, unit_id]]`

### 5. Soft Screener
Ranks filtered products by semantic similarity to `preference_text`. Returns top 5 deduplicated by product_id.

## Data Model

Products follow OCTO specification, flattened for search:

```
Product (1) ──► Options (N) ──► Units (M)
   │               │               │
   title           dates           age restrictions
   location        restrictions    pricing
   description
```

Stored in LanceDB with:
- Full-text search index on `search_text`
- Vector embeddings (sentence-transformers) for semantic search

## Design Decisions

### Why two-phase screening?
Pure semantic search causes mismatches. "Boat tour in Venice" and "Walking tour in Rome" both match "tour". Hard constraints eliminate impossible options first, then soft preferences rank what remains.

### Why local LLM?
Personal/medical data stays on-device. Ollama + Llama 3.1:8b provides sufficient capability for constraint extraction without cloud dependencies.

### Why LanceDB?
Combines SQL filtering with vector search in one query. No need for separate vector DB + relational DB.

### Why expand exclusion terms?
User says "no stairs" but product says "steps" or "climbing". LLM-generated expansions catch synonyms and related concepts.

## Configuration

All tunable values in `src/common/config.py`:

```python
PROXIMITY_RADIUS_KM = 20.0           # Max distance from target
SEMANTIC_EXCLUSION_THRESHOLD = 0.7   # Similarity cutoff for exclusions
TOP_RESULTS_COUNT = 5                # Final results count
EMBEDDING_MODEL_NAME = "all-MiniLM-L6-v2"
LLM_MODEL = "llama3.1:8b"
```
