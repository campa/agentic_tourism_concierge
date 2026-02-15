import json

import ollama

from common.logging_config import get_logger

logger = get_logger("common_llm_utils")

# Shared Constants
LLM_MODEL = "llama3.1:8b"
CONVERSATION_COMPLETE_MARKER = "CONVERSATION_COMPLETE"
LIST_OF_STRINGS = "list of strings"


def get_ai_response(messages):
    """Interface to the chat model"""
    response = ollama.chat(model=LLM_MODEL, messages=messages)
    return response["message"]["content"]


def extract_json(assistant_msg):
    """Extract JSON if the conversation is finished"""
    logger.debug(f"extract_json called with: {assistant_msg}")
    if CONVERSATION_COMPLETE_MARKER in assistant_msg:
        try:
            parts = assistant_msg.split(CONVERSATION_COMPLETE_MARKER, 1)
            text_part = parts[0].strip()
            # Clean up to capture pure JSON
            raw_part = parts[1].strip()
            start = raw_part.find("{")
            end = raw_part.rfind("}")
            if start != -1 and end != -1 and end > start:
                json_part = raw_part[start : end + 1]
                return text_part, json.loads(json_part)
            return assistant_msg, None
        except Exception as e:
            logger.error(f"Failed to extract JSON from assistant message: {e}", exc_info=True)
            return assistant_msg, None
    return assistant_msg, None
