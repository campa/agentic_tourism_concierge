"""Tests for the Product Soft Screener Agent."""

import pytest

from product_hard_screener.core import screen_hard
from product_soft_screener.core import (
    SoftScreeningResult,
    load_products_by_ids,
    rank_by_preferences,
    screen_soft,
)
from product_synthesizer.types import HardConstraints, SoftPreferences


class TestSoftScreenerCore:
    """Tests for soft screener core functions."""

    def test_load_products_empty_ids(self):
        """Test loading with empty ID list returns empty DataFrame."""
        df = load_products_by_ids([])
        assert df.empty

    def test_screen_soft_empty_ids(self):
        """Test soft screening with empty IDs."""
        soft_prefs: SoftPreferences = {
            "preference_text": "historical tours",
            "interests": ["history"],
            "activity_level": "moderate",
            "sports": [],
            "languages": ["en"],
            "notes": None,
        }
        
        result = screen_soft([], soft_prefs)
        
        assert isinstance(result, SoftScreeningResult)
        assert result.products == []
        assert result.input_count == 0
        assert result.output_count == 0


class TestSoftScreenerIntegration:
    """Integration tests for soft screener with database."""

    @pytest.fixture
    def italy_constraints(self) -> HardConstraints:
        """Constraints for Italian products."""
        return {
            "country": "IT",
            "target_latitude": 41.9028,
            "target_longitude": 12.4964,
            "accommodation_latitude": None,
            "accommodation_longitude": None,
            "holiday_begin_date": "2025-06-01",
            "holiday_end_date": "2025-12-31",
            "not_available_date_times": [],
            "age": 35,
            "max_pax": 2,
            "semantic_exclusions": {},
        }

    @pytest.fixture
    def history_preferences(self) -> SoftPreferences:
        """Preferences for history-focused tours."""
        return {
            "preference_text": "historical tours, ancient Rome, museums",
            "interests": ["history", "art", "architecture"],
            "activity_level": "moderate",
            "sports": [],
            "languages": ["en"],
            "notes": "Looking for educational experiences",
        }

    def test_screen_soft_returns_result(self, italy_constraints, history_preferences):
        """Test that screen_soft returns a SoftScreeningResult."""
        # First get IDs from hard screener
        hard_result = screen_hard(italy_constraints)
        
        # Then apply soft screening
        result = screen_soft(hard_result.filtered_ids, history_preferences)
        
        assert isinstance(result, SoftScreeningResult)
        assert isinstance(result.products, list)

    def test_screen_soft_products_have_scores(self, italy_constraints, history_preferences):
        """Test that soft screening adds relevance scores."""
        hard_result = screen_hard(italy_constraints)
        result = screen_soft(hard_result.filtered_ids, history_preferences)
        
        if result.products:
            first_product = result.products[0]
            assert "relevance_score" in first_product
            assert 0.0 <= first_product["relevance_score"] <= 1.0

    def test_screen_soft_respects_top_n(self, italy_constraints, history_preferences):
        """Test that soft screening respects top_n limit."""
        hard_result = screen_hard(italy_constraints)
        
        result = screen_soft(hard_result.filtered_ids, history_preferences, top_n=3)
        
        assert len(result.products) <= 3

    def test_screen_soft_no_vector_in_output(self, italy_constraints, history_preferences):
        """Test that vector field is removed from output."""
        hard_result = screen_hard(italy_constraints)
        result = screen_soft(hard_result.filtered_ids, history_preferences)
        
        for product in result.products:
            assert "vector" not in product


class TestPipelineIntegration:
    """Tests for the full hard -> soft pipeline."""

    def test_full_pipeline(self):
        """Test the complete pipeline from hard to soft screening."""
        from common.pipeline import screen_products, PipelineResult
        from product_synthesizer.types import SynthesizerOutput
        
        profile: SynthesizerOutput = {
            "hard_constraints": {
                "country": "IT",
                "target_latitude": 41.9028,
                "target_longitude": 12.4964,
                "accommodation_latitude": None,
                "accommodation_longitude": None,
                "holiday_begin_date": "2025-06-01",
                "holiday_end_date": "2025-12-31",
                "not_available_date_times": [],
                "age": 35,
                "max_pax": 2,
                "semantic_exclusions": {},
            },
            "soft_preferences": {
                "preference_text": "historical tours",
                "interests": ["history"],
                "activity_level": "moderate",
                "sports": [],
                "languages": ["en"],
                "notes": None,
            },
        }

        result = screen_products(profile)

        assert isinstance(result, PipelineResult)
        assert isinstance(result.products, list)
        assert result.hard_result is not None
        assert result.soft_result is not None

    def test_screen_products_returns_pipeline_result(self):
        """Test screen_products returns PipelineResult."""
        from common.pipeline import screen_products, PipelineResult
        from product_synthesizer.types import SynthesizerOutput

        profile: SynthesizerOutput = {
            "hard_constraints": {
                "country": "IT",
                "target_latitude": 41.9028,
                "target_longitude": 12.4964,
                "accommodation_latitude": None,
                "accommodation_longitude": None,
                "holiday_begin_date": "2025-06-01",
                "holiday_end_date": "2025-12-31",
                "not_available_date_times": [],
                "age": 35,
                "max_pax": 2,
                "semantic_exclusions": {},
            },
            "soft_preferences": {
                "preference_text": "historical tours",
                "interests": ["history"],
                "activity_level": "moderate",
                "sports": [],
                "languages": ["en"],
                "notes": None,
            },
        }

        result = screen_products(profile)

        assert isinstance(result, PipelineResult)
        assert isinstance(result.products, list)
        assert result.hard_result is not None
        assert result.soft_result is not None
