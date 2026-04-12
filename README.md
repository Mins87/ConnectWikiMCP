# 🚀 ConnectWikiMCP v1.1.0 (Karpathy Edition)

[English](#-english) | [한국어](#-한국어)

---

## 🇺🇸 English

### Definition
ConnectWikiMCP is an autonomous knowledge management server that transforms fragmented information into a structured **Knowledge Graph**. Based on Andrej Karpathy's "LLM Wiki" philosophy and built on the **Model Context Protocol (MCP)**, it enables AI agents to independently build, connect, and evolve a second brain.

This **v1.1.0 (Karpathy Edition)** fully realizes Andrej Karpathy's LLM Wiki vision: a self-improving, semantically searchable second brain that actively ingests knowledge from any source.

### ✨ Features
- **Streamable HTTP Transport**: Full MCP Streamable HTTP standard (`/mcp` endpoint). Also supports STDIO for direct local integration.
- **Semantic Vector Search**: Embedding-based search via Ollama (`nomic-embed-text`), with automatic keyword fallback. Pages are auto-indexed on every save.
- **URL & YouTube Capture**: `CaptureFromURL` fetches clean article text from any URL, or pulls transcripts from YouTube videos — ready for synthesis into wiki pages.
- **Page Version History**: Every `SaveWikiContent` call backs up the previous version to `wiki/history/` before overwriting. No edits are ever truly lost.
- **Auto Evolution Scheduler**: Background asyncio task runs `run_evolution_cycle()` on a configurable interval (default: 6h), analyzing intent logs and appending insights to `System/Intelligence.md` automatically.
- **Pydantic Config Kernel**: Type-safe `Config` model; environment variables always take precedence over `config.json` (critical for Docker).
- **Cross-Platform Path Normalization**: Automatically discards Windows-style paths (`D:\...`) in Linux/Docker environments.
- **Hierarchical Knowledge Structure**: `Category/Sub-Category/Page` system for large-scale knowledge management.
- **Automatic Document Sync**: Converts PDF, Word, etc. into AI-optimized Markdown via `MarkItDown`.
- **Background AI Enrichment**: Auto-adds tags and `[[WikiLinks]]` after every page save without blocking.
- **Safe Bootstrap & Reset**: `ResetSystemDocs` force-syncs official system documentation into the wiki.

### 📁 Documentation
- **[System Intelligence Manual](docs/system/Intelligence.md)**: Rules for AI autonomous enrichment and maintenance.
- **[Setup & User Guide](docs/system/UserGuide.md)**: Installation, configuration, and tool usage.

### 🛠 Available MCP Tools

| Tool | Description |
|---|---|
| `ListAllKnowledge` | Returns a full list of all wiki pages |
| `FetchWikiPage` | Reads a specific page by name |
| `SaveWikiContent` | Writes or updates a page (auto-backs up history) |
| `SearchAcrossWiki` | **Semantic** search (vector similarity → keyword fallback) |
| `RebuildSearchIndex` | Force-rebuilds the vector embedding index after bulk imports |
| `ExploreConnections` | Finds all pages linking to a given page |
| `AnalyzeKnowledgeGraph` | Returns graph data (nodes & edges) |
| `CaptureQuickNote` | Ingests a raw note for later synthesis |
| `CaptureFromURL` | Captures web page or **YouTube transcript** into raw folder |
| `SyncDocuments` | Converts pending raw files (PDF, Word, etc.) to wiki pages |
| `SynthesizeKnowledge` | Uses LLM to compile a raw note into a wiki page |
| `OrganizeByTag` | Lists raw notes by hashtag |
| `EvolutionAudit` | Returns recent intent logs for pattern analysis |
| `ConfigureSettings` | Updates server configuration at runtime |
| `ResetSystemDocs` | Force-syncs official system documentation |
| `AccessOriginalSource` | Reads a raw source file directly |

### Installation

#### Method 1. Docker (Recommended)
Best for stable, isolated production environments.

1. **Configure**: Copy `.env.example` to `.env` and set your wiki path.
2. **Build & Run**:
   ```bash
   docker-compose up --build -d
   ```

`.env` key settings:
```env
WIKI_ROOT_PATH=/path/to/your/wiki        # host path to mount as wiki volume
MCP_TRANSPORT=http                        # 'http' for Streamable HTTP, 'stdio' for local
MCP_PORT=15252

# Semantic Search (requires Ollama)
EMBEDDING_MODEL=nomic-embed-text         # run: ollama pull nomic-embed-text

# Auto-Evolution Scheduler
EVOLUTION_INTERVAL_HOURS=6               # set to 0 to disable
```

#### Method 2. Direct Execution (Local Python)
Best for quick development and testing.
1. **Install dependencies**: `pip install -r requirements.txt`
2. **Configure**: Copy `.env.example` to `.env`.
3. **Run**: `PYTHONPATH=src python src/server.py`

### MCP Registration Guide

#### Streamable HTTP (Recommended for Docker)
The modern, stable transport method. Add to your agent's `mcp_config.json`:

```json
"ConnectWiki": {
  "serverUrl": "http://localhost:15252/mcp"
}
```

> Change `15252` to match your `MCP_PORT` setting.

#### STDIO (For Direct Local Integration)
For scenarios where you run the server directly without Docker:
```json
"ConnectWiki": {
  "command": "python",
  "args": ["src/server.py"],
  "env": { "PYTHONPATH": "src", "MCP_TRANSPORT": "stdio" }
}
```

---

## 🇰🇷 한국어

### 정의
ConnectWikiMCP는 파편화된 정보를 체계적인 **지식 그래프(Knowledge Graph)**로 변환하고 관리하는 자율형 지식 관리 서버입니다.

이번 **v1.1.0 (Karpathy Edition)**은 Andrej Karpathy의 LLM Wiki 비전을 완전히 구현한 버전입니다. 의미론적 검색, URL/YouTube 수집, 페이지 버전 이력, 자동 진화 스케줄러를 갖춘 스스로 성장하는 두 번째 뇌입니다.

### ✨ 특징
- **Streamable HTTP 전송 방식**: 최신 MCP Streamable HTTP 표준(`/mcp` 엔드포인트)을 완전 지원합니다. STDIO도 지원합니다.
- **시맨틱 벡터 검색**: Ollama(`nomic-embed-text`)를 통한 임베딩 기반 검색을 지원합니다. 인덱스가 없을 경우 키워드 검색으로 자동 폴백됩니다. 페이지 저장 시마다 자동 인덱싱됩니다.
- **URL & YouTube 수집**: `CaptureFromURL`로 웹 페이지 본문 또는 유튜브 자막을 수집하여 raw 폴더에 저장합니다.
- **페이지 버전 이력**: `SaveWikiContent` 호출 시마다 기존 내용을 `wiki/history/`에 타임스탬프 파일로 자동 백업합니다.
- **자동 진화 스케줄러**: 백그라운드 asyncio 태스크가 설정 주기(기본 6시간)마다 의도 로그를 분석하고 `System/Intelligence.md`에 인사이트를 자동 추가합니다.
- **Pydantic 설정 커널**: 환경 변수가 `config.json`보다 항상 우선합니다.
- **계층형 지식 구조**: `분류/중분류/페이지` 체계로 대규모 지식을 관리합니다.
- **자동 문서 동기화**: PDF, Word 등을 MarkItDown으로 Markdown 변환합니다.
- **백그라운드 AI 지능 보강**: 저장되는 모든 페이지에 태그와 `[[WikiLinks]]`를 자동 추가합니다.
- **안전 부트스트랩 및 초기화**: `ResetSystemDocs`로 공식 시스템 문서를 언제든 강제 동기화할 수 있습니다.

### 📁 핵심 문서
- **[System Intelligence Manual](docs/system/Intelligence.md)**: AI 자율 보강 및 유지보수 규칙.
- **[Setup & User Guide](docs/system/UserGuide.md)**: 설치, 설정 및 도구 활용 가이드.

### 🛠 사용 가능한 MCP 도구

| 도구 | 설명 |
|---|---|
| `ListAllKnowledge` | 전체 위키 페이지 목록 반환 |
| `FetchWikiPage` | 특정 페이지 읽기 |
| `SaveWikiContent` | 페이지 작성 또는 수정 (이전 버전 자동 백업) |
| `SearchAcrossWiki` | **시맨틱 검색** (벡터 유사도 → 키워드 자동 폴백) |
| `RebuildSearchIndex` | 벡터 임베딩 인덱스 전체 재구축 |
| `ExploreConnections` | 특정 페이지로 연결되는 모든 페이지 탐색 |
| `AnalyzeKnowledgeGraph` | 그래프 데이터(노드 및 엣지) 반환 |
| `CaptureQuickNote` | 나중에 합성할 원본 메모 입력 |
| `CaptureFromURL` | 웹 페이지 또는 **유튜브 자막**을 raw 폴더로 수집 |
| `SyncDocuments` | 대기 중인 원본 파일(PDF, Word 등)을 위키 페이지로 변환 |
| `SynthesizeKnowledge` | LLM을 사용하여 원본 메모를 위키 페이지로 컴파일 |
| `OrganizeByTag` | 해시태그로 원본 메모 목록 조회 |
| `EvolutionAudit` | 최근 의도 로그 반환 (패턴 분석용) |
| `ConfigureSettings` | 런타임에 서버 설정 업데이트 |
| `ResetSystemDocs` | 공식 시스템 문서 강제 동기화 |
| `AccessOriginalSource` | 원본 파일 직접 읽기 |

### 설치 가이드

#### 방법 1. 도커 실행 (권장)
격리된 환경에서 안정적으로 운영할 때 권장합니다.

1. **환경 설정**: `.env.example`을 `.env`로 복사하고 설정값을 수정합니다.
2. **컨테이너 빌드 및 실행**:
   ```bash
   docker-compose up --build -d
   ```

`.env` 주요 설정:
```env
WIKI_ROOT_PATH=/path/to/your/wiki        # 위키 볼륨으로 마운트할 호스트 경로
MCP_TRANSPORT=http                        # 'http': Streamable HTTP, 'stdio': 직접 연동
MCP_PORT=15252

# 시맨틱 검색 (Ollama 필요)
EMBEDDING_MODEL=nomic-embed-text         # 실행: ollama pull nomic-embed-text

# 자동 진화 스케줄러
EVOLUTION_INTERVAL_HOURS=6               # 0으로 설정 시 비활성화
```

#### 방법 2. 직접 실행 (Local Python)
빠른 개발과 테스트에 적합합니다.
1. **의존성 설치**: `pip install -r requirements.txt`
2. **환경 설정**: `.env.example`을 `.env`로 복사합니다.
3. **실행**: `PYTHONPATH=src python src/server.py`

### MCP 등록 가이드

#### Streamable HTTP 방식 (도커 환경 권장)
최신 MCP 표준을 사용하는 가장 안정적인 연결 방식입니다. `mcp_config.json`에 추가하세요:

```json
"ConnectWiki": {
  "serverUrl": "http://localhost:15252/mcp"
}
```

> `15252`는 `.env`의 `MCP_PORT` 설정값에 맞게 변경하세요.

#### STDIO 방식 (도커 없이 직접 실행 시)
서버를 도커 없이 직접 실행하는 경우에 사용합니다:
```json
"ConnectWiki": {
  "command": "python",
  "args": ["src/server.py"],
  "env": { "PYTHONPATH": "src", "MCP_TRANSPORT": "stdio" }
}
```

---

## 📄 License
MIT License

> **ConnectWikiMCP** - *AI and Humans building a better knowledge garden together.*
