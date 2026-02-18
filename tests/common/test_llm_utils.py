"""Tests for common.llm_utils module."""

from common.llm_utils import CONVERSATION_COMPLETE_MARKER, extract_json


class TestExtractJson:
    """Tests for extract_json function."""

    def test_no_marker_returns_original(self):
        """When no marker present, return original text and None."""
        text = "Hello, how are you?"
        result_text, result_json = extract_json(text)
        assert result_text == text
        assert result_json is None

    def test_extracts_valid_json(self):
        """When marker + valid JSON present, extract both parts."""
        text = f'Thank you! {CONVERSATION_COMPLETE_MARKER} {{"name": "Test", "age": 30}}'
        result_text, result_json = extract_json(text)
        assert result_text == "Thank you!"
        assert result_json == {"name": "Test", "age": 30}

    def test_handles_nested_json(self):
        """Handles nested JSON structures."""
        json_str = '{"name": "Test", "items": ["a", "b"], "nested": {"key": "val"}}'
        text = f"Done {CONVERSATION_COMPLETE_MARKER} {json_str}"
        result_text, result_json = extract_json(text)
        assert result_text == "Done"
        assert result_json["items"] == ["a", "b"]
        assert result_json["nested"]["key"] == "val"

    def test_handles_invalid_json(self):
        """When JSON is malformed, return original text and None."""
        text = f"Done {CONVERSATION_COMPLETE_MARKER} {{not valid json}}"
        result_text, result_json = extract_json(text)
        assert result_json is None

    def test_handles_no_json_after_marker(self):
        """When marker present but no JSON, return original and None."""
        text = f"Done {CONVERSATION_COMPLETE_MARKER} no json here"
        result_text, result_json = extract_json(text)
        assert result_json is None

    def test_empty_text_before_marker(self):
        """When nothing before marker, text part is empty."""
        text = f'{CONVERSATION_COMPLETE_MARKER} {{"key": "value"}}'
        result_text, result_json = extract_json(text)
        assert result_text == ""
        assert result_json == {"key": "value"}


class TestLogMetrics:
    """Tests for _log_metrics function."""

    def test_log_metrics_does_not_raise(self):
        """Verify _log_metrics handles valid Ollama response without errors."""
        from common.llm_utils import _log_metrics

        response = {
            "total_duration": 5_000_000_000,
            "prompt_eval_duration": 500_000_000,
            "eval_duration": 4_000_000_000,
            "load_duration": 100_000_000,
            "prompt_eval_count": 100,
            "eval_count": 50,
        }
        # Should not raise
        _log_metrics(response, caller="test")

    def test_log_metrics_handles_empty_response(self):
        """Verify _log_metrics handles missing fields gracefully."""
        from common.llm_utils import _log_metrics

        # Should not raise even with empty dict
        _log_metrics({}, caller="test")

    def test_log_metrics_handles_zero_eval_duration(self):
        """Verify _log_metrics handles zero eval_duration (avoids division by zero)."""
        from common.llm_utils import _log_metrics

        response = {
            "total_duration": 1_000_000,
            "eval_duration": 0,
            "eval_count": 0,
        }
        # Should not raise
        _log_metrics(response, caller="test")
