"""
OpenTelemetry metrics for LLM observability.

Exports LLM performance metrics (TTFT, TPS, latency, token counts)
via OTLP to an OpenTelemetry Collector.

Metrics are fire-and-forget: if the collector is down, the app continues normally.
"""

import os

from opentelemetry import metrics
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.resources import Resource

from common.logging_config import get_logger

logger = get_logger("common_metrics")

# OTEL Collector endpoint (default: localhost:4317 for gRPC)
OTEL_ENDPOINT = os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4317")

# Setup OTEL metrics
_resource = Resource.create({"service.name": "agentic-tourism-concierge"})

try:
    _exporter = OTLPMetricExporter(endpoint=OTEL_ENDPOINT, insecure=True)
    _reader = PeriodicExportingMetricReader(_exporter, export_interval_millis=5000)
    _provider = MeterProvider(resource=_resource, metric_readers=[_reader])
    metrics.set_meter_provider(_provider)
    logger.info(f"OpenTelemetry metrics enabled, exporting to {OTEL_ENDPOINT}")
except Exception as e:
    logger.warning(f"OpenTelemetry setup failed (metrics disabled): {e}")
    _provider = None

# Create meter and instruments
_meter = metrics.get_meter("llm", version="1.0.0")

llm_ttft = _meter.create_histogram(
    name="llm.ttft",
    description="Time to first token (ms)",
    unit="ms",
)

llm_total_duration = _meter.create_histogram(
    name="llm.total_duration",
    description="Total request-response duration (ms)",
    unit="ms",
)

llm_generation_duration = _meter.create_histogram(
    name="llm.generation_duration",
    description="Token generation duration (ms)",
    unit="ms",
)

llm_tps = _meter.create_histogram(
    name="llm.tokens_per_second",
    description="Tokens per second during generation",
    unit="tokens/s",
)

llm_prompt_tokens = _meter.create_counter(
    name="llm.prompt_tokens",
    description="Total prompt tokens processed",
    unit="tokens",
)

llm_completion_tokens = _meter.create_counter(
    name="llm.completion_tokens",
    description="Total completion tokens generated",
    unit="tokens",
)
