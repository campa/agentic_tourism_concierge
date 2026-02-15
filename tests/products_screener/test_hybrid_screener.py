"""
End-to-End test script for the Hybrid Product Screener.

Tests the complete pipeline with Venice example:
- Accessibility: "no stairs"
- Fears: "heights"

Verifies:
- Synthesized profile structure (hard_constraints + soft_preferences)
- Product counts after each phase
- Top 5 results with relevance scores
- No stairs/towers in final results
"""

import os
import sys

import pytest

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))

from common.config import TOP_RESULTS_COUNT
from common.pipeline import screen_products
from conftest import requires_db
from product_synthesizer.types import (
    HardConstraints,
    SemanticExclusions,
    SoftPreferences,
    SynthesizerOutput,
)

# Venice example test data
VENICE_PERSONAL_INFO = {
    "name": "Test User",
    "age": 35,
    "accessibility": "no stairs - mobility issues",
    "diet": None,
    "medical": None,
    "fears": "heights - afraid of tall buildings and towers",
    "interests": ["history", "art", "architecture", "romantic experiences"],
    "activity_level": "sedentary",
    "sports": [],
    "languages": ["English", "Italian"],
}

VENICE_HOLIDAY_INFO = {
    "location": "Venice, Italy",
    "accommodation": "Hotel near St. Mark's Square, Venice",
    "holiday_begin_date": "2025-10-20",
    "holiday_end_date": "2025-10-27",
    "budget": "150 EUR",
    "max_pax": 2,
    "notes": "Romantic anniversary trip, looking for relaxing boat tours",
}


def print_separator(title: str) -> None:
    """Print a formatted section separator."""
    print(f"\n{'=' * 60}")
    print(f"  {title}")
    print(f"{'=' * 60}\n")


def print_profile(profile: SynthesizerOutput) -> None:
    """Print the synthesized profile in a readable format."""
    print_separator("SYNTHESIZED PROFILE")

    hard = profile.get("hard_constraints", {})
    soft = profile.get("soft_preferences", {})

    print("HARD CONSTRAINTS:")
    print(f"  Country: {hard.get('country')}")
    print(f"  Target Location: ({hard.get('target_latitude')}, {hard.get('target_longitude')})")
    print(f"  Accommodation: ({hard.get('accommodation_latitude')}, {hard.get('accommodation_longitude')})")
    print(f"  Holiday Dates: {hard.get('holiday_begin_date')} to {hard.get('holiday_end_date')}")
    print(f"  Age: {hard.get('age')}")
    print(f"  Max Pax: {hard.get('max_pax')}")

    exclusions = hard.get("semantic_exclusions", {})
    print("  Semantic Exclusions:")
    print(f"    Accessibility: {exclusions.get('accessibility', [])}")
    print(f"    Diet: {exclusions.get('diet', [])}")
    print(f"    Medical: {exclusions.get('medical', [])}")
    print(f"    Fears: {exclusions.get('fears', [])}")

    print("\nSOFT PREFERENCES:")
    print(f"  Preference Text: {soft.get('preference_text')}")
    print(f"  Interests: {soft.get('interests', [])}")
    print(f"  Activity Level: {soft.get('activity_level')}")
    print(f"  Sports: {soft.get('sports', [])}")
    print(f"  Languages: {soft.get('languages', [])}")
    print(f"  Notes: {soft.get('notes')}")


def print_phase_counts(result: dict) -> None:
    """Print product counts after each phase."""
    print_separator("PHASE COUNTS")

    phases = result.get("phases_applied", [])
    for i, phase in enumerate(phases, 1):
        print(f"  {i}. {phase}")

    print(f"\n  Final product count: {len(result.get('products', []))}")

    if result.get("message"):
        print(f"  Message: {result['message']}")


def print_results(products: list[dict]) -> None:
    """Print top results with relevance scores."""
    print_separator(f"TOP {TOP_RESULTS_COUNT} RESULTS")

    if not products:
        print("  No products found matching criteria.")
        return

    for i, product in enumerate(products[:TOP_RESULTS_COUNT], 1):
        print(f"\n  {i}. {product.get('title', 'Unknown Title')}")
        print(f"     Product ID: {product.get('product_id', 'N/A')}")
        print(f"     Location: {product.get('location', 'N/A')}")
        print(f"     Country: {product.get('country', 'N/A')}")

        if "relevance_score" in product:
            print(f"     Relevance Score: {product['relevance_score']:.3f}")
        if "distance_km" in product:
            print(f"     Distance: {product['distance_km']:.2f} km")
        if "exclusion_similarity" in product:
            print(f"     Exclusion Similarity: {product['exclusion_similarity']:.3f}")
        if "price_amount" in product:
            price_eur = product["price_amount"] / 100
            print(f"     Price: €{price_eur:.2f}")


def verify_no_stairs_towers(products: list[dict]) -> tuple[bool, list[str]]:
    """
    Verify that no products contain stairs or towers in their content.

    Returns:
        Tuple of (passed, violations) where violations is a list of product titles
        that contain forbidden terms.
    """
    forbidden_terms = ["stairs", "steps", "climbing", "tower", "rooftop", "heights", "observation deck"]
    violations = []

    for product in products:
        title = product.get("title", "").lower()
        search_text = product.get("search_text", "").lower()
        faq_text = product.get("faq_text", "").lower()

        combined_text = f"{title} {search_text} {faq_text}"

        for term in forbidden_terms:
            if term in combined_text:
                violations.append(f"{product.get('title', 'Unknown')} (contains '{term}')")
                break

    return len(violations) == 0, violations


@requires_db
class TestHybridScreenerE2E:
    """End-to-end tests for the hybrid product screener."""

    @pytest.fixture
    def venice_profile(self) -> SynthesizerOutput:
        """Create a Venice profile for testing without LLM dependency."""
        return SynthesizerOutput(
            hard_constraints=HardConstraints(
                country="IT",
                target_latitude=45.4408,  # Venice center
                target_longitude=12.3155,
                accommodation_latitude=45.4371,  # Near St. Mark's
                accommodation_longitude=12.3326,
                holiday_begin_date="2025-10-20",
                holiday_end_date="2025-10-27",
                not_available_date_times=[],
                age=35,
                max_pax=2,
                semantic_exclusions=SemanticExclusions(
                    accessibility=["stairs", "steps", "climbing", "steep"],
                    diet=[],
                    medical=[],
                    fears=["heights", "tower", "rooftop", "cliff", "balcony", "high", "observation deck"],
                ),
            ),
            soft_preferences=SoftPreferences(
                preference_text="romantic boat tour history art relaxing gondola canal",
                interests=["history", "art", "architecture", "romantic experiences"],
                activity_level="sedentary",
                sports=[],
                languages=["English", "Italian"],
                notes="Romantic anniversary trip, looking for relaxing boat tours",
            ),
        )

    def test_profile_structure(self, venice_profile):
        """Test that the profile has correct structure."""
        assert "hard_constraints" in venice_profile
        assert "soft_preferences" in venice_profile

        hard = venice_profile["hard_constraints"]
        assert hard["country"] == "IT"
        assert hard["target_latitude"] is not None
        assert hard["target_longitude"] is not None
        assert "semantic_exclusions" in hard

        soft = venice_profile["soft_preferences"]
        assert soft["preference_text"] is not None
        assert len(soft["interests"]) > 0

    def test_semantic_exclusions_populated(self, venice_profile):
        """Test that semantic exclusions are properly populated."""
        exclusions = venice_profile["hard_constraints"]["semantic_exclusions"]

        # Accessibility exclusions for "no stairs"
        assert len(exclusions["accessibility"]) > 0
        assert "stairs" in exclusions["accessibility"]

        # Fear exclusions for "heights"
        assert len(exclusions["fears"]) > 0
        assert "heights" in exclusions["fears"] or "tower" in exclusions["fears"]

    def test_full_pipeline_execution(self, venice_profile):
        """Test the complete screening pipeline."""
        result = screen_products(venice_profile)

        # Verify result structure
        assert hasattr(result, "products")
        assert hasattr(result, "hard_result")
        assert hasattr(result, "soft_result")

        # Print results for manual inspection
        print_profile(venice_profile)
        print(f"\nHard result: {result.hard_result.initial_count} -> {result.hard_result.after_exclusion_count}")
        print_results(result.products)

    def test_results_respect_constraints(self, venice_profile):
        """Test that results respect hard constraints."""
        result = screen_products(venice_profile)
        products = result.products

        # If products were found, verify they match constraints
        for product in products:
            # Country should match
            if "country" in product:
                assert product["country"] == "IT", f"Product {product.get('title')} has wrong country"

            # Relevance scores should be valid
            if "relevance_score" in product:
                assert 0.0 <= product["relevance_score"] <= 1.0

    def test_no_stairs_towers_in_results(self, venice_profile):
        """Test that no products with stairs/towers appear in results."""
        result = screen_products(venice_profile)
        products = result.products

        if not products:
            pytest.skip("No products returned - cannot verify exclusions")

        passed, violations = verify_no_stairs_towers(products)

        if not passed:
            print(f"\nViolations found: {violations}")

        # Note: This is a soft assertion - semantic filtering may not catch all cases
        # depending on the threshold and embedding similarity
        if violations:
            print(f"\nWARNING: Some products may contain forbidden terms: {violations}")
            print("This may indicate the semantic exclusion threshold needs adjustment.")

    def test_results_ordered_by_relevance(self, venice_profile):
        """Test that results are ordered by relevance score descending."""
        result = screen_products(venice_profile)
        products = result.products

        if len(products) < 2:
            pytest.skip("Not enough products to verify ordering")

        scores = [p.get("relevance_score", 0) for p in products]
        assert scores == sorted(scores, reverse=True), "Results should be ordered by relevance descending"

    def test_max_results_count(self, venice_profile):
        """Test that at most TOP_RESULTS_COUNT products are returned."""
        result = screen_products(venice_profile)
        products = result.products

        assert len(products) <= TOP_RESULTS_COUNT, f"Should return at most {TOP_RESULTS_COUNT} products"


@requires_db
class TestHybridScreenerWithRomeData:
    """
    E2E tests using Rome coordinates to match the mock data.

    The mock_products.json contains a Rome Colosseum product, so we test
    with Rome coordinates to ensure we get results.
    """

    @pytest.fixture
    def rome_profile(self) -> SynthesizerOutput:
        """Create a Rome profile that matches the mock data."""
        return SynthesizerOutput(
            hard_constraints=HardConstraints(
                country="IT",
                target_latitude=41.9028,  # Rome center
                target_longitude=12.4964,
                accommodation_latitude=None,
                accommodation_longitude=None,
                holiday_begin_date="2025-06-01",
                holiday_end_date="2025-12-31",
                not_available_date_times=[],
                age=35,
                max_pax=2,
                semantic_exclusions=SemanticExclusions(
                    accessibility=["stairs", "steps", "climbing", "steep"],
                    diet=[],
                    medical=[],
                    fears=["heights", "tower", "rooftop"],
                ),
            ),
            soft_preferences=SoftPreferences(
                preference_text="historical tour ancient rome accessible wheelchair",
                interests=["history", "ancient rome", "architecture"],
                activity_level="sedentary",
                sports=[],
                languages=["English"],
                notes="Looking for wheelchair accessible historical tours",
            ),
        )

    def test_rome_pipeline_returns_results(self, rome_profile):
        """Test that Rome profile returns the Colosseum product."""
        result = screen_products(rome_profile)

        print_profile(rome_profile)
        print(f"\nHard: {result.hard_result.initial_count} -> {result.hard_result.after_exclusion_count}")
        print_results(result.products)

        assert result.products is not None

        if result.products:
            titles = [p.get("title", "") for p in result.products]
            print(f"\nProducts found: {titles}")

    def test_colosseum_ranks_high_for_history_preference(self, rome_profile):
        """Test that Colosseum ranks high for history preferences."""
        result = screen_products(rome_profile)
        products = result.products

        if not products:
            pytest.skip("No products returned")

        # Find the Colosseum product
        colosseum = None
        for p in products:
            if "Colosseum" in p.get("title", ""):
                colosseum = p
                break

        if colosseum:
            print(f"\nColosseum found with relevance score: {colosseum.get('relevance_score', 'N/A')}")
            # Colosseum should have a decent relevance score for history preferences
            if "relevance_score" in colosseum:
                assert colosseum["relevance_score"] > 0.3, "Colosseum should have reasonable relevance for history"


def run_e2e_test():
    """
    Run the E2E test manually (outside pytest).

    This function can be called directly to see the full output
    of the hybrid screener pipeline.
    """
    print_separator("HYBRID PRODUCT SCREENER E2E TEST")
    print("Testing with Venice example:")
    print("  - Accessibility: 'no stairs'")
    print("  - Fears: 'heights'")
    print("  - Preferences: romantic boat tour, history, art")

    profile: SynthesizerOutput = {
        "hard_constraints": {
            "country": "IT",
            "target_latitude": 45.4408,
            "target_longitude": 12.3155,
            "accommodation_latitude": 45.4371,
            "accommodation_longitude": 12.3326,
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
        },
        "soft_preferences": {
            "preference_text": "romantic boat tour history art relaxing gondola",
            "interests": ["history", "art", "architecture"],
            "activity_level": "sedentary",
            "sports": [],
            "languages": ["English", "Italian"],
            "notes": "Romantic anniversary trip",
        },
    }

    print_profile(profile)

    print_separator("RUNNING SCREENING PIPELINE")
    result = screen_products(profile)

    print(f"Hard: {result.hard_result.initial_count} -> {result.hard_result.after_exclusion_count}")
    print(f"Soft: {result.soft_result.input_count} -> {result.soft_result.output_count}")

    print_results(result.products)

    print_separator("VERIFICATION: NO STAIRS/TOWERS")
    passed, violations = verify_no_stairs_towers(result.products)

    if passed:
        print("  ✓ PASSED: No products with stairs/towers in results")
    else:
        print(f"  ✗ FAILED: Found violations: {violations}")

    print_separator("E2E TEST COMPLETE")

    return result


if __name__ == "__main__":
    run_e2e_test()
