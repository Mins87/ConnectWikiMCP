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

## 🚀 Setup Guide

```bash
# 1. Clone & Enter
git clone https://github.com/Mins87/ConnectWikiMCP.git
cd ConnectWikiMCP

# 2. Setup (Python 3.10+)
pip install -r requirements.txt

# 3. Execution (Windows PowerShell)
$env:PYTHONPATH="src"; python src/server.py
```

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

## 🚢 Docker Support
```bash
docker-compose run connect-wiki-mcp
```

---

> **ConnectWikiMCP** - *Empowering AI to build better knowledge.*
