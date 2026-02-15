import json

import ollama

from common.logging_config import get_logger

logger = get_logger("common_llm_utils")

# Shared Constants
LLM_MODEL = "llama3.1:8b"


def get_json_response(messages):
    """Interface that forces the LLM to return a valid JSON object"""
    try:
        response = ollama.chat(
            model=LLM_MODEL,
            messages=messages,
            format="json",  # This is the key for Ollama to enforce JSON
        )
        content = response["message"]["content"]
        return json.loads(content)
    except Exception as e:
        logger.error(f"Failed to parse LLM JSON response: {e}")
        return None
