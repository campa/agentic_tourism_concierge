"""
Product Screening Pipeline

Orchestrates the hard and soft screeners to produce final ranked products.
"""

from dataclasses import dataclass

from common.config import TOP_RESULTS_COUNT
from common.logging_config import get_logger
from product_hard_screener.core import HardScreeningResult, screen_hard
from product_soft_screener.core import SoftScreeningResult, screen_soft
from product_synthesizer.types import SynthesizerOutput

logger = get_logger("products_screener_pipeline")


@dataclass
class PipelineResult:
    """Result from the screening pipeline."""

    products: list[dict]
    hard_result: HardScreeningResult
    soft_result: SoftScreeningResult


def screen_products(
    profile: SynthesizerOutput,
    top_n: int = TOP_RESULTS_COUNT,
) -> PipelineResult:
    """
    Run the full screening pipeline: hard filtering -> soft ranking.

    Args:
        profile: SynthesizerOutput with hard_constraints and soft_preferences
        top_n: Number of top results to return

    Returns:
        PipelineResult with ranked products and stage results
    """
    logger.info("Starting screening pipeline")

    hard_constraints = profile.get("hard_constraints", {})
    hard_result = screen_hard(hard_constraints)

    logger.info(
        f"Hard screening: {hard_result.initial_count} -> {hard_result.after_exclusion_count} products"
    )

    soft_preferences = profile.get("soft_preferences", {})
    soft_result = screen_soft(hard_result.filtered_ids, soft_preferences, top_n)

    logger.info(f"Soft screening: {soft_result.input_count} -> {soft_result.output_count} products")

    return PipelineResult(
        products=soft_result.products,
        hard_result=hard_result,
        soft_result=soft_result,
    )
