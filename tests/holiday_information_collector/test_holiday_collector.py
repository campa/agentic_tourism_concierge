"""Tests for holiday_information_collector core module."""

from datetime import date

from holiday_information_collector.core import (
    COLLECTION_GUIDE,
    get_first_message,
    get_system_instructions,
)


class TestCollectionGuide:
    """Tests for the COLLECTION_GUIDE configuration."""

    def test_collection_guide_has_required_fields(self):
        """Verify all required holiday info fields are defined."""
        required_fields = [
            "holiday_begin_date",
            "holiday_end_date",
            "location",
            "accommodation",
            "preferred_date_times",
            "not_available_date_times",
            "notes",
        ]
        for field in required_fields:
            assert field in COLLECTION_GUIDE, f"Missing field: {field}"

    def test_collection_guide_fields_have_hint_and_type(self):
        """Verify each field has hint and type."""
        for field, config in COLLECTION_GUIDE.items():
            assert "hint" in config, f"Field {field} missing 'hint'"
            assert "type" in config, f"Field {field} missing 'type'"

    def test_date_fields_are_strings(self):
        """Verify date fields are typed as strings."""
        assert COLLECTION_GUIDE["holiday_begin_date"]["type"] == "string"
        assert COLLECTION_GUIDE["holiday_end_date"]["type"] == "string"


class TestGetSystemInstructions:
    """Tests for get_system_instructions function."""

    def test_returns_string(self):
        """Verify function returns a string."""
        result = get_system_instructions()
        assert isinstance(result, str)

    def test_contains_today_date(self):
        """Verify prompt contains today's date."""
        result = get_system_instructions()
        today = date.today().strftime("%Y-%m-%d")
        assert today in result

    def test_contains_all_collection_fields(self):
        """Verify prompt mentions all fields to collect."""
        result = get_system_instructions()
        for field in COLLECTION_GUIDE.keys():
            assert field in result, f"Field {field} not in system instructions"

    def test_contains_json_schema(self):
        """Verify prompt contains JSON schema instruction."""
        result = get_system_instructions()
        assert '"holiday_begin_date"' in result
        assert '"location"' in result

    def test_contains_conversation_complete_marker(self):
        """Verify prompt mentions CONVERSATION_COMPLETE trigger."""
        result = get_system_instructions()
        assert "CONVERSATION_COMPLETE" in result

    def test_contains_operating_phases(self):
        """Verify prompt defines operating phases."""
        result = get_system_instructions()
        assert "COLLECTION" in result
        assert "REVIEW" in result
        assert "CORRECTION" in result


class TestGetFirstMessage:
    """Tests for get_first_message function."""

    def test_returns_string(self):
        """Verify function returns a string."""
        result = get_first_message()
        assert isinstance(result, str)

    def test_message_not_empty(self):
        """Verify message is not empty."""
        result = get_first_message()
        assert len(result) > 0

    def test_message_indicates_readiness(self):
        """Verify message indicates readiness to start."""
        result = get_first_message()
        assert "ready" in result.lower() or "start" in result.lower()
