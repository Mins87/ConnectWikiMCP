# Setup & User Guide (ConnectWiki v0.9.3-Alpha)

This guide covers the installation, configuration, and utilization of the ConnectWiki system.

## 🏗 Knowledge Architecture

ConnectWiki follows a 3-tier workflow to ensure data integrity and AI readability:

1.  **`raw/` (Original Source)**: Stores unprocessed notes, PDFs, Word documents, etc.
2.  **`transformed/` (Digital Twin)**: Automatically converts source files into AI-readable Markdown via the [[SyncDocuments]] tool.
3.  **`pages/` (Knowledge Graph)**: Stores finally organized knowledge nodes, serving as the interconnected "Source of Truth".

---

## 🚀 Installation

### Method A: Docker Deployment (Recommended)
This is the most stable and isolated way to run the system.

1.  Verify the wiki path in `docker-compose.yml`:
    ```yaml
    volumes:
      - ./wiki:/app/wiki
    ```
2.  Start the server: `docker-compose up -d`

### Method B: Local Python Setup
1.  **Requirements**: Python 3.10+, Git.
2.  **Install dependencies**: `pip install -r requirements.txt`
3.  **Start server**: `PYTHONPATH=src python src/server.py`

---

## ⚙️ Configuration

The system is controlled via Docker environment variables (`.env`) and an internal configuration file (`config.json`).

### 1. Environment Variables (`.env`)
Modify the `.env` file in the project root to define core execution environments.
- `WIKI_ROOT_PATH`: The local path where wiki data is stored.
- `MCP_TRANSPORT`: Specifies the transport method (`stdio` or `sse`).
- `MCP_PORT`: The service port when SSE mode is active (default is `8000`).

---

## 🌐 Cloud MCP Registration (SSE Mode)

To register this MCP with Perplexity or other cloud AI agents, **SSE mode** is required.

1.  Set `MCP_TRANSPORT=sse` (or `hybrid`) in the `.env` file.
2.  Expose local port 8000 to an external HTTPS address (e.g., via `ngrok http 8000`).
3.  Enter the generated HTTPS URL (e.g., `https://abcd.ngrok-free.app/sse`) in the cloud service registration page.

---

## 🛠 Semantic Toolbox

| Action | Tool | Purpose |
| :--- | :--- | :--- |
| **Summarize/Synthesize** | `SynthesizeKnowledge` | Synthesizes multiple notes into a single finished wiki page. |
| **Search** | `SearchAcrossWiki` | Searches for keywords across the entire knowledge graph. |
| **Explore Connectivity** | `ExploreConnections` | Explores backlinks and related [[WikiLinks]] between pages. |
| **Quick Note** | `CaptureQuickNote` | Immediately saves ideas to the `raw/` folder. |
| **Reset System** | `ResetSystemDocs` | Forcefully resets system documents in the wiki to repo versions. |

---

## 🤖 System Intelligence
Rules for AI behavior and learned patterns can be found in the [[System/Intelligence]] manual.
