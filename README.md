# 🚀 ConnectWikiMCP v1.1.0 (Semantic Edition)

> **Building an Autonomous Second Brain with Andrej Karpathy's "LLM Wiki" Philosophy.**

ConnectWikiMCP is a professional knowledge management server that transforms fragmented information into a structured, interconnected **Knowledge Graph**. Designed for seamless AI interaction, it prioritizes natural language understanding over complex commands.

---

## 🏗 Knowledge Architecture
Your Wiki follows a strategic three-tier workflow:
1.  **`raw/` (Original Source)**: Unprocessed notes and documents (PDF, Word, etc.).
2.  **`transformed/` (Digital Twin)**: AI-readable Markdown versions of your raw documents.
3.  **`pages/` (Knowledge Graph)**: The finalized, cross-linked Source of Truth.

---

## 🧠 Semantic AI Intelligence

### 🗣️ Natural Intent Matching
You don't need to learn a manual. Simply tell your AI agent (Claude, Gemini) what you want in plain Korean or English:
- *"이 프로젝트 기획안 정리해줘"*
- *"이 파일이랑 연결된 지식이 뭐가 있지?"*
- *"오늘 메모한 내용들 요약해서 위키에 넣어줘"*
AI will automatically map your intent to the correct underlying tools.

### 🕸️ Knowledge Connectivity
The system automatically tracks **WikiLinks** (`[[PageName]]`) and **Hashtags** (`#tag`), building a vivid graph of how your ideas relate to each other.

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
| **"지식 읽어줘"** | `FetchWikiPage` | Retrieves a finalized Wiki entry. |
| **"지식 저장해"** | `SaveWikiContent` | Updates your knowledge graph. |
| **"전체 목록"** | `ListAllKnowledge` | Catalogs all available knowledge nodes. |
| **"지식 검색"** | `SearchAcrossWiki` | Full-text search across your second brain. |
| **"연결고리 탐색"** | `ExploreConnections` | Discovers backlinks and references. |
| **"지식망 분석"** | `AnalyzeKnowledgeGraph`| Analyzes total connectivity (Nodes/Edges). |
| **"메모 기록"** | `CaptureQuickNote` | Rapidly captures raw thoughts. |
| **"원본 소스 보기"** | `AccessOriginalSource` | Reads raw notes or documents. |
| **"문서 동기화"** | `SyncDocuments` | Processes new files into Markdown. |
| **"지식 합성/요약"** | `SynthesizeKnowledge` | LLM-powered compilation of raw data. |
| **"키워드 정리"** | `OrganizeByTag` | Groups information by hashtag. |

---

## 🎭 Intelligent AI Workflows (Prompts)
Available in your MCP client's **Prompts** menu:

- **`AutomatedCompilation`**: Launches an autonomous agent to build a Wiki page from a keyword.
- **`KnowledgeAudit`**: Asks the AI to heal the graph by finding gaps and suggesting new links.

---

## 🚢 Docker Support
```bash
docker-compose run connect-wiki-mcp
```

---

> **ConnectWikiMCP** - *Empowering AI to build better knowledge.*
