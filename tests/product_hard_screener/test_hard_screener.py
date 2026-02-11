"""Tests for the Product Hard Screener Agent."""

import pytest

from product_hard_screener.core import (
    HardScreeningResult,
    build_sql_where,
    filter_by_proximity,
    filter_by_semantic_exclusion,
    haversine_distance,
    screen_hard,
)
from product_synthesizer.types import HardConstraints


class TestHardScreenerCore:
    """Tests for hard screener core functions."""

    def test_build_sql_where_country(self):
        """Test SQL WHERE with country constraint."""
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
            "semantic_exclusions": {},
        }
        
        where = build_sql_where(constraints)
        assert "country = 'IT'" in where

    def test_build_sql_where_full(self):
        """Test SQL WHERE with all constraints."""
        constraints: HardConstraints = {
            "country": "IT",
            "target_latitude": 41.9,
            "target_longitude": 12.5,
            "accommodation_latitude": None,
            "accommodation_longitude": None,
            "holiday_begin_date": "2025-06-01",
            "holiday_end_date": "2025-06-15",
            "not_available_date_times": [],
            "age": 35,
            "max_pax": 2,
            "semantic_exclusions": {},
        }
        
        where = build_sql_where(constraints)
        assert "country = 'IT'" in where
        assert "min_age" in where
        assert "max_age" in where
        assert "max_pax" in where

    def test_haversine_distance_same_point(self):
        """Test distance between same point is zero."""
        dist = haversine_distance(41.9, 12.5, 41.9, 12.5)
        assert dist == 0.0

    def test_haversine_distance_rome_venice(self):
        """Test distance between Rome and Venice (~400km)."""
        rome_lat, rome_lon = 41.9028, 12.4964
        venice_lat, venice_lon = 45.4408, 12.3155
        
        dist = haversine_distance(rome_lat, rome_lon, venice_lat, venice_lon)
        assert 390 < dist < 400  # ~394km


class TestHardScreenerIntegration:
    """Integration tests for hard screener with database."""

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
            "semantic_exclusions": {
                "accessibility": [],
                "diet": [],
                "medical": [],
                "fears": [],
            },
        }

    def test_screen_hard_returns_result(self, italy_constraints):
        """Test that screen_hard returns a HardScreeningResult."""
        result = screen_hard(italy_constraints)
        
        assert isinstance(result, HardScreeningResult)
        assert isinstance(result.filtered_ids, list)
        assert result.initial_count >= 0

    def test_screen_hard_returns_tuples(self, italy_constraints):
        """Test that filtered_ids contains (product_id, option_id, unit_id) tuples."""
        result = screen_hard(italy_constraints)
        
        if result.filtered_ids:
            first_id = result.filtered_ids[0]
            assert isinstance(first_id, tuple)
            assert len(first_id) == 3  # product_id, option_id, unit_id

    def test_screen_hard_with_exclusions(self):
        """Test hard screening with semantic exclusions."""
        constraints: HardConstraints = {
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
            "semantic_exclusions": {
                "accessibility": ["stairs", "climbing"],
                "diet": [],
                "medical": [],
                "fears": ["heights"],
            },
        }
        
        result = screen_hard(constraints)
        
        # Should have fewer results after exclusions
        assert result.after_exclusion_count <= result.after_proximity_count
