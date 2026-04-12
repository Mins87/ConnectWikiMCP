# 🚀 ConnectWikiMCP v1.2.0 (Intelligence Edition)

> **Building an Autonomous Second Brain with Andrej Karpathy's "LLM Wiki" Philosophy.**

ConnectWikiMCP is an advanced knowledge management server that transforms fragmented information into a structured, interconnected **Knowledge Graph**. It features a self-improving intelligence engine that learns from your usage patterns to become your perfect digital assistant.

---

## 🏗 Knowledge Architecture
Your Wiki follows a strategic three-tier workflow:
1.  **`raw/` (Original Source)**: Unprocessed notes and documents (PDF, Word, etc.).
2.  **`transformed/` (Digital Twin)**: AI-readable Markdown versions of your raw documents.
3.  **`pages/` (Knowledge Graph)**: Finalized, cross-linked Source of Truth.

---

## 🧠 Self-Improving Intelligence (New in v1.2.0)

### ✍️ Shared Intelligence Manual
The system maintains a specialized wiki page: `System/Intelligence.md`. This is the AI's "Operating Manual." 
- **Enforced English**: Per user request, the system is now configured to work exclusively in **English**.
- **Self-Evolution**: Use the `EvolveSystemIntelligence` prompt to have the AI audit its logs and update its own behavior rules.

### 🗣️ Natural Intent Matching
Simply talk to your AI agent (Claude, Gemini) in plain English:
- *"Organize this project draft into the wiki"*
- *"What other knowledge is connected to this file?"*
- *"Summarize today's notes and save them"*

---

## 🚀 Local Setup Guide

Follow these steps to set up ConnectWikiMCP on your local development machine.

### 1. Prerequisites
- **Python 3.10+**: Ensure you have a modern Python environment.
- **Git**: For cloning the repository.
- **MarkItDown Dependencies**: Some features (like OCR or specific document types) may require system-level libraries like `libmagic`.

### 2. Installation
```bash
# Clone the repository
git clone https://github.com/Mins87/ConnectWikiMCP.git
cd ConnectWikiMCP

# Create a virtual environment (Recommended)
python -m venv venv

# Activate the virtual environment
# Windows:
.\venv\Scripts\activate
# Linux/macOS:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

## ⚙️ Configuration Reference

On its first run, ConnectWikiMCP creates a `config.json` inside your designated `wiki/` folder. You can customize the server behavior by editing this file or by setting environment variables.

### Configuration Fields

| Key | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `wiki_root_path` | `String` | `./wiki` | The absolute path where the system stores all data (pages, raw notes, logs). |
| `local_llm_type` | `String` | `"ollama"` | Choice of Backend: `"ollama"`, `"llamacpp, or `"external"`. |
| `local_llm_api_url` | `String` | `...:11434` | The endpoint for your LLM inference engine. |
| `local_llm_model` | `String` | `gemma4-E4B-it` | The specific model name to be used for synthesis. |
| `local_llm_api_key` | `String` | `null` | Required only if `local_llm_type` is set to `"external"`. |

### LLM Backend Setup

#### 🐑 Ollama (Default)
Fastest way for local setup. Ensure Ollama is running and the model is pulled (`ollama pull llama3.2`).
- **URL**: `http://localhost:11434`
- **Type**: `ollama`

#### 🧩 llama.cpp
Recommended for fine-tuned performance or GGUF models. Run `llama-server` with the `--api-key` if needed.
- **URL**: `http://localhost:8080/v1`
- **Type**: `llamacpp`

#### 🌐 External API (OpenAI Compatible)
Use any OpenAI-compatible API (e.g., Groq, TogetherAI, or OpenAI itself).
- **Type**: `external`
- **URL**: `https://api.openai.com/v1`
- **API Key**: Your secret key.

---

### 4. Running the Server
To start the MCP server via STDIO (the default way MCP clients like Claude connect):

```bash
# Windows
$env:PYTHONPATH="src"; python src/server.py

# Linux/macOS
PYTHONPATH=src python3 src/server.py
```

## 🔌 MCP Integration Guide

To use ConnectWikiMCP with your AI assistant (e.g., Claude Desktop, Antigravity), add the following to your `claude_desktop_config.json` or `mcp_config.json`.

### Option A: Running via Docker (Recommended for isolation)
Use this if you have the ConnectWikiMCP container running via `docker-compose`.

```json
"ConnectWiki": {
  "command": "docker",
  "args": ["exec", "-i", "connect-wiki-mcp", "python", "src/server.py"]
}
```

### Option B: Running via Local Python (Faster & simpler)
Use this if you have the dependencies installed locally in your virtual environment.

```json
"ConnectWiki": {
  "command": "python",
  "args": ["/absolute/path/to/ConnectWikiMCP/src/server.py"],
  "env": {
    "PYTHONPATH": "/absolute/path/to/ConnectWikiMCP/src"
  }
}
```

---

> [!TIP]
> **First Run**: On the first execution, the system will automatically create the `wiki/`, `wiki/raw/`, and `wiki/pages/` directories along with a default `wiki/config.json`. You can stop the server, adjust the config, and restart.

---

## 🛠 Semantic Tool Reference

| Human Intent | System Action | Purpose |
| :--- | :--- | :--- |
| **"Read knowledge"** | `FetchWikiPage` | Retrieves a finalized Wiki entry. |
| **"Save knowledge"** | `SaveWikiContent` | Updates your knowledge graph. |
| **"Knowledge List"** | `ListAllKnowledge` | Catalogs all available knowledge nodes. |
| **"Search Wiki"** | `SearchAcrossWiki` | Full-text search across your second brain. |
| **"Explore Link"** | `ExploreConnections` | Discovers backlinks and references. |
| **"Graph Analysis"** | `AnalyzeKnowledgeGraph`| Analyzes total connectivity (Nodes/Edges). |
| **"Quick Note"** | `CaptureQuickNote` | Rapidly captures raw thoughts. |
| **"Access Source"** | `AccessOriginalSource` | Reads raw notes or documents. |
| **"Sync Files"** | `SyncDocuments` | Processes new files into Markdown. |
| **"Synthesize/Summarize"**| `SynthesizeKnowledge` | AI-powered compilation of raw data. |
| **"Group by Tag"** | `OrganizeByTag` | Groups information by hashtag. |
| **"Self-Audit"** | `EvolutionAudit` | Analyzes usage logs for learning. |

---

## 🎭 Intelligent AI Workflows (Prompts)
Available in your MCP client's **Prompts** menu:

- **`AutomatedCompilation`**: Launches an autonomous agent to build a Wiki page.
- **`KnowledgeAudit`**: Suggests structural improvements for your graph.
- **`EvolveSystemIntelligence`**: Triggers the self-improvement loop based on logs.

---

## 🚢 Docker Deployment Guide

ConnectWikiMCP is designed to be fully containerized. To ensure your knowledge persists and the system can communicate with your local LLM, follow these configurations:

### 1. Persistent Storage (Volumes)
Your knowledge base must be mounted from the host to ensure it isn't lost when the container restarts.

- **Host Path**: `./wiki` (Create this directory before running)
- **Container Path**: `/app/wiki`

### 2. Configuration via Docker Compose
The recommended way to deploy is using the provided `docker-compose.yml`:

```yaml
services:
  connect-wiki-mcp:
    build: .
    container_name: connect-wiki-mcp
    stdin_open: true  # Required for MCP (STDIO)
    tty: true        # Required for MCP (STDIO)
    volumes:
      - ./wiki:/app/wiki  # Map your local wiki folder
    environment:
      - WIKI_ROOT_PATH=/app/wiki
      - LOCAL_LLM_TYPE=ollama  # ollama, llamacpp, or external
      - LOCAL_LLM_API_URL=http://host.docker.internal:11434
    extra_hosts:
      - "host.docker.internal:host-gateway" # Allow container to talk to local host
```

### 3. Execution
```bash
# Start the server
docker-compose up -d

# Check if the server is healthy
docker logs connect-wiki-mcp
```

> [!IMPORTANT]
> **Permissions**: On Linux/macOS, ensure the `./wiki` directory has write permissions (`chmod -R 777 ./wiki`) so the container can save logs and wiki pages.
> **Networking**: If using Ollama or llama.cpp on your host machine, use `http://host.docker.internal:[PORT]` to allow the Docker container to reach your machine's services.

---

## 📄 License

This project is licensed under the **MIT License**. See the [LICENSE](LICENSE) file for details.

---

> **ConnectWikiMCP** - *Empowering AI to build better knowledge.*
