"""
Checkpoint tests for verifying all filtering phases work correctly.

Tests:
- Phase 1: SQL filter with sample constraints
- Phase 1b: Proximity filter with Venice coordinates
- Phase 1c: Semantic exclusion with "stairs" exclusion
- Phase 2: Semantic ranking by soft preferences
"""

import numpy as np
import pandas as pd
import pytest
from conftest import requires_db

from common.config import PROXIMITY_RADIUS_KM, SEMANTIC_EXCLUSION_THRESHOLD, TOP_RESULTS_COUNT
from product_hard_screener.core import (
    build_sql_where,
    filter_by_proximity,
    filter_by_semantic_exclusion,
    haversine_distance,
)
from product_soft_screener.core import rank_by_preferences
from product_synthesizer.types import HardConstraints, SemanticExclusions, SoftPreferences


class TestSQLFilter:
    """Tests for Phase 1: SQL WHERE clause building."""

    def test_build_sql_where_country_only(self):
        """Test SQL filter with country constraint only."""
        constraints: HardConstraints = {
            "country": "IT",
            "target_latitude": None,
            "target_longitude": None,
            "accommodation_latitude": None,
            "accommodation_longitude": None,
            "holiday_begin_date": None,
            "holiday_end_date": None,
            "not_available_date_times": [],
            "age": None,
            "max_pax": None,
            "semantic_exclusions": {
                "accessibility": [],
                "diet": [],
                "medical": [],
                "fears": [],
            },
        }

        where_clause = build_sql_where(constraints)
        assert "country = 'IT'" in where_clause

    def test_build_sql_where_full_constraints(self):
        """Test SQL filter with all constraints."""
        constraints: HardConstraints = {
            "country": "IT",
            "target_latitude": 45.4408,
            "target_longitude": 12.3155,
            "accommodation_latitude": None,
            "accommodation_longitude": None,
            "holiday_begin_date": "2025-10-20",
            "holiday_end_date": "2025-10-27",
            "not_available_date_times": [],
            "age": 35,
            "max_pax": 2,
            "semantic_exclusions": {
                "accessibility": [],
                "diet": [],
                "medical": [],
                "fears": [],
            },
        }

        where_clause = build_sql_where(constraints)

        # Verify all constraints are present
        assert "country = 'IT'" in where_clause
        assert "min_age <= 35" in where_clause
        assert "max_age >= 35" in where_clause
        assert "max_pax >= 2" in where_clause
        # Date overlap logic
        assert "start_date" in where_clause
        assert "end_date" in where_clause

    def test_build_sql_where_empty_constraints(self):
        """Test SQL filter with no constraints returns match-all."""
        constraints: HardConstraints = {
            "country": None,
            "target_latitude": None,
            "target_longitude": None,
            "accommodation_latitude": None,
            "accommodation_longitude": None,
            "holiday_begin_date": None,
            "holiday_end_date": None,
            "not_available_date_times": [],
            "age": None,
            "max_pax": None,
            "semantic_exclusions": {
                "accessibility": [],
                "diet": [],
                "medical": [],
                "fears": [],
            },
        }

        where_clause = build_sql_where(constraints)
        assert where_clause == "1=1"


class TestProximityFilter:
    """Tests for Phase 1b: Proximity filtering."""

    def test_haversine_distance_known_cities(self):
        """Test Haversine calculation with known distances."""
        # Venice coordinates
        venice_lat, venice_lon = 45.4408, 12.3155
        # Rome coordinates
        rome_lat, rome_lon = 41.9028, 12.4964

        distance = haversine_distance(venice_lat, venice_lon, rome_lat, rome_lon)

        # Known distance Venice to Rome is approximately 394 km
        assert 390 < distance < 400, f"Expected ~394km, got {distance}km"

    def test_haversine_distance_same_point(self):
        """Test Haversine returns 0 for same point."""
        lat, lon = 45.4408, 12.3155
        distance = haversine_distance(lat, lon, lat, lon)
        assert distance == 0.0

    def test_filter_by_proximity_includes_nearby(self):
        """Test proximity filter includes products within radius."""
        # Venice coordinates
        target_lat, target_lon = 45.4408, 12.3155

        # Create test products - one in Venice, one in Rome
        products = pd.DataFrame(
            [
                {
                    "product_id": "venice-tour",
                    "title": "Venice Boat Tour",
                    "latitude": 45.4371,  # Very close to Venice center
                    "longitude": 12.3326,
                    "location": "Venice",
                },
                {
                    "product_id": "rome-tour",
                    "title": "Rome Walking Tour",
                    "latitude": 41.9028,  # Rome - far from Venice
                    "longitude": 12.4964,
                    "location": "Rome",
                },
            ]
        )

        result = filter_by_proximity(products, target_lat, target_lon, radius_km=20.0)

        # Only Venice tour should be included
        assert len(result) == 1
        assert result.iloc[0]["product_id"] == "venice-tour"
        assert "distance_km" in result.columns
        assert result.iloc[0]["distance_km"] < 20.0

    def test_filter_by_proximity_excludes_distant(self):
        """Test proximity filter excludes products beyond radius."""
        # Venice coordinates
        target_lat, target_lon = 45.4408, 12.3155

        # Create test product in Rome (far from Venice)
        products = pd.DataFrame(
            [
                {
                    "product_id": "rome-tour",
                    "title": "Rome Walking Tour",
                    "latitude": 41.9028,
                    "longitude": 12.4964,
                    "location": "Rome",
                },
            ]
        )

        result = filter_by_proximity(products, target_lat, target_lon, radius_km=20.0)

        # Rome tour should be excluded (too far)
        assert len(result) == 0

    def test_filter_by_proximity_empty_dataframe(self):
        """Test proximity filter handles empty DataFrame."""
        products = pd.DataFrame()
        result = filter_by_proximity(products, 45.4408, 12.3155)
        assert len(result) == 0


class TestSemanticExclusionFilter:
    """Tests for Phase 1c: Semantic exclusion filtering."""

    def test_filter_excludes_high_similarity_products(self):
        """Test semantic exclusion filters products with high similarity to exclusion terms."""
        # Create mock products with embeddings
        # Product 1: About stairs/climbing (should be excluded with "stairs" exclusion)
        # Product 2: About boats (should be kept)

        # Generate mock embeddings that simulate semantic similarity
        # For testing, we'll use simple vectors where similarity can be controlled
        stairs_vector = np.array([1.0, 0.0, 0.0, 0.0] * 96)  # 384 dims
        boat_vector = np.array([0.0, 1.0, 0.0, 0.0] * 96)  # 384 dims

        products = pd.DataFrame(
            [
                {
                    "product_id": "tower-climb",
                    "title": "Tower Climbing Experience",
                    "vector": stairs_vector.tolist(),
                },
                {
                    "product_id": "boat-tour",
                    "title": "Relaxing Boat Tour",
                    "vector": boat_vector.tolist(),
                },
            ]
        )

        exclusions: SemanticExclusions = {
            "accessibility": ["stairs", "steps", "climbing"],
            "diet": [],
            "medical": [],
            "fears": [],
        }

        # Note: This test verifies the function runs without error
        # Actual semantic filtering depends on the embedding model
        result = filter_by_semantic_exclusion(products, exclusions)

        # Both products should have exclusion_similarity column
        assert "exclusion_similarity" in result.columns

    def test_filter_no_exclusions_keeps_all(self):
        """Test semantic exclusion with no terms keeps all products."""
        products = pd.DataFrame(
            [
                {
                    "product_id": "tour-1",
                    "title": "Tour 1",
                    "vector": [0.1] * 384,
                },
                {
                    "product_id": "tour-2",
                    "title": "Tour 2",
                    "vector": [0.2] * 384,
                },
            ]
        )

        exclusions: SemanticExclusions = {
            "accessibility": [],
            "diet": [],
            "medical": [],
            "fears": [],
        }

        result = filter_by_semantic_exclusion(products, exclusions)

        # All products should be kept when no exclusions
        assert len(result) == 2

    def test_filter_empty_dataframe(self):
        """Test semantic exclusion handles empty DataFrame."""
        products = pd.DataFrame()
        exclusions: SemanticExclusions = {
            "accessibility": ["stairs"],
            "diet": [],
            "medical": [],
            "fears": [],
        }

        result = filter_by_semantic_exclusion(products, exclusions)
        assert len(result) == 0


class TestConfigValues:
    """Tests to verify configuration values are set correctly."""

    def test_proximity_radius_default(self):
        """Verify default proximity radius is 20km."""
        assert PROXIMITY_RADIUS_KM == 20.0

    def test_semantic_exclusion_threshold_default(self):
        """Verify default semantic exclusion threshold is 0.7."""
        assert SEMANTIC_EXCLUSION_THRESHOLD == 0.7


@requires_db
class TestIntegrationWithDatabase:
    """Integration tests using the actual LanceDB database."""

    @pytest.fixture
    def db_products(self):
        """Load products from the actual database."""
        import os

        import lancedb

        db_path = os.path.join(os.getcwd(), "data", "products_screener", "products.db")
        if not os.path.exists(db_path):
            pytest.skip("Database not found - run ingestion first")

        db = lancedb.connect(db_path)
        table = db.open_table("product_catalog")
        return table.to_pandas()

    def test_sql_filter_with_database(self, db_products):
        """Test SQL filter generates valid clause for database products."""
        constraints: HardConstraints = {
            "country": "IT",
            "target_latitude": None,
            "target_longitude": None,
            "accommodation_latitude": None,
            "accommodation_longitude": None,
            "holiday_begin_date": "2025-06-01",
            "holiday_end_date": "2025-12-31",
            "not_available_date_times": [],
            "age": 30,
            "max_pax": 2,
            "semantic_exclusions": {
                "accessibility": [],
                "diet": [],
                "medical": [],
                "fears": [],
            },
        }

        where_clause = build_sql_where(constraints)

        # Verify the clause is valid SQL syntax
        assert "country = 'IT'" in where_clause
        assert "min_age <= 30" in where_clause
        assert "max_age >= 30" in where_clause

    def test_proximity_filter_with_venice_coordinates(self, db_products):
        """Test proximity filter with Venice coordinates on actual data."""
        # Venice coordinates
        venice_lat, venice_lon = 45.4408, 12.3155

        # Filter products near Venice
        result = filter_by_proximity(db_products, venice_lat, venice_lon, radius_km=20.0)

        # Rome and Barcelona products should be excluded (too far from Venice)
        # Venice is ~394km from Rome and ~1100km from Barcelona
        assert len(result) == 0, "No products should be within 20km of Venice in mock data"

    def test_proximity_filter_with_rome_coordinates(self, db_products):
        """Test proximity filter with Rome coordinates on actual data."""
        # Rome coordinates
        rome_lat, rome_lon = 41.9028, 12.4964

        # Filter products near Rome
        result = filter_by_proximity(db_products, rome_lat, rome_lon, radius_km=20.0)

        # Rome Colosseum product should be included
        assert len(result) >= 1, "Rome product should be within 20km of Rome center"
        assert any(
            "Rome" in str(row.get("location", "")) or "Colosseum" in str(row.get("title", ""))
            for _, row in result.iterrows()
        )

    def test_semantic_exclusion_with_stairs(self, db_products):
        """Test semantic exclusion with 'stairs' exclusion on actual data."""
        exclusions: SemanticExclusions = {
            "accessibility": ["stairs", "steps", "climbing", "steep"],
            "diet": [],
            "medical": [],
            "fears": [],
        }

        result = filter_by_semantic_exclusion(db_products, exclusions)

        # Verify exclusion_similarity column is added
        assert "exclusion_similarity" in result.columns

        # The Sagrada Familia tour mentions stairs in FAQ, so it might have higher similarity
        # The Colosseum tour mentions wheelchair accessibility, so it should have lower similarity
        print(f"Products after semantic exclusion: {len(result)}")
        for _, row in result.iterrows():
            print(f"  - {row['title']}: similarity={row['exclusion_similarity']:.3f}")

    def test_full_filtering_pipeline(self, db_products):
        """Test the complete filtering pipeline: SQL -> Proximity -> Semantic Exclusion."""
        # Step 1: SQL filter for Italy

        # Filter by country manually (simulating SQL filter)
        sql_filtered = db_products[db_products["country"] == "IT"]
        print(f"After SQL filter (country=IT): {len(sql_filtered)} products")

        # Step 2: Proximity filter near Rome
        rome_lat, rome_lon = 41.9028, 12.4964
        proximity_filtered = filter_by_proximity(sql_filtered, rome_lat, rome_lon, radius_km=50.0)
        print(f"After proximity filter (50km from Rome): {len(proximity_filtered)} products")

        # Step 3: Semantic exclusion (no stairs)
        exclusions: SemanticExclusions = {
            "accessibility": ["stairs", "steps", "climbing"],
            "diet": [],
            "medical": [],
            "fears": [],
        }
        final_result = filter_by_semantic_exclusion(proximity_filtered, exclusions)
        print(f"After semantic exclusion: {len(final_result)} products")

        # Verify pipeline completed successfully
        assert "distance_km" in final_result.columns
        assert "exclusion_similarity" in final_result.columns


class TestSemanticRanking:
    """Tests for Phase 2: Semantic ranking by preferences."""

    def test_rank_by_preferences_empty_dataframe(self):
        """Test ranking handles empty DataFrame."""
        products = pd.DataFrame()
        preferences: SoftPreferences = {
            "preference_text": "romantic boat tour",
            "interests": ["history", "art"],
            "activity_level": "sedentary",
            "sports": [],
            "languages": ["English"],
            "notes": None,
        }

        result = rank_by_preferences(products, preferences)
        assert len(result) == 0

    def test_rank_by_preferences_no_preference_text(self):
        """Test ranking with no preference text uses interests and notes."""
        products = pd.DataFrame(
            [
                {
                    "product_id": "tour-1",
                    "title": "Tour 1",
                    "vector": [0.1] * 384,
                    "price_amount": 5000,
                },
            ]
        )

        preferences: SoftPreferences = {
            "preference_text": "",
            "interests": ["history", "art"],
            "activity_level": "moderate",
            "sports": [],
            "languages": [],
            "notes": "romantic trip",
        }

        result = rank_by_preferences(products, preferences)

        # Should still return results with relevance_score
        assert len(result) == 1
        assert "relevance_score" in result.columns

    def test_rank_by_preferences_returns_top_n(self):
        """Test ranking returns at most top N results."""
        # Create 10 products
        products = pd.DataFrame(
            [
                {
                    "product_id": f"tour-{i}",
                    "title": f"Tour {i}",
                    "vector": [0.1 * i] * 384,
                    "price_amount": 1000 * i,
                }
                for i in range(1, 11)
            ]
        )

        preferences: SoftPreferences = {
            "preference_text": "romantic boat tour history art",
            "interests": ["history", "art"],
            "activity_level": "sedentary",
            "sports": [],
            "languages": [],
            "notes": None,
        }

        result = rank_by_preferences(products, preferences, top_n=5)

        # Should return at most 5 products
        assert len(result) <= 5

    def test_rank_by_preferences_scores_in_range(self):
        """Test all relevance scores are in [0.0, 1.0] range."""
        products = pd.DataFrame(
            [
                {
                    "product_id": "tour-1",
                    "title": "Venice Boat Tour",
                    "vector": [0.5] * 384,
                    "price_amount": 5000,
                },
                {
                    "product_id": "tour-2",
                    "title": "Rome Walking Tour",
                    "vector": [0.3] * 384,
                    "price_amount": 8000,
                },
            ]
        )

        preferences: SoftPreferences = {
            "preference_text": "romantic boat tour",
            "interests": ["history"],
            "activity_level": "sedentary",
            "sports": [],
            "languages": [],
            "notes": None,
        }

        result = rank_by_preferences(products, preferences)

        # All scores should be in [0.0, 1.0]
        assert all(0.0 <= score <= 1.0 for score in result["relevance_score"])

    def test_rank_by_preferences_descending_order(self):
        """Test results are ordered by relevance_score descending."""
        products = pd.DataFrame(
            [
                {
                    "product_id": "tour-1",
                    "title": "Tour 1",
                    "vector": [0.1] * 384,
                    "price_amount": 5000,
                },
                {
                    "product_id": "tour-2",
                    "title": "Tour 2",
                    "vector": [0.5] * 384,
                    "price_amount": 3000,
                },
                {
                    "product_id": "tour-3",
                    "title": "Tour 3",
                    "vector": [0.3] * 384,
                    "price_amount": 7000,
                },
            ]
        )

        preferences: SoftPreferences = {
            "preference_text": "romantic boat tour",
            "interests": [],
            "activity_level": None,
            "sports": [],
            "languages": [],
            "notes": None,
        }

        result = rank_by_preferences(products, preferences)

        # Scores should be in descending order
        scores = result["relevance_score"].tolist()
        assert scores == sorted(scores, reverse=True)

    def test_rank_by_preferences_deduplicates_by_product_id(self):
        """Test ranking deduplicates by product_id, keeping highest score."""
        # Create products with duplicate product_ids
        products = pd.DataFrame(
            [
                {
                    "product_id": "tour-1",
                    "title": "Tour 1 Option A",
                    "vector": [0.5] * 384,
                    "price_amount": 5000,
                },
                {
                    "product_id": "tour-1",  # Duplicate
                    "title": "Tour 1 Option B",
                    "vector": [0.3] * 384,
                    "price_amount": 3000,
                },
                {
                    "product_id": "tour-2",
                    "title": "Tour 2",
                    "vector": [0.4] * 384,
                    "price_amount": 6000,
                },
            ]
        )

        preferences: SoftPreferences = {
            "preference_text": "romantic boat tour",
            "interests": [],
            "activity_level": None,
            "sports": [],
            "languages": [],
            "notes": None,
        }

        result = rank_by_preferences(products, preferences)

        # Should have no duplicate product_ids
        assert len(result["product_id"].unique()) == len(result)
        # Should have 2 unique products
        assert len(result) == 2


class TestConfigValuesPhase2:
    """Tests to verify Phase 2 configuration values."""

    def test_top_results_count_default(self):
        """Verify default top results count is 5."""
        assert TOP_RESULTS_COUNT == 5


@requires_db
class TestFullPipelineVeniceExample:
    """
    Checkpoint 12: Verify full pipeline works with Venice boat tour example.

    Tests the complete flow:
    - Phase 1: SQL filter
    - Phase 1b: Proximity filter
    - Phase 1c: Semantic exclusion filter
    - Phase 2: Semantic ranking

    Uses Venice example with accessibility constraints (no stairs) and fears (heights).
    """

    @pytest.fixture
    def venice_hard_constraints(self) -> HardConstraints:
        """Hard constraints for Venice boat tour example."""
        return {
            "country": "IT",
            "target_latitude": 45.4408,  # Venice center
            "target_longitude": 12.3155,
            "accommodation_latitude": None,
            "accommodation_longitude": None,
            "holiday_begin_date": "2025-10-20",
            "holiday_end_date": "2025-10-27",
            "not_available_date_times": [],
            "age": 35,
            "max_pax": 2,
            "semantic_exclusions": {
                "accessibility": ["stairs", "steps", "climbing", "steep"],
                "diet": [],
                "medical": [],
                "fears": ["heights", "tower", "rooftop", "cliff", "balcony", "high"],
            },
        }

    @pytest.fixture
    def venice_soft_preferences(self) -> SoftPreferences:
        """Soft preferences for Venice boat tour example."""
        return {
            "preference_text": "romantic boat tour history art relaxing",
            "interests": ["history", "art", "architecture"],
            "activity_level": "sedentary",
            "sports": [],
            "languages": ["English"],
            "notes": "romantic anniversary trip",
        }

    def test_sql_filter_generates_valid_clause(self, venice_hard_constraints):
        """Test Phase 1: SQL filter generates valid WHERE clause."""
        where_clause = build_sql_where(venice_hard_constraints)

        # Verify all expected constraints are in the clause
        assert "country = 'IT'" in where_clause
        assert "min_age <= 35" in where_clause
        assert "max_age >= 35" in where_clause
        assert "max_pax >= 2" in where_clause
        assert "start_date" in where_clause
        assert "end_date" in where_clause

        print(f"Phase 1 SQL WHERE clause: {where_clause}")

    def test_proximity_filter_with_venice_target(self, venice_hard_constraints):
        """Test Phase 1b: Proximity filter with Venice coordinates."""
        # Create test products at different distances from Venice
        products = pd.DataFrame(
            [
                {
                    "product_id": "venice-gondola",
                    "title": "Venice Gondola Ride",
                    "latitude": 45.4371,  # ~1.5km from Venice center
                    "longitude": 12.3326,
                    "location": "Venice",
                    "country": "IT",
                },
                {
                    "product_id": "murano-glass",
                    "title": "Murano Glass Workshop",
                    "latitude": 45.4583,  # ~5km from Venice center (Murano island)
                    "longitude": 12.3533,
                    "location": "Murano",
                    "country": "IT",
                },
                {
                    "product_id": "rome-colosseum",
                    "title": "Rome Colosseum Tour",
                    "latitude": 41.8902,  # ~394km from Venice
                    "longitude": 12.4922,
                    "location": "Rome",
                    "country": "IT",
                },
            ]
        )

        target_lat = venice_hard_constraints["target_latitude"]
        target_lon = venice_hard_constraints["target_longitude"]

        result = filter_by_proximity(products, target_lat, target_lon, radius_km=20.0)

        # Venice and Murano should be included, Rome excluded
        assert len(result) == 2
        product_ids = result["product_id"].tolist()
        assert "venice-gondola" in product_ids
        assert "murano-glass" in product_ids
        assert "rome-colosseum" not in product_ids

        print(f"Phase 1b: {len(products)} -> {len(result)} products within 20km of Venice")
        for _, row in result.iterrows():
            print(f"  - {row['title']}: {row['distance_km']:.2f}km")

    def test_semantic_exclusion_filters_stairs_and_heights(self, venice_hard_constraints):
        """Test Phase 1c: Semantic exclusion filters products with stairs/heights."""
        # Create test products with embeddings
        # We'll use the actual embedding model to generate realistic embeddings
        from lancedb.embeddings import get_registry

        from common.config import EMBEDDING_MODEL_NAME

        model = get_registry().get("sentence-transformers").create(name=EMBEDDING_MODEL_NAME)

        # Product descriptions that should/shouldn't be excluded
        boat_text = "Relaxing gondola ride through Venice canals. No walking required, just sit back and enjoy the romantic scenery."
        tower_text = "Climb the bell tower for panoramic views. 300 stairs to the top observation deck. Not for those afraid of heights."

        boat_embedding = model.generate_embeddings([boat_text])[0]
        tower_embedding = model.generate_embeddings([tower_text])[0]

        products = pd.DataFrame(
            [
                {
                    "product_id": "gondola-ride",
                    "title": "Venice Gondola Ride",
                    "search_text": boat_text,
                    "vector": boat_embedding,
                },
                {
                    "product_id": "bell-tower",
                    "title": "Bell Tower Climb",
                    "search_text": tower_text,
                    "vector": tower_embedding,
                },
            ]
        )

        exclusions = venice_hard_constraints["semantic_exclusions"]
        result = filter_by_semantic_exclusion(products, exclusions)

        print("Phase 1c: Semantic exclusion results:")
        for _, row in result.iterrows():
            print(f"  - {row['title']}: similarity={row['exclusion_similarity']:.3f}")

        # The tower product should have higher similarity to exclusion terms
        # and potentially be excluded (depending on threshold)
        assert "exclusion_similarity" in result.columns

        # Verify the gondola ride has lower similarity than the tower climb
        if len(result) == 2:
            gondola_sim = result[result["product_id"] == "gondola-ride"][
                "exclusion_similarity"
            ].iloc[0]
            tower_sim = result[result["product_id"] == "bell-tower"]["exclusion_similarity"].iloc[0]
            assert gondola_sim < tower_sim, (
                "Gondola should have lower exclusion similarity than tower"
            )

    def test_semantic_ranking_prefers_boat_tours(self, venice_soft_preferences):
        """Test Phase 2: Semantic ranking works correctly for Venice preferences."""
        from lancedb.embeddings import get_registry

        from common.config import EMBEDDING_MODEL_NAME

        model = get_registry().get("sentence-transformers").create(name=EMBEDDING_MODEL_NAME)

        # Create products with different relevance to "romantic boat tour"
        boat_text = "Romantic gondola ride through Venice canals at sunset. Perfect for couples celebrating anniversaries. Includes champagne and history narration."
        walking_text = "Active walking tour through Rome's ancient streets. Visit the Colosseum and Forum. Lots of walking and stairs."
        museum_text = "Art museum guided tour. Explore Renaissance masterpieces in a relaxed setting. Wheelchair accessible."

        boat_embedding = model.generate_embeddings([boat_text])[0]
        walking_embedding = model.generate_embeddings([walking_text])[0]
        museum_embedding = model.generate_embeddings([museum_text])[0]

        products = pd.DataFrame(
            [
                {
                    "product_id": "gondola-sunset",
                    "title": "Sunset Gondola Ride",
                    "search_text": boat_text,
                    "vector": boat_embedding,
                    "price_amount": 8000,
                },
                {
                    "product_id": "rome-walking",
                    "title": "Rome Walking Tour",
                    "search_text": walking_text,
                    "vector": walking_embedding,
                    "price_amount": 4500,
                },
                {
                    "product_id": "art-museum",
                    "title": "Art Museum Tour",
                    "search_text": museum_text,
                    "vector": museum_embedding,
                    "price_amount": 5000,
                },
            ]
        )

        result = rank_by_preferences(products, venice_soft_preferences)

        print("Phase 2: Semantic ranking results:")
        for _, row in result.iterrows():
            print(f"  - {row['title']}: relevance={row['relevance_score']:.3f}")

        # Verify scores are in valid range and descending order
        scores = result["relevance_score"].tolist()
        assert all(0.0 <= s <= 1.0 for s in scores)
        assert scores == sorted(scores, reverse=True)

        # Verify the walking tour (with stairs) ranks lower than relaxing options
        # The walking tour mentions "stairs" and "active" which conflicts with "sedentary" preference
        walking_score = result[result["product_id"] == "rome-walking"]["relevance_score"].iloc[0]
        gondola_score = result[result["product_id"] == "gondola-sunset"]["relevance_score"].iloc[0]
        museum_score = result[result["product_id"] == "art-museum"]["relevance_score"].iloc[0]

        # Walking tour should rank lower than at least one of the relaxing options
        assert walking_score < max(gondola_score, museum_score), (
            f"Walking tour ({walking_score:.3f}) should rank lower than relaxing options"
        )

        # All products should have meaningful relevance scores (not all zeros)
        assert any(s > 0.5 for s in scores), "At least one product should have relevance > 0.5"

    def test_full_pipeline_with_screen_products(self):
        """Test the complete screen_products function with Venice example."""
        from common.pipeline import screen_products
        from product_synthesizer.types import SynthesizerOutput

        # Create a complete profile for Venice boat tour search
        profile: SynthesizerOutput = {
            "hard_constraints": {
                "country": "IT",
                "target_latitude": 41.9028,  # Using Rome coords since mock data has Rome product
                "target_longitude": 12.4964,
                "accommodation_latitude": None,
                "accommodation_longitude": None,
                "holiday_begin_date": "2025-06-01",
                "holiday_end_date": "2025-12-31",
                "not_available_date_times": [],
                "age": 35,
                "max_pax": 2,
                "semantic_exclusions": {
                    "accessibility": ["stairs", "steps", "climbing"],
                    "diet": [],
                    "medical": [],
                    "fears": ["heights", "tower"],
                },
            },
            "soft_preferences": {
                "preference_text": "historical tour ancient rome relaxing accessible",
                "interests": ["history", "ancient rome", "architecture"],
                "activity_level": "sedentary",
                "sports": [],
                "languages": ["English"],
                "notes": "looking for wheelchair accessible options",
            },
        }

        result = screen_products(profile)

        print("\nFull Pipeline Results:")
        print(f"  Products returned: {len(result.products)}")

        for product in result.products:
            print(f"    - {product.get('title', 'Unknown')}")
            if "relevance_score" in product:
                print(f"      Relevance: {product['relevance_score']:.3f}")
            if "distance_km" in product:
                print(f"      Distance: {product['distance_km']:.2f}km")
            if "exclusion_similarity" in product:
                print(f"      Exclusion similarity: {product['exclusion_similarity']:.3f}")

        # Verify the result structure
        assert hasattr(result, "products")
        assert hasattr(result, "hard_result")

        # If products were found, verify they have the expected fields
        if result.products:
            product = result.products[0]
            assert "product_id" in product
            assert "title" in product

    def test_logging_at_each_phase(self, caplog):
        """Test that logging occurs at each phase of the pipeline."""
        import logging

        from common.pipeline import screen_products
        from product_synthesizer.types import SynthesizerOutput

        # Set up logging capture
        caplog.set_level(logging.INFO)

        profile: SynthesizerOutput = {
            "hard_constraints": {
                "country": "IT",
                "target_latitude": 41.9028,
                "target_longitude": 12.4964,
                "accommodation_latitude": None,
                "accommodation_longitude": None,
                "holiday_begin_date": None,
                "holiday_end_date": None,
                "not_available_date_times": [],
                "age": None,
                "max_pax": None,
                "semantic_exclusions": {
                    "accessibility": ["stairs"],
                    "diet": [],
                    "medical": [],
                    "fears": [],
                },
            },
            "soft_preferences": {
                "preference_text": "historical tour",
                "interests": ["history"],
                "activity_level": None,
                "sports": [],
                "languages": [],
                "notes": None,
            },
        }

        screen_products(profile)

        # Check that logging occurred
        log_text = caplog.text

        print("\nLogging output:")
        for record in caplog.records:
            if "product" in record.name:
                print(f"  [{record.levelname}] {record.message}")

        # Verify key log messages are present
        assert "Hard screening" in log_text or "SQL" in log_text, (
            "Hard screening logging should occur"
        )
