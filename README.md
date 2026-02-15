# Agentic Tourism Concierge

AI-powered system that recommends tourism experiences based on user profiles. Collects personal/holiday info through conversational agents, then filters and ranks products from an OCTO-compliant catalog.

## What It Does

1. **Collects** user info via two conversational agents (personal profile + holiday logistics)
2. **Synthesizes** constraints and preferences using an LLM
3. **Filters** products through hard constraints (location, dates, accessibility, safety)
4. **Ranks** remaining products by semantic similarity to user preferences

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

## Tech Stack

- **LLM**: Ollama with Llama 3.1:8b (local, privacy-preserving)
- **Vector DB**: LanceDB with sentence-transformers embeddings
- **UI**: Chainlit for conversational interface
- **Data Format**: OCTO specification for tourism products

## Setup

```bash
# 1. Install Ollama and pull model
ollama pull llama3.1:8b

# 2. Clone and install
git clone <repo-url>
cd agentic_tourism_concierge
uv sync

# 3. Run
uv run chainlit run src/personal_information_collector/app.py
```

## Project Structure

```
src/
├── common/                     # Shared utilities (config, geocoding, LLM)
├── orchestrator/               # Pipeline coordinator
├── personal_information_collector/  # Agent 1: user profile
├── holiday_information_collector/   # Agent 2: trip logistics
├── product_synthesizer/        # LLM-based constraint extraction
├── product_ingestor/           # OCTO data → LanceDB
├── product_hard_screener/      # Filtering (SQL, proximity, exclusions)
└── product_soft_screener/      # Semantic ranking
```

## Development

```bash
uv uv sync --extra dev
uv run pytest                    # Run tests
uv run ruff check . --fix        # Lint
uv run ruff format .             # Format
```

## Why This Design

**Two-phase screening** solves the semantic mismatch problem. Pure keyword search returns "Colosseum tour" when user wants "boat tour" because both contain "tour". By separating hard constraints (must-have filters) from soft preferences (nice-to-have ranking), we ensure:

1. Safety-critical constraints (accessibility, medical) are never violated
2. User preferences influence ranking without excluding valid options
3. Location proximity is enforced before semantic matching

**Local LLM** keeps sensitive personal/medical data on-device. No cloud API calls for user information processing.
