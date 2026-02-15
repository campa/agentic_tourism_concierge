"""Type definitions for the product screening system."""

from typing import TypedDict


class SemanticExclusions(TypedDict):
    """Semantic exclusion terms by category."""

    accessibility: list[str]
    diet: list[str]
    medical: list[str]
    fears: list[str]


class HardConstraints(TypedDict):
    """Non-negotiable filters that disqualify products if violated."""

    country: str | None
    target_latitude: float | None
    target_longitude: float | None
    accommodation_latitude: float | None
    accommodation_longitude: float | None
    holiday_begin_date: str | None
    holiday_end_date: str | None
    not_available_date_times: list[str]
    age: int | None
    max_pax: int | None
    semantic_exclusions: SemanticExclusions


class SoftPreferences(TypedDict):
    """Preferences that influence ranking but do not disqualify products."""

    preference_text: str
    interests: list[str]
    activity_level: str | None
    sports: list[str]
    languages: list[str]
    notes: str | None


class SynthesizerOutput(TypedDict):
    """Complete synthesizer output with hard constraints and soft preferences."""

    hard_constraints: HardConstraints
    soft_preferences: SoftPreferences


class SynthesizerError(TypedDict):
    """Structured error returned when synthesizer fails."""

    error: bool
    error_type: str
    error_message: str
    raw_response: str | None


def is_synthesizer_error(result: SynthesizerOutput | SynthesizerError) -> bool:
    """Check if the synthesizer result is an error."""
    return isinstance(result, dict) and result.get("error", False) is True
