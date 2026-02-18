"""LLM utilities for Ollama interactions."""

import json

import ollama

from common.config import (
    LLM_DISABLE_THINKING,
    LLM_KV_CACHE_TYPE,
    LLM_MODEL,
    LLM_NO_THINK_PROMPT,
    LLM_NUM_CTX,
    LLM_NUM_PREDICT,
    LLM_REPEAT_PENALTY,
    LLM_SYSTEM_PROMPT,
    LLM_TEMPERATURE,
    LLM_TOP_K,
    LLM_TOP_P,
)
from common.logging_config import get_logger
from common.metrics import (
    llm_completion_tokens,
    llm_generation_duration,
    llm_prompt_tokens,
    llm_total_duration,
    llm_tps,
    llm_ttft,
)

logger = get_logger("common_llm_utils")

# Log LLM configuration at startup
logger.info(f"LLM configured: model={LLM_MODEL}, temp={LLM_TEMPERATURE}, num_ctx={LLM_NUM_CTX}")

if LLM_DISABLE_THINKING:
    logger.info("Qwen 3 'Thinking' mode DISABLED (direct response mode)")
else:
    logger.info("Qwen 3 'Thinking' mode ENABLED (may add ~200-400ms latency)")

if LLM_KV_CACHE_TYPE:
    logger.info(f"KV Cache Quantization: {LLM_KV_CACHE_TYPE}")
    logger.info(
        f"NOTE: Set env var before starting Ollama: export OLLAMA_KV_CACHE_TYPE={LLM_KV_CACHE_TYPE}"
    )
else:
    logger.info("KV Cache Quantization: DISABLED (default f16)")

# Conversation markers
CONVERSATION_COMPLETE_MARKER = "CONVERSATION_COMPLETE"


def _log_metrics(response: dict, caller: str = "unknown") -> None:
    """
    Log and export LLM performance metrics from Ollama response.

    Ollama returns timing data in nanoseconds. We convert to human-readable format
    and emit OpenTelemetry metrics.
    """
    total_ns = response.get("total_duration", 0)
    prompt_eval_ns = response.get("prompt_eval_duration", 0)
    eval_ns = response.get("eval_duration", 0)
    load_ns = response.get("load_duration", 0)
    prompt_tokens = response.get("prompt_eval_count", 0)
    completion_tokens = response.get("eval_count", 0)

    total_ms = total_ns / 1_000_000
    ttft_ms = (load_ns + prompt_eval_ns) / 1_000_000
    eval_ms = eval_ns / 1_000_000
    tps = (completion_tokens / (eval_ns / 1_000_000_000)) if eval_ns > 0 else 0

    # Log to console
    logger.info(
        f"[{caller}] "
        f"total={total_ms:.0f}ms | "
        f"TTFT={ttft_ms:.0f}ms | "
        f"generation={eval_ms:.0f}ms | "
        f"tokens={prompt_tokens}→{completion_tokens} | "
        f"TPS={tps:.1f}"
    )

    # Emit OpenTelemetry metrics
    attrs = {"caller": caller, "model": LLM_MODEL}
    llm_ttft.record(ttft_ms, attributes=attrs)
    llm_total_duration.record(total_ms, attributes=attrs)
    llm_generation_duration.record(eval_ms, attributes=attrs)
    llm_tps.record(tps, attributes=attrs)
    llm_prompt_tokens.add(prompt_tokens, attributes=attrs)
    llm_completion_tokens.add(completion_tokens, attributes=attrs)


def _get_llm_options() -> dict:
    """Build the options dict for Ollama calls from config."""
    return {
        "num_ctx": LLM_NUM_CTX,
        "temperature": LLM_TEMPERATURE,
        "repeat_penalty": LLM_REPEAT_PENALTY,
        "top_p": LLM_TOP_P,
        "top_k": LLM_TOP_K,
        "num_predict": LLM_NUM_PREDICT,
    }


def _prepare_messages(messages: list[dict]) -> list[dict]:
    """Prepend system prompt if configured and not already present."""
    # Determine the effective system prompt
    effective_system_prompt = LLM_SYSTEM_PROMPT

    # If thinking is disabled and no custom system prompt, use the no-think prompt
    if LLM_DISABLE_THINKING and effective_system_prompt is None:
        effective_system_prompt = LLM_NO_THINK_PROMPT
    # If thinking is disabled AND there's a custom system prompt, prepend no-think instruction
    elif LLM_DISABLE_THINKING and effective_system_prompt is not None:
        effective_system_prompt = f"{LLM_NO_THINK_PROMPT}\n\n{effective_system_prompt}"

    if effective_system_prompt is None:
        return messages

    # Check if there's already a system message
    if messages and messages[0].get("role") == "system":
        # Prepend no-think instruction to existing system message if thinking is disabled
        if LLM_DISABLE_THINKING:
            updated_messages = messages.copy()
            updated_messages[0] = {
                "role": "system",
                "content": f"{LLM_NO_THINK_PROMPT}\n\n{messages[0]['content']}",
            }
            return updated_messages
        return messages

    return [{"role": "system", "content": effective_system_prompt}] + messages


def _log_llm_context(messages: list[dict], caller: str = "unknown") -> None:
    """
    Log the full LLM context/messages for debugging prompts.

    Uses DEBUG level - control visibility via logging configuration.

    Args:
        messages: The full message history being sent to the LLM
        caller: Name of the calling function for context
    """
    logger.debug(f"\n{'=' * 80}")
    logger.debug(f"LLM CALL from: {caller}")
    logger.debug(f"Model: {LLM_MODEL}")
    logger.debug(f"Message count: {len(messages)}")
    logger.debug(f"{'=' * 80}")

    for i, msg in enumerate(messages):
        role = msg.get("role", "unknown")
        content = msg.get("content", "")

        logger.debug(f"\n{'─' * 40}")
        logger.debug(f"[{i}] ROLE: {role.upper()}")
        logger.debug(f"{'─' * 40}")
        logger.debug(f"{content}")

    logger.debug(f"\n{'=' * 80}")
    logger.debug("END LLM CONTEXT")
    logger.debug(f"{'=' * 80}\n")


def get_ai_response(messages: list[dict]) -> str:
    """Get a plain text response from the LLM."""
    prepared_messages = _prepare_messages(messages)
    _log_llm_context(prepared_messages, caller="get_ai_response")
    response = ollama.chat(
        model=LLM_MODEL,
        messages=prepared_messages,
        options=_get_llm_options(),
    )
    response_content = response["message"]["content"]
    _log_metrics(response, caller="get_ai_response")

    logger.debug(f"\n{'─' * 40}")
    logger.debug("LLM RESPONSE:")
    logger.debug(f"{'─' * 40}")
    logger.debug(f"{response_content}")
    logger.debug(f"{'─' * 40}\n")

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
    prepared_messages = _prepare_messages(messages)
    _log_llm_context(prepared_messages, caller="get_ai_response_streaming")

    full_response = ""
    last_chunk = {}
    stream = ollama.chat(
        model=LLM_MODEL,
        messages=prepared_messages,
        stream=True,
        options=_get_llm_options(),
    )
    for chunk in stream:
        last_chunk = chunk
        if "message" in chunk and "content" in chunk["message"]:
            token = chunk["message"]["content"]
            full_response += token
            yield token

    # Last chunk contains metrics when done=True
    if last_chunk.get("done"):
        _log_metrics(last_chunk, caller="get_ai_response_streaming")

    # Log the complete response after streaming finishes
    logger.debug(f"\n{'─' * 40}")
    logger.debug("LLM STREAMING RESPONSE (complete):")
    logger.debug(f"{'─' * 40}")
    logger.debug(f"{full_response}")
    logger.debug(f"{'─' * 40}\n")


def get_json_response(messages: list[dict]) -> dict | None:
    """Get a JSON response from the LLM (forces JSON format)."""
    prepared_messages = _prepare_messages(messages)
    _log_llm_context(prepared_messages, caller="get_json_response")
    try:
        response = ollama.chat(
            model=LLM_MODEL,
            messages=prepared_messages,
            format="json",
            options=_get_llm_options(),
        )
        content = response["message"]["content"]
        _log_metrics(response, caller="get_json_response")

        logger.debug(f"\n{'─' * 40}")
        logger.debug("LLM JSON RESPONSE:")
        logger.debug(f"{'─' * 40}")
        logger.debug(f"{content}")
        logger.debug(f"{'─' * 40}\n")

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
