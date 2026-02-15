"""
Unified Web Layer for Agentic Tourism Concierge.

This package provides a single Chainlit application that orchestrates
the complete pipeline: Personal Collector → Holiday Collector →
Synthesizer → Hard Screener → Soft Screener → Results.
"""

from unified_app.formatting import (
    format_error_for_display,
    format_progress,
    format_results,
)
from unified_app.orchestration import (
    AgentContext,
    InteractiveOrchestrator,
    Stage,
    StageConfig,
    get_stage_config,
    process_response,
)

__all__ = [
    # Orchestration
    "Stage",
    "StageConfig",
    "get_stage_config",
    "process_response",
    "AgentContext",
    "InteractiveOrchestrator",
    # Formatting
    "format_progress",
    "format_results",
    "format_error_for_display",
]
