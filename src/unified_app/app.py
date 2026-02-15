"""
Unified Chainlit Application for Agentic Tourism Concierge.

This module provides a single Chainlit application that orchestrates
the complete pipeline: Personal Collector → Holiday Collector →
Synthesizer → Hard Screener → Soft Screener → Results.

All business logic is delegated to the orchestration adapter layer.
"""

import chainlit as cl

from common.logging_config import get_logger
from unified_app.formatting import format_progress
from unified_app.orchestration import (
    InteractiveOrchestrator,
    get_ai_response_streaming,
    get_stage_config,
    process_response,
)

logger = get_logger("unified_app")

# Constants
THINKING_MESSAGE = "🔄 Thinking..."


@cl.on_chat_start
async def start():
    """
    Initialize a new user session.

    - Creates an InteractiveOrchestrator instance
    - Sets initial stage to "personal"
    - Displays progress indicator
    - Sends first message from personal collector (with streaming)
    """
    logger.debug("Starting unified app session")

    # Initialize orchestrator and session state
    orchestrator = InteractiveOrchestrator()
    current_stage = "personal"
    completed_stages: list[str] = []

    # Get stage configuration for personal collector
    stage_config = get_stage_config(current_stage)

    # Initialize conversation history with system prompt and first message trigger
    history = [
        {"role": "system", "content": stage_config.system_prompt},
        {"role": "user", "content": stage_config.first_message},
    ]

    # Store session state early so it's available
    cl.user_session.set("orchestrator", orchestrator)
    cl.user_session.set("current_stage", current_stage)
    cl.user_session.set("completed_stages", completed_stages)
    cl.user_session.set("history", history)

    logger.debug(f"Session initialized: stage={current_stage}")

    # Display progress indicator
    progress = format_progress(current_stage, completed_stages)
    await cl.Message(content=progress).send()

    # Stream initial response from LLM
    msg = cl.Message(content="")
    await msg.send()

    full_response = ""
    try:
        for token in get_ai_response_streaming(history):
            full_response += token
            await msg.stream_token(token)
    except Exception as e:
        # Fallback: show loading indicator if streaming fails
        logger.warning(f"Streaming failed, using fallback: {e}")
        await msg.update()
        loading_msg = cl.Message(content=THINKING_MESSAGE)
        await loading_msg.send()

        from common.llm_utils import get_ai_response
        full_response = get_ai_response(history)
        await loading_msg.remove()
        msg = cl.Message(content=full_response)
        await msg.send()
        history.append({"role": "assistant", "content": full_response})
        cl.user_session.set("history", history)
        return

    # Finalize the streamed message
    await msg.update()

    # Update history with the response
    history.append({"role": "assistant", "content": full_response})
    cl.user_session.set("history", history)


@cl.on_message
async def on_message(message: cl.Message):
    """
    Handle incoming user messages.

    - Routes messages to current stage's conversation history
    - Streams LLM response tokens in real-time
    - Implements streaming fallback with loading indicator
    - Detects stage completion and triggers transitions
    """
    # Retrieve session state
    history = cl.user_session.get("history")
    current_stage = cl.user_session.get("current_stage")
    orchestrator = cl.user_session.get("orchestrator")
    completed_stages = cl.user_session.get("completed_stages")

    logger.debug(f"Received message in stage '{current_stage}': {message.content[:50]}...")

    # Add user message to history
    history.append({"role": "user", "content": message.content})

    # Create a streaming message
    msg = cl.Message(content="")
    await msg.send()

    full_response = ""
    try:
        # Stream tokens from LLM
        for token in get_ai_response_streaming(history):
            full_response += token
            await msg.stream_token(token)
    except Exception as e:
        # Fallback: show loading indicator if streaming fails
        logger.warning(f"Streaming failed, using fallback: {e}")
        await msg.update()
        loading_msg = cl.Message(content=THINKING_MESSAGE)
        await loading_msg.send()

        from common.llm_utils import get_ai_response
        full_response = get_ai_response(history)
        await loading_msg.remove()
        msg = cl.Message(content=full_response)
        await msg.send()
        history.append({"role": "assistant", "content": full_response})
        cl.user_session.set("history", history)
        # Still need to check for stage completion in fallback path
        await _handle_stage_completion(full_response, current_stage, orchestrator, completed_stages)
        return

    # Finalize the streamed message
    await msg.update()

    # Update history with the full response
    history.append({"role": "assistant", "content": full_response})
    cl.user_session.set("history", history)

    # Process response to check for stage completion and handle transitions
    await _handle_stage_completion(full_response, current_stage, orchestrator, completed_stages)


async def _handle_stage_completion(
    response: str,
    current_stage: str,
    orchestrator: InteractiveOrchestrator,
    completed_stages: list[str],
) -> None:
    """
    Handle potential stage completion and transition.

    Detects CONVERSATION_COMPLETE marker, extracts JSON data,
    calls appropriate orchestrator method, and transitions to next stage.

    Args:
        response: The full LLM response text
        current_stage: Current pipeline stage
        orchestrator: The InteractiveOrchestrator instance
        completed_stages: List of completed stages
    """
    # Process response to check for stage completion
    _display_text, json_data = process_response(response)

    logger.debug(f"Response processed: complete={json_data is not None}")

    # If no JSON extracted, conversation continues in current stage
    if json_data is None:
        return

    # Stage completed - handle transition based on current stage
    if current_stage == "personal":
        # Store personal info in orchestrator
        orchestrator.set_personal_info(json_data)
        logger.info("Personal info collected, transitioning to holiday stage")

        # Mark stage as completed
        completed_stages.append("personal")
        cl.user_session.set("completed_stages", completed_stages)

        # Transition to holiday stage
        await _transition_to_stage("holiday", completed_stages)

    elif current_stage == "holiday":
        # Store holiday info in orchestrator
        orchestrator.set_holiday_info(json_data)
        logger.info("Holiday info collected, transitioning to processing stage")

        # Mark stage as completed
        completed_stages.append("holiday")
        cl.user_session.set("completed_stages", completed_stages)

        # Transition to processing stage
        # Note: Processing stage execution will be implemented in Task 7
        new_stage = "processing"
        cl.user_session.set("current_stage", new_stage)

        # Display progress indicator
        progress = format_progress(new_stage, completed_stages)
        await cl.Message(content=progress).send()

        # Display transition message
        await cl.Message(
            content="✨ Great! I have all the information I need. Now let me find the perfect activities for you..."
        ).send()

        logger.debug(f"Transitioned to stage: {new_stage}")


async def _transition_to_stage(
    new_stage: str,
    completed_stages: list[str],
) -> None:
    """
    Transition to a new conversation stage.

    Resets conversation history, updates session state,
    displays progress indicator, and sends first message.

    Args:
        new_stage: The stage to transition to
        completed_stages: List of completed stages
    """
    # Get stage configuration for new stage
    stage_config = get_stage_config(new_stage)

    # Reset conversation history for new stage
    new_history = [
        {"role": "system", "content": stage_config.system_prompt},
        {"role": "user", "content": stage_config.first_message},
    ]

    # Update session state
    cl.user_session.set("current_stage", new_stage)
    cl.user_session.set("history", new_history)

    # Display progress indicator
    progress = format_progress(new_stage, completed_stages)
    await cl.Message(content=progress).send()

    # Display transition message
    await cl.Message(
        content="✅ Personal information collected! Now let's talk about your holiday plans."
    ).send()

    # Stream initial response from LLM for new stage
    msg = cl.Message(content="")
    await msg.send()

    full_response = ""
    try:
        for token in get_ai_response_streaming(new_history):
            full_response += token
            await msg.stream_token(token)
    except Exception as e:
        # Fallback: show loading indicator if streaming fails
        logger.warning(f"Streaming failed during transition, using fallback: {e}")
        await msg.update()
        loading_msg = cl.Message(content=THINKING_MESSAGE)
        await loading_msg.send()

        from common.llm_utils import get_ai_response
        full_response = get_ai_response(new_history)
        await loading_msg.remove()
        msg = cl.Message(content=full_response)
        await msg.send()
        new_history.append({"role": "assistant", "content": full_response})
        cl.user_session.set("history", new_history)
        return

    # Finalize the streamed message
    await msg.update()

    # Update history with the response
    new_history.append({"role": "assistant", "content": full_response})
    cl.user_session.set("history", new_history)

    logger.debug(f"Transitioned to stage: {new_stage}")
