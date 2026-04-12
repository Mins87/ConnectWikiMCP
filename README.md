# 🚀 ConnectWikiMCP v1.0.1 (Kernel Edition)

[English](#-english) | [한국어](#-한국어)

---

## 🇺🇸 English

### Definition
ConnectWikiMCP is an autonomous knowledge management server that transforms fragmented information into a structured **Knowledge Graph**. Based on Andrej Karpathy's "LLM Wiki" philosophy and built on the **Model Context Protocol (MCP)**, it enables AI agents to independently build, connect, and evolve a second brain.

This **v1.0.1 (Kernel Edition)** is a major stability release, replacing the previous monolithic design with a clean Pydantic-based configuration kernel and a robust Streamable HTTP transport layer.

### ✨ Features
- **Streamable HTTP Transport**: Full support for the latest MCP Streamable HTTP standard (`/mcp` endpoint), replacing the legacy SSE transport. Also supports STDIO for direct local integration.
- **Pydantic Config Kernel**: All configuration is managed through a type-safe `Config` model, with environment variables always taking precedence over `config.json` (critical for Docker deployments).
- **Cross-Platform Path Normalization**: Automatically detects and discards Windows-style paths (`D:\...`) when running in a Linux/Docker environment, preventing cross-platform configuration corruption.
- **Hierarchical Knowledge Structure**: Manages large-scale knowledge using a `Category/Sub-Category/Page` system.
- **Automatic Document Sync**: Converts source files (PDF, Word, etc.) into AI-optimized Markdown.
- **Background AI Enrichment**: Automatically adds tags and `[[WikiLinks]]` to new pages using a local LLM without blocking tool execution.
- **Self-Evolving Intelligence**: Analyzes usage patterns and logs to autonomously update AI behavior guidelines.
- **Safe Bootstrap & Reset**: Ensures official docs are present in the wiki; the `ResetSystemDocs` tool provides force-sync capability.
- **Robust I/O Management**: BOM-resilient stdin, stdout stream protection, and graceful shutdown handlers prevent MCP JSON-RPC stream corruption.

### 📁 Documentation
- **[System Intelligence Manual](docs/system/Intelligence.md)**: Rules for AI autonomous enrichment and maintenance.
- **[Setup & User Guide](docs/system/UserGuide.md)**: Installation, configuration, and tool usage.

### 🛠 Available MCP Tools

| Tool | Description |
|---|---|
| `ListAllKnowledge` | Returns a full list of all wiki pages |
| `FetchWikiPage` | Reads a specific page by name |
| `SaveWikiContent` | Writes or updates a page |
| `SearchAcrossWiki` | Full-text search across all pages |
| `ExploreConnections` | Finds all pages linking to a given page |
| `AnalyzeKnowledgeGraph` | Returns graph data (nodes & edges) |
| `CaptureQuickNote` | Ingests a raw note for later synthesis |
| `SyncDocuments` | Converts pending raw files to wiki pages |
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
WIKI_ROOT_PATH=/path/to/your/wiki   # host path to mount as wiki volume
MCP_TRANSPORT=http                   # 'http' for Streamable HTTP, 'stdio' for local
MCP_PORT=15252
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

이번 **v1.0.1 (Kernel Edition)**은 주요 안정화 릴리즈로, 기존의 단일 구조 설계를 Pydantic 기반의 깔끔한 설정 커널과 견고한 Streamable HTTP 전송 계층으로 대체한 버전입니다.

### ✨ 특징
- **Streamable HTTP 전송 방식**: 최신 MCP Streamable HTTP 표준(`/mcp` 엔드포인트)을 완전 지원합니다. 로컬 직접 연동을 위한 STDIO도 계속 지원합니다.
- **Pydantic 설정 커널**: 모든 설정이 타입 안전한 `Config` 모델로 관리되며, 도커 환경에서 환경 변수가 `config.json` 파일 설정보다 항상 우선합니다.
- **크로스 플랫폼 경로 정규화**: 리눅스/도커 환경에서 윈도우 스타일 경로(`D:\...`)를 자동 감지하고 무시하여, 호스트-컨테이너 간 설정 충돌을 원천 차단합니다.
- **계층형 지식 구조**: `분류/중분류/페이지` 체계를 통해 대규모 지식도 체계적으로 관리합니다.
- **자동 문서 동기화**: PDF, Word 등 다양한 원본 문서를 AI가 최적화된 Markdown으로 자동 변환합니다.
- **백그라운드 AI 지능 보강**: 로컬 LLM을 통해 저장되는 모든 페이지에 태그와 `[[WikiLinks]]`를 자동으로 추가합니다. 도구 실행을 블로킹하지 않습니다.
- **자가 진화 지능**: 사용 패턴과 로그를 분석하여 AI 행동 지침을 스스로 업데이트합니다.
- **안전 부트스트랩 및 초기화**: 가이드 문서를 위키에 자동 배치하고, `ResetSystemDocs`로 언제든 강제 초기화가 가능합니다.
- **강력한 I/O 보호**: BOM 처리, Stdout 스트림 보호, 안전한 종료 핸들러를 통해 MCP JSON-RPC 스트림 오염을 방지합니다.

### 📁 핵심 문서
- **[System Intelligence Manual](docs/system/Intelligence.md)**: AI 자율 보강 및 유지보수 규칙.
- **[Setup & User Guide](docs/system/UserGuide.md)**: 설치, 설정 및 도구 활용 가이드.

### 🛠 사용 가능한 MCP 도구

| 도구 | 설명 |
|---|---|
| `ListAllKnowledge` | 전체 위키 페이지 목록 반환 |
| `FetchWikiPage` | 특정 페이지 읽기 |
| `SaveWikiContent` | 페이지 작성 또는 수정 |
| `SearchAcrossWiki` | 전체 페이지 전문 검색 |
| `ExploreConnections` | 특정 페이지로 연결되는 모든 페이지 탐색 |
| `AnalyzeKnowledgeGraph` | 그래프 데이터(노드 및 엣지) 반환 |
| `CaptureQuickNote` | 나중에 합성할 원본 메모 입력 |
| `SyncDocuments` | 대기 중인 원본 파일을 위키 페이지로 변환 |
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
WIKI_ROOT_PATH=/path/to/your/wiki   # 위키 볼륨으로 마운트할 호스트 경로
MCP_TRANSPORT=http                   # 'http': Streamable HTTP, 'stdio': 직접 연동
MCP_PORT=15252
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
