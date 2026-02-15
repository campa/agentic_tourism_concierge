"""LLM utilities for Ollama interactions."""

import json

import ollama

from common.config import LLM_MODEL
from common.logging_config import get_logger

logger = get_logger("common_llm_utils")

# Conversation markers
CONVERSATION_COMPLETE_MARKER = "CONVERSATION_COMPLETE"


def _log_llm_context(messages: list[dict], caller: str = "unknown") -> None:
    """
    Log the full LLM context/messages for debugging prompts.

    Uses DEBUG level - control visibility via logging configuration.

    Args:
        messages: The full message history being sent to the LLM
        caller: Name of the calling function for context
    """
    logger.debug(f"\n{'='*80}")
    logger.debug(f"LLM CALL from: {caller}")
    logger.debug(f"Model: {LLM_MODEL}")
    logger.debug(f"Message count: {len(messages)}")
    logger.debug(f"{'='*80}")

    for i, msg in enumerate(messages):
        role = msg.get("role", "unknown")
        content = msg.get("content", "")

        logger.debug(f"\n{'─'*40}")
        logger.debug(f"[{i}] ROLE: {role.upper()}")
        logger.debug(f"{'─'*40}")
        logger.debug(f"{content}")

    logger.debug(f"\n{'='*80}")
    logger.debug("END LLM CONTEXT")
    logger.debug(f"{'='*80}\n")


def get_ai_response(messages: list[dict]) -> str:
    """Get a plain text response from the LLM."""
    _log_llm_context(messages, caller="get_ai_response")
    response = ollama.chat(model=LLM_MODEL, messages=messages)
    response_content = response["message"]["content"]

    logger.debug(f"\n{'─'*40}")
    logger.debug("LLM RESPONSE:")
    logger.debug(f"{'─'*40}")
    logger.debug(f"{response_content}")
    logger.debug(f"{'─'*40}\n")

    return response_content

def get_ai_response_streaming(messages: list[dict]):
    """
    Get a streaming response from the LLM.

    Yields individual tokens/chunks as they are generated.

    Args:
        messages: List of message dicts with 'role' and 'content'

    Yields:
        str: Individual tokens or small chunks as they become available
    """
    _log_llm_context(messages, caller="get_ai_response_streaming")

    full_response = ""
    stream = ollama.chat(model=LLM_MODEL, messages=messages, stream=True)
    for chunk in stream:
        if "message" in chunk and "content" in chunk["message"]:
            token = chunk["message"]["content"]
            full_response += token
            yield token

    # Log the complete response after streaming finishes
    logger.debug(f"\n{'─'*40}")
    logger.debug("LLM STREAMING RESPONSE (complete):")
    logger.debug(f"{'─'*40}")
    logger.debug(f"{full_response}")
    logger.debug(f"{'─'*40}\n")



def get_json_response(messages: list[dict]) -> dict | None:
    """Get a JSON response from the LLM (forces JSON format)."""
    _log_llm_context(messages, caller="get_json_response")
    try:
        response = ollama.chat(
            model=LLM_MODEL,
            messages=messages,
            format="json",
        )
        content = response["message"]["content"]

        logger.debug(f"\n{'─'*40}")
        logger.debug("LLM JSON RESPONSE:")
        logger.debug(f"{'─'*40}")
        logger.debug(f"{content}")
        logger.debug(f"{'─'*40}\n")

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
