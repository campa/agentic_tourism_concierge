# Implementation Plan: Hybrid Product Screener

## Overview

This plan implements the four-phase hybrid filtering approach for the Product Screener:
- Phase 1: SQL WHERE filtering (country, dates, age, pax)
- Phase 1b: Proximity filtering (Haversine distance)
- Phase 1c: Semantic exclusion filtering (accessibility, diet, medical, fears)
- Phase 2: Semantic ranking by soft preferences

The implementation follows existing agent patterns, using Ollama (Llama 3.1:8b) for LLM synthesis and LanceDB with sentence-transformers for vector storage.

## Tasks

- [x] 0. Create centralized configuration
  - [x] 0.1 Create `config.py` module in `src/products_screener/`
    - Define PROXIMITY_RADIUS_KM (20.0)
    - Define SEMANTIC_EXCLUSION_THRESHOLD (0.7)
    - Define TOP_RESULTS_COUNT (5)
    - Define EMBEDDING_MODEL_NAME ("all-MiniLM-L6-v2")
    - Define LLM_MODEL ("llama3.1:8b")
    - Define DB_PATH and TABLE_NAME
    - Define CITY_COORDINATES lookup table (Venice, Rome, Florence, Milan, Barcelona, etc.)

- [-] 1. Enhance Ingestor for vector embeddings
  - [x] 1.1 Update `run_ingestion` to capture all OCTO fields
    - Add address, latitude, longitude fields from product level
    - Extract and flatten FAQ content into faq_text field
    - Include faq_text in search_text blob
    - _Requirements: 6.2, 6.3, 6.4, 6.5, 6.10_
  
  - [x] 1.2 Add vector embedding generation using sentence-transformers
    - Use LanceDB's built-in embedding support with model from config.EMBEDDING_MODEL_NAME
    - Generate embedding from search_text (title + description + tags + highlights + faq)
    - Store vector column alongside search_text
    - _Requirements: 6.6, 6.7, 6.8_
  
  - [ ]* 1.3 Write property test for ingestor field completeness
    - **Property 10: Ingestor Field Completeness**
    - *For any* OCTO product ingested, verify all required fields present
    - **Validates: Requirements 6.1, 6.2, 6.3, 6.4, 6.8**
  
  - [ ]* 1.4 Write property test for embedding generation
    - **Property 11: Embedding Generation Completeness**
    - *For any* ingested product, verify vector column is non-empty with correct dimensionality
    - **Validates: Requirements 6.6, 6.8**

- [-] 2. Create Geocoding Service
  - [x] 2.1 Create `geocoding.py` module
    - Implement `geocode(location: str) -> Coordinates | None` function
    - Use CITY_COORDINATES lookup table from config.py
    - Implement module-level cache `_geocode_cache`
    - Return None for unknown locations
    - _Requirements: 1.17, 3.1, 3.2, 3.4, 3.12_
  
  - [ ]* 2.2 Write property test for geocode cache consistency
    - **Property 12: Geocode Cache Consistency**
    - *For any* location string, repeated calls return identical coordinates
    - **Validates: Requirements 3.12**

- [x] 3. Checkpoint - Verify ingestor and geocoding work
  - Re-run ingestion with `mock_products.json`
  - Verify vector column is populated
  - Test geocoding with known cities
  - Ensure all tests pass, ask the user if questions arise.

- [x] 4. Enhance Synthesizer for hybrid output
  - [x] 4.1 Update synthesizer prompt for new output schema
    - Output `hard_constraints` with: country, target_latitude, target_longitude, accommodation_latitude, accommodation_longitude, holiday_begin_date, holiday_end_date, not_available_date_times, age, max_pax, semantic_exclusions
    - Output `soft_preferences` with: preference_text, interests, activity_level, sports, languages, price_max, notes
    - Expand constraint terms to related exclusion terms (stairs → steps, climbing, steep)
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 4.5, 4.6, 4.7, 4.8_
  
  - [x] 4.2 Create `synthesize_profile` function
    - Call LLM to extract constraints and preferences
    - Call geocoding service to resolve locations to coordinates
    - Return SynthesizerOutput with hard_constraints and soft_preferences
    - _Requirements: 1.6, 1.7, 1.8, 1.9, 1.10, 1.11, 1.12, 1.13, 1.14, 1.15, 1.16_
  
  - [ ]* 4.3 Write property test for synthesizer output schema
    - **Property 1: Synthesizer Output Schema Validity**
    - *For any* valid input, output contains both hard_constraints and soft_preferences keys
    - **Validates: Requirements 1.1**
  
  - [ ]* 4.4 Write property test for constraint-to-exclusion mapping
    - **Property 2: Constraint-to-Exclusion Mapping**
    - *For any* personal_info with constraints, verify exclusion terms are generated
    - **Validates: Requirements 1.2, 1.3, 1.4, 1.5, 4.5, 4.6, 4.7, 4.8**

- [x] 5. Implement Phase 1: SQL Filter
  - [x] 5.1 Create `build_sql_where` function in `matcher.py`
    - Build WHERE clause for country, dates (overlap logic), age, max_pax
    - Handle optional fields gracefully (skip if not provided)
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 2.7_

- [x] 6. Implement Phase 1b: Proximity Filter
  - [x] 6.1 Create `haversine_distance` function
    - Calculate distance in km between two coordinates
    - Use standard Haversine formula
    - _Requirements: 3.5, 3.11_
  
  - [x] 6.2 Create `filter_by_proximity` function
    - Filter products within config.PROXIMITY_RADIUS_KM (default 20km)
    - Use accommodation coordinates if available, else city coordinates
    - Geocode product locations if coordinates missing
    - _Requirements: 3.3, 3.4, 3.6, 3.7, 3.8, 3.9, 3.10_
  
  - [ ]* 6.3 Write property test for Haversine calculation
    - **Property 4: Haversine Distance Calculation**
    - *For any* two coordinates, result within 0.5% of known geodesic distance
    - **Validates: Requirements 3.5, 3.11**
  
  - [ ]* 6.4 Write property test for proximity filtering
    - **Property 5: Proximity Filtering Correctness**
    - *For any* products and target, include within R km, exclude beyond R km
    - **Validates: Requirements 3.6, 3.7, 3.8**

- [-] 7. Implement Phase 1c: Semantic Exclusion Filter
  - [x] 7.1 Create `filter_by_semantic_exclusion` function
    - Generate embedding for combined exclusion terms
    - Compute similarity between product embeddings and exclusion embedding
    - Exclude products with similarity > config.SEMANTIC_EXCLUSION_THRESHOLD (0.7)
    - _Requirements: 4.1, 4.2, 4.3, 4.4_
  
  - [ ]* 7.2 Write property test for semantic exclusion
    - **Property 6: Semantic Exclusion Filtering**
    - *For any* product with similarity > threshold, verify exclusion from results
    - **Validates: Requirements 4.2, 4.3**

- [x] 8. Checkpoint - Verify all filtering phases work
  - Test SQL filter with sample constraints
  - Test proximity filter with Venice coordinates
  - Test semantic exclusion with "stairs" exclusion
  - Ensure all tests pass, ask the user if questions arise.

- [x] 9. Implement Phase 2: Semantic Ranking
  - [x] 9.1 Create `rank_by_preferences` function
    - Generate embedding for preference_text
    - Use LanceDB vector search for similarity scoring
    - Combine with price scoring (within budget = higher score)
    - Normalize scores to [0.0, 1.0]
    - Deduplicate by product_id (keep highest score)
    - Return top 5 ordered by combined score
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5, 5.6, 5.7_
  
  - [ ]* 9.2 Write property test for score validity
    - **Property 7: Semantic Ranking Score Validity**
    - *For any* ranked products, scores in [0.0, 1.0] and descending order
    - **Validates: Requirements 5.2, 5.7**
  
  - [ ]* 9.3 Write property test for result count and deduplication
    - **Property 8: Result Count and Deduplication**
    - *For any* result, at most 5 products with no duplicate product_ids
    - **Validates: Requirements 5.7, 7.5**

- [x] 10. Implement Main Screening Function
  - [x] 10.1 Create `screen_products` function
    - Orchestrate: Phase 1 (SQL) → Phase 1b (Proximity) → Phase 1c (Exclusion) → Phase 2 (Ranking)
    - Log product counts after each phase
    - Return empty list with message if no products pass filtering
    - Handle missing soft_preferences (return filtered results by proximity)
    - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5, 7.6, 7.7_
  
  - [ ]* 10.2 Write property test for phase precedence
    - **Property 9: Phase Precedence**
    - *For any* product excluded by Phase 1/1b/1c, verify not in final results
    - **Validates: Requirements 7.1, 7.2, 7.3, 7.4**

- [x] 11. Implement Error Handling
  - [x] 11.1 Add error handling to synthesizer
    - Return structured error if LLM fails to parse
    - Fall back to country-only filter if geocoding fails
    - _Requirements: 8.1, 8.2_
  
  - [x] 11.2 Add error handling to matcher
    - Apply default filters if hard_constraints empty
    - Skip ranking if soft_preferences empty
    - Fall back to FTS if embedding fails
    - _Requirements: 8.3, 8.4, 8.5_

- [x] 12. Checkpoint - Verify full pipeline works
  - Test complete flow with Venice boat tour example
  - Verify logging at each phase
  - Ensure all tests pass, ask the user if questions arise.

- [x] 13. Update logging configuration
  - [x] 13.1 Update `common/logging_config.py`
    - Add `products_screener_geocoding` logger
    - Ensure existing loggers work with new functions

- [x] 14. Create E2E test script
  - [x] 14.1 Create `test_hybrid_screener.py` script
    - Test with Venice example (accessibility: "no stairs", fears: "heights")
    - Print synthesized profile (hard_constraints + soft_preferences)
    - Print product counts after each phase
    - Print top 5 results with relevance scores
    - Verify no stairs/towers in results

- [x] 15. Final checkpoint - Full integration test
  - Run E2E test script
  - Verify Venice boat tour ranks higher than Rome walking tour
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation
- Property tests validate universal correctness properties (12 total in design)
- The E2E test script provides quick verification of the full pipeline
