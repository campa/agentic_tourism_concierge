# 🛎️ Agentic Tourism Concierge

A Full-Stack Proof of Concept (PoC) for an AI-driven tourism experiences system. This application represents **Step 1** of an autonomous pipeline composed of 4 agents.

The **Concierge** is designed to offer a high-level hospitality experience. It manages conversations dynamically, recognizes user preferences, and ensures all data is verified before generating the final profile.

---

## 🚀 Key Features
- **Schema-Driven Dialogue:** Uses a single `COLLECTION_GUIDE` to guide both conversation and final JSON structure.
- **Human-in-the-Loop:** Includes a dedicated **Review & Correction** phase to ensure 100% accurate data.
- **Local Privacy:** Powered by `ollama` with `llama3.1:8b`, keeping sensitive data on the local machine.
- **Contextual Awareness:** Handles environmental sensitivities and neutral redirection for off-scope topics.

---

## 🏗️ Project Architecture
The project is modularized to separate AI logic from the web interface:
- `src/core.py`: **Backend Logic.** Contains the `COLLECTION_GUIDE`, system prompts, and Ollama integration.
- `src/app.py`: **Frontend UI.** Built with **Chainlit** to provide a modern, responsive chat experience.
- `.chainlit/config.toml`: **UI Configuration.** Used to enable/disable features like file uploads.

---

## 🛠️ Requirements
- [uv](https://docs.astral.sh/uv/) - Ultra-fast Python package and environment manager.
- [Ollama](https://ollama.com/) - Running with the `llama3.1:8b` model.

---

## 📦 Installation

### 1. Model Setup
Make sure Ollama is running and download the model:
```bash
ollama pull llama3.1:8b
```

### 2. Clone and Setup
```bash
git clone <your-repo-url>
cd agentic_tourism_concierge
uv sync
```

### 3. Start the Application
```bash
uv run streamlit run app.py
```

---

## 🔄 Workflow

1. **Intake:** The user interacts with the Concierge providing personal data, interests, and medical needs.

2. **Review:** The agent presents a summary; the user can confirm or request changes.

3. **Data Export:** Once confirmed, a structured JSON is generated and downloadable via the interface button.

---

## 🛠️ Development
### 🌍 Environment Management

The project uses uv for robust management:

- **Sync environment:** `uv sync`
- **Add dependencies:** `uv add <package-name>`
- **Add development tools:** `uv add --dev <package-name>`

### 🧹 Linting and Formatting

We use Ruff for quality control and formatting:

- **Check errors:** `uv run ruff check .`
- **Auto-fix:** `uv run ruff check . --fix`
- **Format:** `uv run ruff format .`

### 🔍 Type Checking

Static type analysis via Mypy:

- **Run type check:** `uv run mypy .`