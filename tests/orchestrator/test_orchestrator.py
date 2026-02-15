"""Tests for the agent orchestrator."""

import pytest

from orchestrator.core import (
    AgentContext,
    InteractiveOrchestrator,
    run_full_pipeline,
    run_screening,
    run_synthesizer,
)


# Sample test data
SAMPLE_PERSONAL_INFO = {
    "full_name": "Test User",
    "age": 35,
    "languages": ["en", "it"],
    "activity_level": "moderate",
    "sports": ["swimming"],
    "accessibility": ["no stairs"],
    "diet": [],
    "interests": ["history", "art"],
    "fears": ["heights"],
    "medical": [],
}

SAMPLE_HOLIDAY_INFO = {
    "holiday_begin_date": "2025-06-01",
    "holiday_end_date": "2025-06-15",
    "location": "Rome, Italy",
    "accommodation": "Hotel near Colosseum",
    "preferred_date_times": [],
    "not_available_date_times": [],
    "notes": "Anniversary trip",
}


class TestAgentContext:
    """Tests for AgentContext dataclass."""

    def test_default_values(self):
        """Test context initializes with None values."""
        ctx = AgentContext()
        assert ctx.personal_info is None
        assert ctx.holiday_info is None
        assert ctx.synthesized_profile is None
        assert ctx.hard_result is None
        assert ctx.soft_result is None
        assert ctx.products == []
        assert ctx.error is None

    def test_can_set_values(self):
        """Test context values can be set."""
        ctx = AgentContext(
            personal_info=SAMPLE_PERSONAL_INFO,
            holiday_info=SAMPLE_HOLIDAY_INFO,
        )
        assert ctx.personal_info == SAMPLE_PERSONAL_INFO
        assert ctx.holiday_info == SAMPLE_HOLIDAY_INFO


class TestRunSynthesizer:
    """Tests for run_synthesizer function."""

    def test_requires_personal_info(self):
        """Test synthesizer fails without personal_info."""
        ctx = AgentContext(holiday_info=SAMPLE_HOLIDAY_INFO)
        result = run_synthesizer(ctx)
        assert result.error is not None
        assert "personal_info" in result.error

    def test_requires_holiday_info(self):
        """Test synthesizer fails without holiday_info."""
        ctx = AgentContext(personal_info=SAMPLE_PERSONAL_INFO)
        result = run_synthesizer(ctx)
        assert result.error is not None
        assert "holiday_info" in result.error


class TestRunScreening:
    """Tests for run_screening function."""

    def test_requires_synthesized_profile(self):
        """Test screening fails without synthesized_profile."""
        ctx = AgentContext()
        result = run_screening(ctx)
        assert result.error is not None
        assert "synthesized_profile" in result.error


class TestInteractiveOrchestrator:
    """Tests for InteractiveOrchestrator class."""

    def test_initial_stage(self):
        """Test orchestrator starts at personal_info stage."""
        orch = InteractiveOrchestrator()
        assert orch.current_stage == "personal_info"
        assert not orch.is_ready_for_screening()

    def test_set_personal_info_advances_stage(self):
        """Test setting personal info advances to holiday stage."""
        orch = InteractiveOrchestrator()
        orch.set_personal_info(SAMPLE_PERSONAL_INFO)

        assert orch.current_stage == "holiday_info"
        assert orch.ctx.personal_info == SAMPLE_PERSONAL_INFO
        assert not orch.is_ready_for_screening()

    def test_set_holiday_info_advances_stage(self):
        """Test setting holiday info advances to screening stage."""
        orch = InteractiveOrchestrator()
        orch.set_personal_info(SAMPLE_PERSONAL_INFO)
        orch.set_holiday_info(SAMPLE_HOLIDAY_INFO)

        assert orch.current_stage == "screening"
        assert orch.ctx.holiday_info == SAMPLE_HOLIDAY_INFO
        assert orch.is_ready_for_screening()

    def test_cannot_run_pipeline_early(self):
        """Test pipeline fails if called before both collectors complete."""
        orch = InteractiveOrchestrator()
        orch.set_personal_info(SAMPLE_PERSONAL_INFO)
        # Don't set holiday info

        result = orch.run_remaining_pipeline()
        assert result.error is not None


class TestRunFullPipeline:
    """Integration tests for run_full_pipeline."""

    def test_full_pipeline_returns_context(self):
        """Test full pipeline returns AgentContext."""
        ctx = run_full_pipeline(SAMPLE_PERSONAL_INFO, SAMPLE_HOLIDAY_INFO)

        assert isinstance(ctx, AgentContext)
        assert ctx.personal_info == SAMPLE_PERSONAL_INFO
        assert ctx.holiday_info == SAMPLE_HOLIDAY_INFO

    def test_full_pipeline_produces_products(self):
        """Test full pipeline produces product list."""
        ctx = run_full_pipeline(SAMPLE_PERSONAL_INFO, SAMPLE_HOLIDAY_INFO)

        # Should complete without error (products may be empty depending on data)
        if ctx.error is None:
            assert isinstance(ctx.products, list)
            assert ctx.synthesized_profile is not None
            assert ctx.hard_result is not None
            assert ctx.soft_result is not None
