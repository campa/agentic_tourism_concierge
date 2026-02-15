"""
Agent Orchestrator

Coordinates the full agent pipeline:
1. Personal Information Collector (interactive)
2. Holiday Information Collector (interactive)
3. Synthesizer (transforms collected info into constraints/preferences)
4. Hard Screener (filters products)
5. Soft Screener (ranks products)

Uses a shared AgentContext to pass data between agents.
"""

from dataclasses import dataclass, field

from common.logging_config import get_logger
from product_hard_screener.core import HardScreeningResult
from product_soft_screener.core import SoftScreeningResult
from product_synthesizer.core import synthesize_profile
from product_synthesizer.types import SynthesizerOutput, is_synthesizer_error

logger = get_logger("orchestrator")


@dataclass
class AgentContext:
    """
    Shared context that accumulates outputs from each agent in the pipeline.

    Each agent reads what it needs and writes its output to this context.
    This makes data flow explicit and easy to test/debug.
    """

    personal_info: dict | None = None
    holiday_info: dict | None = None
    synthesized_profile: SynthesizerOutput | None = None
    hard_result: HardScreeningResult | None = None
    soft_result: SoftScreeningResult | None = None
    products: list[dict] = field(default_factory=list)
    error: str | None = None


def run_synthesizer(ctx: AgentContext) -> AgentContext:
    """
    Run the synthesizer to transform collected info into screening profile.

    Requires: ctx.personal_info and ctx.holiday_info
    Produces: ctx.synthesized_profile
    """
    if ctx.personal_info is None or ctx.holiday_info is None:
        ctx.error = "Synthesizer requires both personal_info and holiday_info"
        logger.error(ctx.error)
        return ctx

    logger.info("Running synthesizer...")

    result = synthesize_profile(ctx.personal_info, ctx.holiday_info)

    if is_synthesizer_error(result):
        ctx.error = f"Synthesizer failed: {result.get('error_message', 'Unknown error')}"
        logger.error(ctx.error)
        return ctx

    ctx.synthesized_profile = result
    logger.info("Synthesizer completed successfully")
    return ctx


def run_screening(ctx: AgentContext) -> AgentContext:
    """
    Run the hard and soft screeners.

    Requires: ctx.synthesized_profile
    Produces: ctx.hard_result, ctx.soft_result, ctx.products
    """
    from common.pipeline import screen_products

    if ctx.synthesized_profile is None:
        ctx.error = "Screening requires synthesized_profile"
        logger.error(ctx.error)
        return ctx

    logger.info("Running screening pipeline...")

    result = screen_products(ctx.synthesized_profile)

    ctx.hard_result = result.hard_result
    ctx.soft_result = result.soft_result
    ctx.products = result.products

    logger.info(f"Screening completed: {len(ctx.products)} products found")
    return ctx


def run_full_pipeline(personal_info: dict, holiday_info: dict) -> AgentContext:
    """
    Run the full pipeline from collected info to final products.

    Args:
        personal_info: Output from personal information collector
        holiday_info: Output from holiday information collector

    Returns:
        AgentContext with all results
    """
    ctx = AgentContext(personal_info=personal_info, holiday_info=holiday_info)

    ctx = run_synthesizer(ctx)
    if ctx.error:
        return ctx

    ctx = run_screening(ctx)
    return ctx


class InteractiveOrchestrator:
    """
    Orchestrator for interactive agent execution.

    Manages the conversation flow and context accumulation
    when agents are run interactively (e.g., via Chainlit).
    """

    def __init__(self):
        self.ctx = AgentContext()
        self.current_stage = "personal_info"

    def set_personal_info(self, data: dict) -> None:
        """Set personal info and advance to next stage."""
        self.ctx.personal_info = data
        self.current_stage = "holiday_info"
        logger.info("Personal info collected, advancing to holiday info")

    def set_holiday_info(self, data: dict) -> None:
        """Set holiday info and advance to next stage."""
        self.ctx.holiday_info = data
        self.current_stage = "screening"
        logger.info("Holiday info collected, ready for screening")

    def run_remaining_pipeline(self) -> AgentContext:
        """Run the non-interactive parts of the pipeline."""
        if self.current_stage != "screening":
            self.ctx.error = f"Cannot run pipeline, current stage is {self.current_stage}"
            return self.ctx

        self.ctx = run_synthesizer(self.ctx)
        if self.ctx.error:
            return self.ctx

        self.ctx = run_screening(self.ctx)
        self.current_stage = "complete"

        return self.ctx

    def get_context(self) -> AgentContext:
        """Get the current context."""
        return self.ctx

    def is_ready_for_screening(self) -> bool:
        """Check if both collectors have completed."""
        return self.ctx.personal_info is not None and self.ctx.holiday_info is not None
