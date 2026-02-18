# Agentic Tourism Concierge

POC for an AI-powered system that recommends tourism experiences and activities for travelers who have already booked their trip. Collects user profile and stay details through conversational agents, then filters and ranks experiences from an OCTO-compliant catalog.

Think of it like Musement, GetYourGuide, or Viator - helping travelers discover things to do during their stay (museum visits, tours, lessons, excursions, etc.).

## What It Does

1. **Collects** user info via two conversational agents (personal profile + stay details)
2. **Synthesizes** constraints and preferences using an LLM
3. **Filters** experiences through hard constraints (location, dates, accessibility, safety)
4. **Ranks** remaining experiences by semantic similarity to user preferences

## Architecture

```
┌─────────────────┐    ┌─────────────────┐
│    Personal     │    │     Holiday     │
│   Collector     │    │    Collector    │
└────────┬────────┘    └────────┬────────┘
         │                      │
         └──────────┬───────────┘
                    ▼
           ┌────────────────┐
           │   Synthesizer  │  LLM extracts constraints + preferences
           └────────┬───────┘
                    ▼
           ┌────────────────┐
           │ Hard Screener  │  SQL + Proximity + Semantic Exclusion
           └────────┬───────┘
                    ▼
           ┌────────────────┐
           │ Soft Screener  │  Vector similarity ranking
           └────────┬───────┘
                    ▼
              Top 5 Products
```

See [docs/architecture.md](docs/architecture.md) for details.

## Requirements

### Software Requirements

| Software | Minimum Version | Notes |
|----------|-----------------|-------|
| Python | 3.11+ | Required for type hints and modern features |
| Ollama | 0.16.0+ | Local LLM runtime |
| uv | 0.4+ | Python package manager (recommended) |

### Hardware Requirements

The application runs local LLMs, so hardware requirements depend on the model size:

| Model | VRAM Required | RAM Required | Notes |
|-------|---------------|--------------|-------|
| `qwen3:8b` | ~6 GB | ~10 GB | Default model, good balance |

### Reference Configuration (Tested)

This application has been developed and tested on:

| Component | Specification |
|-----------|---------------|
| Machine | MacBook Pro M3 Max |
| CPU | Apple M3 Max (14-core) |
| RAM | 64 GB unified memory |
| OS | macOS Sonoma 15.x |
| Ollama | 0.16.1 |
| Python | 3.12 |
| Model | `qwen3:8b` |

**Performance on reference hardware:** ~15-25 tokens/sec

## Tech Stack

- **LLM**: Ollama with Qwen 3 (local, privacy-preserving)
- **Vector DB**: LanceDB with sentence-transformers embeddings
- **UI**: Chainlit for conversational interface
- **Observability**: OpenTelemetry → Prometheus → Grafana
- **Data Format**: OCTO specification for tourism products

## Setup

```bash
# 1. Install Ollama and pull model
ollama pull qwen3:8b

# 2. Clone and install
git clone <repo-url>
cd agentic_tourism_concierge
uv sync

# 3. Start Ollama (in a separate terminal)
./start-ollama.sh

# 4. Run the application
uv run chainlit run src/unified_app/app.py

# Run individual agents in isolation (for testing/debugging)
uv run chainlit run src/personal_information_collector/app.py
uv run chainlit run src/holiday_information_collector/app.py
```

## LLM Configuration

All LLM settings are centralized in `src/common/config.py`. This allows easy tuning and A/B testing.

### Basic Settings

| Parameter | Default | Description |
|-----------|---------|-------------|
| `LLM_MODEL` | `qwen3:8b` | Main model to use |
| `LLM_TEMPERATURE` | `0.3` | Lower = more deterministic, faster |
| `LLM_NUM_CTX` | `4096` | Context window size (lower reduces TTFT) |
| `LLM_REPEAT_PENALTY` | `1.0` | Qwen 3 is sensitive to this; 1.1+ slows it down |
| `LLM_TOP_P` | `0.9` | Nucleus sampling threshold |
| `LLM_TOP_K` | `40` | Limits token choices |
| `LLM_NUM_PREDICT` | `-1` | Max tokens to generate (-1 = infinite) |
| `LLM_SYSTEM_PROMPT` | `None` | Optional system prompt for all calls |

## Project Structure

```
src/
├── common/                          # Shared utilities (config, geocoding, LLM)
│   └── metrics/                     # OpenTelemetry instruments
├── orchestrator/                    # Pipeline coordinator
├── personal_information_collector/  # Agent 1: user profile
├── holiday_information_collector/   # Agent 2: trip logistics
├── product_synthesizer/             # LLM-based constraint extraction
├── product_ingestor/                # OCTO data → LanceDB
├── product_hard_screener/           # Filtering (SQL, proximity, exclusions)
└── product_soft_screener/           # Semantic ranking

metrics/                             # Observability stack (Docker)
├── docker-compose.otel.yml
├── otel-collector-config.yml
└── prometheus.yml
```

## Development

```bash
uv sync --extra dev
uv run pytest                    # Run tests
uv run ruff check . --fix        # Lint
uv run ruff format .             # Format
```

## Observability

LLM performance metrics (TTFT, TPS, latency, token counts) are exported via OpenTelemetry to a local Prometheus + Grafana stack.

```bash
# Start metrics stack (requires Docker)
docker compose -f metrics/docker-compose.otel.yml up -d

# Grafana dashboard
open http://localhost:3001
# Add Prometheus data source: http://prometheus:9090
```

Available metrics:
| Metric | Type | Description |
|--------|------|-------------|
| `llm_ttft` | histogram | Time to first token (ms) |
| `llm_total_duration` | histogram | Total request-response time (ms) |
| `llm_generation_duration` | histogram | Token generation time (ms) |
| `llm_tokens_per_second` | histogram | Generation speed (TPS) |
| `llm_prompt_tokens` | counter | Total prompt tokens processed |
| `llm_completion_tokens` | counter | Total completion tokens generated |

Metrics are fire-and-forget: if the Docker stack is not running, the app works normally.

## Why This Design

**Two-phase screening** solves the semantic mismatch problem. Pure keyword search returns "Colosseum tour" when user wants "boat tour" because both contain "tour". By separating hard constraints (must-have filters) from soft preferences (nice-to-have ranking), we ensure:

1. Safety-critical constraints (accessibility, medical) are never violated
2. User preferences influence ranking without excluding valid options
3. Location proximity is enforced before semantic matching

**Local LLM** keeps sensitive personal/medical data on-device. No cloud API calls for user information processing.
