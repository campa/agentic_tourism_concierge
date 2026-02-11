"""LLM utilities for Ollama interactions."""

import json

import ollama

from common.config import LLM_MODEL
from common.logging_config import get_logger

logger = get_logger("common_llm_utils")

# Conversation markers
CONVERSATION_COMPLETE_MARKER = "CONVERSATION_COMPLETE"


def get_ai_response(messages: list[dict]) -> str:
    """Get a plain text response from the LLM."""
    response = ollama.chat(model=LLM_MODEL, messages=messages)
    return response["message"]["content"]


def get_json_response(messages: list[dict]) -> dict | None:
    """Get a JSON response from the LLM (forces JSON format)."""
    try:
        response = ollama.chat(
            model=LLM_MODEL,
            messages=messages,
            format="json",
        )
        content = response["message"]["content"]
        return json.loads(content)
    except Exception as e:
        logger.error(f"Failed to parse LLM JSON response: {e}")
        return None


def extract_json(assistant_msg: str) -> tuple[str, dict | None]:
    """
    Extract JSON from a message containing CONVERSATION_COMPLETE marker.

    Returns:
        Tuple of (text_before_marker, parsed_json_or_none)
    """
    if CONVERSATION_COMPLETE_MARKER not in assistant_msg:
        return assistant_msg, None

    try:
        parts = assistant_msg.split(CONVERSATION_COMPLETE_MARKER, 1)
        text_part = parts[0].strip()
        raw_part = parts[1].strip()

        start = raw_part.find("{")
        end = raw_part.rfind("}")

        if start != -1 and end != -1 and end > start:
            json_part = raw_part[start : end + 1]
            return text_part, json.loads(json_part)

        return assistant_msg, None
    except Exception as e:
        logger.error(f"Failed to extract JSON from assistant message: {e}")
        return assistant_msg, None
