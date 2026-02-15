"""
Formatting utilities for the Unified Web Layer.

Provides display formatting for progress indicators, product results,
and error messages. All functions are UI-agnostic and return plain strings.

NO Chainlit imports allowed in this file.
"""

from orchestrator.core import AgentContext

# Stage labels with emoji indicators
STAGE_LABELS = {
    "personal": "📋 Personal Info",
    "holiday": "🏖️ Holiday Details",
    "processing": "⚙️ Finding Matches",
    "results": "🎯 Recommendations",
}

# Ordered list of pipeline stages
PIPELINE_STAGES = ["personal", "holiday", "processing", "results"]


def format_progress(current_stage: str, completed_stages: list[str]) -> str:
    """
    Format a visual progress indicator for the pipeline.

    Args:
        current_stage: The current active stage
        completed_stages: List of stages that have been completed

    Returns:
        A formatted string showing pipeline progress with emoji indicators.

    Example output:
        ✅ Personal Info → ✅ Holiday Details → 🔄 Finding Matches → ⬜ Recommendations
    """
    parts = []

    for stage in PIPELINE_STAGES:
        label = STAGE_LABELS.get(stage, stage)
        if stage in completed_stages:
            parts.append(f"✅ {label}")
        elif stage == current_stage:
            parts.append(f"🔄 {label}")
        else:
            parts.append(f"⬜ {label}")

    return " → ".join(parts)


def format_results(products: list[dict], context: AgentContext) -> str:
    """
    Format the final product recommendations for display.

    Args:
        products: List of product dictionaries with title, description, location
        context: The AgentContext containing full pipeline results

    Returns:
        A formatted string presenting product recommendations.
    """
    if not products:
        return "No matching products found for your preferences."

    lines = ["## 🎯 Your Personalized Recommendations\n"]

    for i, product in enumerate(products, 1):
        title = product.get("title", product.get("internalName", "Unknown Product"))
        description = product.get("shortDescription", product.get("description", ""))
        location = product.get("location", "")

        lines.append(f"### {i}. {title}")
        if description:
            lines.append(f"{description}")
        if location:
            lines.append(f"📍 {location}")
        lines.append("")  # Empty line between products

    return "\n".join(lines)


def format_error_for_display(error: str) -> str:
    """
    Convert internal error message to user-friendly format.

    Strips technical details like file paths, stack traces, and internal
    function names to provide a clean message for end users.

    Args:
        error: The raw error message from the pipeline

    Returns:
        A sanitized, user-friendly error message.
    """
    if not error:
        return "An unexpected error occurred. Please try again."

    # Map known error patterns to friendly messages
    error_mappings = {
        "Synthesizer failed": "We had trouble processing your preferences. Please try again.",
        "Screening requires": "Something went wrong with the search. Please try again.",
        "LLM": "The AI assistant is temporarily unavailable. Please wait a moment.",
        "Cannot run pipeline": "The system isn't ready to process your request yet.",
        "timeout": "The request took too long. Please try again.",
        "connection": "We're having trouble connecting. Please check your connection and try again.",
    }

    # Check for known patterns (case-insensitive)
    error_lower = error.lower()
    for pattern, friendly in error_mappings.items():
        if pattern.lower() in error_lower:
            return friendly

    # Default fallback - don't expose raw error
    return "An unexpected error occurred. Please try again or start over."
