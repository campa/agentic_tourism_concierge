# Requirements Document

## Introduction

This document specifies the requirements for transforming the existing keyword-based Full-Text Search (FTS) product screener into a hybrid two-phase screening system. The current FTS approach causes semantic mismatches (e.g., returning "Colosseum tour in Rome" when user wants "boat tour in Venice" because both contain "tour"). The hybrid approach separates hard constraints (feasibility filters) from soft preferences (semantic ranking) to improve match quality.

## Glossary

- **Hard_Constraint**: A non-negotiable filter that disqualifies products if violated (e.g., accessibility requirements, dietary restrictions, date availability)
- **Soft_Preference**: A preference that influences ranking but does not disqualify products (e.g., interests, activity level, price)
- **Feasibility_Filter**: Phase 1 SQL-based filtering that removes impossible products based on hard constraints
- **Semantic_Ranker**: Phase 2 vector-based ranking that scores remaining products by soft preference similarity
- **Synthesizer**: LLM component that transforms user input into structured hard_constraints and soft_preferences objects
- **LanceDB**: Vector database used for storage, filtering, and semantic search
- **Embedding**: Vector representation of text for semantic similarity comparison
- **OCTO_Product**: A travel product following the OCTO specification format

## Requirements

### Requirement 1: Synthesizer Output Restructuring

**User Story:** As a system component, I want the synthesizer to output separate hard_constraints and soft_preferences objects, so that the matcher can apply them in distinct phases.

#### Acceptance Criteria

1. WHEN the Synthesizer processes user input, THE Synthesizer SHALL output a JSON object containing both `hard_constraints` and `soft_preferences` as separate top-level keys
2. WHEN personal_info contains accessibility requirements, THE Synthesizer SHALL include corresponding exclusion terms in `hard_constraints.semantic_exclusions`
3. WHEN personal_info contains dietary restrictions, THE Synthesizer SHALL include corresponding exclusion terms in `hard_constraints.semantic_exclusions`
4. WHEN personal_info contains medical conditions, THE Synthesizer SHALL include corresponding exclusion terms in `hard_constraints.semantic_exclusions`
5. WHEN personal_info contains fears, THE Synthesizer SHALL include corresponding exclusion terms in `hard_constraints.semantic_exclusions`
6. WHEN holiday_info contains location, THE Synthesizer SHALL extract and include `country` (2-letter ISO code) in `hard_constraints`
7. WHEN holiday_info contains location, THE Synthesizer SHALL extract city name and resolve it to `target_latitude` and `target_longitude` in `hard_constraints`
8. WHEN holiday_info contains accommodation address, THE Synthesizer SHALL resolve it to `accommodation_latitude` and `accommodation_longitude` in `hard_constraints`
9. WHEN holiday_info contains date range, THE Synthesizer SHALL include `holiday_begin_date` and `holiday_end_date` in `hard_constraints`
10. WHEN holiday_info contains blocked times, THE Synthesizer SHALL include `not_available_date_times` in `hard_constraints`
11. WHEN personal_info contains interests, THE Synthesizer SHALL include them as preference keywords in `soft_preferences`
12. WHEN personal_info contains activity_level, THE Synthesizer SHALL include it in `soft_preferences`
13. WHEN personal_info contains sports preferences, THE Synthesizer SHALL include them in `soft_preferences`
14. WHEN personal_info contains language preferences, THE Synthesizer SHALL include them in `soft_preferences`
15. WHEN holiday_info contains budget/price preferences, THE Synthesizer SHALL include price_max in `soft_preferences` (not hard_constraints)
16. WHEN holiday_info contains notes, THE Synthesizer SHALL include them in `soft_preferences` for semantic matching
17. THE Synthesizer SHALL use a geocoding service or lookup table to resolve city/address names to coordinates

### Requirement 2: Hard Constraint Filtering (Phase 1)

**User Story:** As a user with accessibility needs, I want products that violate my physical constraints to be completely excluded, so that I only see feasible options.

#### Acceptance Criteria

1. THE Feasibility_Filter SHALL build a single SQL WHERE clause combining all exact-match hard constraints
2. WHEN hard_constraints contains country, THE Feasibility_Filter SHALL add `country = 'XX'` to the WHERE clause
3. WHEN hard_constraints contains holiday_begin_date and holiday_end_date, THE Feasibility_Filter SHALL add date overlap conditions to the WHERE clause (e.g., `start_date <= holiday_end_date AND end_date >= holiday_begin_date`)
4. WHEN hard_constraints contains not_available_date_times, THE Feasibility_Filter SHALL add exclusion conditions to the WHERE clause for conflicting time slots
5. WHEN hard_constraints contains age, THE Feasibility_Filter SHALL add `min_age <= age AND max_age >= age` to the WHERE clause
6. WHEN hard_constraints contains max_pax, THE Feasibility_Filter SHALL add `max_pax >= group_size` to the WHERE clause
7. THE Feasibility_Filter SHALL execute the combined SQL WHERE clause against LanceDB using the `.where()` method

### Requirement 3: Location-Based Filtering (Phase 1b - Proximity)

**User Story:** As a user traveling to a specific city, I want products within a reasonable distance from my destination, so that I don't see products too far away to be practical.

#### Acceptance Criteria

1. WHEN hard_constraints contains city, THE Synthesizer SHALL resolve the city to latitude/longitude coordinates (city center)
2. WHEN hard_constraints contains accommodation address, THE Synthesizer SHALL resolve it to latitude/longitude coordinates
3. WHEN a product has latitude/longitude coordinates, THE Feasibility_Filter SHALL use them directly for distance calculation
4. WHEN a product lacks latitude/longitude coordinates, THE Feasibility_Filter SHALL resolve the product's location/city field to coordinates using a geocoding service (city center)
5. THE Feasibility_Filter SHALL calculate the distance between each product's coordinates and the target location coordinates
6. THE Feasibility_Filter SHALL use a configurable `PROXIMITY_RADIUS_KM` constant (default: 20km) for distance threshold
7. THE Feasibility_Filter SHALL include products within `PROXIMITY_RADIUS_KM` of the target location
8. THE Feasibility_Filter SHALL exclude products beyond `PROXIMITY_RADIUS_KM`
9. WHEN both city and accommodation coordinates are available, THE Feasibility_Filter SHALL use accommodation coordinates as the primary reference point
10. IF city coordinates cannot be resolved, THEN THE Feasibility_Filter SHALL fall back to country-only filter with a warning
11. THE Feasibility_Filter SHALL use the Haversine formula to calculate distances between coordinates
12. THE Feasibility_Filter SHALL cache geocoded coordinates to avoid repeated lookups for the same location

### Requirement 4: Semantic Hard Constraint Filtering (Phase 1c)

**User Story:** As a user with dietary restrictions or medical conditions, I want products that semantically conflict with my constraints to be excluded, so that I don't see products that use synonyms or related terms for things I must avoid.

#### Acceptance Criteria

1. WHEN hard_constraints contains semantic exclusions (accessibility, diet, medical, fears), THE Synthesizer SHALL generate an `exclusion_embedding_text` combining all semantic exclusion terms
2. THE Feasibility_Filter SHALL compute vector similarity between each product's embedding and the exclusion_embedding
3. WHEN a product's similarity to the exclusion_embedding exceeds a configurable threshold, THE Feasibility_Filter SHALL exclude that product
4. THE Feasibility_Filter SHALL apply semantic exclusion filtering after SQL WHERE filtering but before soft preference ranking
5. WHEN hard_constraints contains accessibility terms (e.g., "no stairs"), THE Synthesizer SHALL expand them to related terms (e.g., "stairs, steps, climbing, steep")
6. WHEN hard_constraints contains dietary terms (e.g., "gluten-free"), THE Synthesizer SHALL expand them to conflicting terms (e.g., "wheat, bread, pasta, flour, gluten")
7. WHEN hard_constraints contains medical terms (e.g., "asthma"), THE Synthesizer SHALL expand them to hazardous terms (e.g., "smoke, dust, fumes, pollution")
8. WHEN hard_constraints contains fear terms (e.g., "heights"), THE Synthesizer SHALL expand them to related terms (e.g., "tower, rooftop, cliff, balcony, high")

### Requirement 5: Semantic Ranking (Phase 2)

**User Story:** As a user with specific interests, I want products that match my preferences to rank higher, so that the most relevant options appear first.

#### Acceptance Criteria

1. WHEN soft_preferences are provided, THE Semantic_Ranker SHALL generate a vector embedding from the combined preference text
2. WHEN ranking products, THE Semantic_Ranker SHALL compute similarity scores between the preference embedding and product embeddings
3. WHEN soft_preferences contains interests, THE Semantic_Ranker SHALL boost products semantically related to those interests
4. WHEN soft_preferences contains activity_level, THE Semantic_Ranker SHALL boost products matching the activity intensity
5. WHEN soft_preferences contains price_max, THE Semantic_Ranker SHALL boost products within budget (higher score for lower price relative to budget)
6. WHEN soft_preferences contains location, THE Semantic_Ranker SHALL boost products closer to the specified location
7. THE Semantic_Ranker SHALL return the top 5 products ordered by combined semantic score

### Requirement 6: Ingestor Enhancement for Vector Search

**User Story:** As a system component, I want products to have all OCTO fields captured and vector embeddings stored, so that semantic search and comprehensive filtering can be performed efficiently.

#### Acceptance Criteria

1. THE Ingestor SHALL flatten OCTO products from Product → Options → Units structure into individual rows
2. THE Ingestor SHALL capture all Product-level fields: id, title, description, country, location, address, latitude, longitude, tags, highlights
3. THE Ingestor SHALL capture all Option-level fields: id, internalName, availabilityLocalDateStart, availabilityLocalDateEnd, restrictions (minPaxCount, maxPaxCount)
4. THE Ingestor SHALL capture all Unit-level fields: id, type, title, restrictions (minAge, maxAge), pricingFrom (original, retail, currency)
5. THE Ingestor SHALL extract and flatten FAQ content (questions and answers) into a searchable text field
6. WHEN ingesting products, THE Ingestor SHALL generate vector embeddings for each product's search_text using sentence-transformers
7. WHEN creating the LanceDB table, THE Ingestor SHALL configure LanceDB's built-in embedding functions for automatic embedding generation
8. WHEN storing products, THE Ingestor SHALL store both the raw search_text and its vector embedding in a `vector` column
9. THE Ingestor SHALL create a vector index on the embeddings column for efficient similarity search
10. THE Ingestor SHALL include FAQ content in the search_text blob for semantic matching of accessibility and other product details

### Requirement 7: Hybrid Matcher Integration

**User Story:** As a user, I want the screening process to first filter impossible products then rank by preference, so that I get relevant and feasible results.

#### Acceptance Criteria

1. WHEN screening products, THE Matcher SHALL first execute Phase 1 (SQL-based Feasibility_Filter) to remove products violating exact-match constraints
2. WHEN Phase 1 completes, THE Matcher SHALL execute Phase 1b (Proximity Filter) to remove products beyond the distance threshold
3. WHEN Phase 1b completes, THE Matcher SHALL execute Phase 1c (Semantic Exclusion Filter) to remove products semantically matching exclusion criteria
4. WHEN Phase 1c completes, THE Matcher SHALL execute Phase 2 (Semantic_Ranker) on the filtered results
5. WHEN all phases complete, THE Matcher SHALL return the top 5 products ordered by semantic score
6. IF any filtering phase returns zero products, THEN THE Matcher SHALL return an empty result set with a message indicating no feasible products found
7. IF Phase 2 has no soft_preferences, THEN THE Matcher SHALL return filtered results ordered by proximity score (closer = higher)

### Requirement 8: Error Handling and Edge Cases

**User Story:** As a system operator, I want the screener to handle edge cases gracefully, so that the system remains stable under unexpected inputs.

#### Acceptance Criteria

1. IF the Synthesizer fails to parse user input, THEN THE Synthesizer SHALL return a structured error with details
2. IF hard_constraints is empty or missing, THEN THE Feasibility_Filter SHALL apply only default country and age filters
3. IF soft_preferences is empty or missing, THEN THE Semantic_Ranker SHALL skip semantic ranking and return filtered results
4. IF embedding generation fails, THEN THE Semantic_Ranker SHALL fall back to FTS-based ranking
5. IF the database connection fails, THEN THE Matcher SHALL return an error response with retry guidance
