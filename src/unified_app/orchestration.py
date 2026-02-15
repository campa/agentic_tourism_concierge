"""
Orchestration adapter layer for the Unified Web Layer.

This module provides a UI-agnostic interface that wraps core logic,
enabling any frontend (Chainlit, CLI, REST API) to interact with
the pipeline without direct coupling to agent core modules.

NO Chainlit imports allowed in this file.
"""

from dataclasses import dataclass
from typing import Literal

from common.llm_utils import extract_json, get_ai_response_streaming
from holiday_information_collector.core import get_first_message as holiday_first_message
from holiday_information_collector.core import (
    get_system_instructions as holiday_system_instructions,
)
from orchestrator.core import AgentContext, InteractiveOrchestrator
from personal_information_collector.core import get_first_message as personal_first_message
from personal_information_collector.core import (
    get_system_instructions as personal_system_instructions,
)

# Type alias for pipeline stages
Stage = Literal["personal", "holiday", "processing", "results", "error"]


@dataclass
class StageConfig:
    """Configuration for a conversation stage."""

    system_prompt: str
    first_message: str
    stage_name: str


def get_stage_config(stage: Stage) -> StageConfig:
    """
    Get the configuration for a given conversation stage.

    Args:
        stage: The pipeline stage ("personal" or "holiday")

    Returns:
        StageConfig with system_prompt, first_message, and stage_name

    Raises:
        ValueError: If stage is not a conversation stage
    """
    if stage == "personal":
        return StageConfig(
            system_prompt=personal_system_instructions(),
            first_message=personal_first_message(),
            stage_name="Personal Information Collection",
        )
    elif stage == "holiday":
        return StageConfig(
            system_prompt=holiday_system_instructions(),
            first_message=holiday_first_message(),
            stage_name="Holiday Information Collection",
        )
    else:
        raise ValueError(f"Stage '{stage}' does not have a conversation config")


def process_response(response: str) -> tuple[str, dict | None]:
    """
    Process an LLM response, extracting JSON if conversation is complete.

    Delegates to the existing extract_json() utility from common.llm_utils.

    Args:
        response: The raw LLM response text

    Returns:
        Tuple of (display_text, extracted_json_or_none)
        - display_text: Text to show the user (before CONVERSATION_COMPLETE marker)
        - extracted_json_or_none: Parsed JSON dict if complete, None otherwise
    """
    return extract_json(response)


# Re-export core classes for convenience
__all__ = [
    "Stage",
    "StageConfig",
    "get_stage_config",
    "process_response",
    "get_ai_response_streaming",
    "AgentContext",
    "InteractiveOrchestrator",
]
