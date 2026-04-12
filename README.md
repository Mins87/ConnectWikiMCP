# 🚀 ConnectWikiMCP v1.3.0 (Autonomous Intelligence Edition)

[English](#-english) | [한국어](#-한국어)

---

## 🇺🇸 English

### Definition
ConnectWikiMCP is an autonomous knowledge management server designed to transform fragmented information into a structured **Knowledge Graph**. Based on Andrej Karpathy's "LLM Wiki" philosophy and built on the Model Context Protocol (MCP), it enables AI agents to independently build, connect, and evolve a second brain.

### Features
- **Hybrid Transport Layer**: Supports both STDIO (local collaboration) and SSE (cloud integration) simultaneously.
- **Hierarchical Knowledge Structure**: Scales knowledge management using a `Category/Sub-Category/Page` system.
- **Automatic Document Sync**: Converts source files (PDF, Word, etc.) into AI-optimized Markdown.
- **Background AI Enrichment**: Automatically adds tags and [[WikiLinks]] to new pages using local LLM without blocking.
- **Self-Evolving Intelligence**: Automatically updates AI behavior guidelines and aggregates logs.
- **Safe Bootstrap & Reset**: Ensures official docs are present in the wiki and provides a `ResetSystemDocs` tool for force-sync.
- **Semantic Toolset**: Advanced tools for connectivity analysis and knowledge graph visualization.

### 📁 Documentation
Detailed guides on system architecture and autonomous intelligence:
- **[System Intelligence Manual](docs/system/Intelligence.md)**: Rules for AI autonomous enrichment and maintenance.
- **[Setup & User Guide](docs/system/UserGuide.md)**: Installation, configuration, and tool usage.

### Usage
Interact with your AI agent (Claude, Gemini, etc.) using natural language:
- "Organize today's meeting notes into the Project A category in the wiki."
- "What other knowledge nodes are connected to this document?"
- "Summarize all AI-related content in the wiki and generate a report."

### Installation Guide

#### Choice 1. Direct Execution (Local Python)
Best for quick development and testing.
1.  **Install dependencies**: `pip install -r requirements.txt`
2.  **Configuration**: Copy `.env.example` to `.env` and adjust settings.
3.  **Run**: `PYTHONPATH=src python src/server.py`

#### Choice 2. Docker Execution (Recommended)
Best for stable, isolated production environments.
1.  **Configuration**: Copy `.env.example` to `.env`.
2.  **Build & Run**:
    ```bash
    docker-compose up --build -d
    ```
    *Note: Always use `--build` after modifying source code.*

### MCP Registration Guide

#### 1. STDIO (For Local Agents)
Use for Claude Desktop or other local apps. Add to `mcp_config.json`:

**[Via Docker]**
```json
"ConnectWiki": {
  "command": "docker",
  "args": ["exec", "-i", "connect-wiki-mcp", "python", "src/server.py"]
}
```

#### 2. SSE (For Cloud Services)
Use for Perplexity or other cloud platforms.
1.  Check `.env` for `MCP_TRANSPORT=hybrid` or `sse`.
2.  Expose port `8000` (e.g., via `ngrok http 8000`).
3.  Register the provided HTTPS URL in the cloud service (e.g., `https://abcd.ngrok-free.app/sse`).

---

## 🇰🇷 한국어

### 정의
ConnectWikiMCP는 파편화된 정보를 체계적인 **지식 그래프(Knowledge Graph)**로 변환하고 관리하는 자율형 지식 관리 서버입니다. 안드레 카파시(Andrej Karpathy)의 "LLM Wiki" 철학을 MCP(Model Context Protocol) 기술과 결합하여, AI 에이전트가 스스로 지식을 구축하고 연결하며 진화시킬 수 있는 환경을 제공합니다.

### 특징
- **하이브리드 전송 계층 (Hybrid Transport)**: STDIO(로컬 협업)와 SSE(클라우드 연동)를 동시에 지원합니다.
- **계층형 지식 구조**: `분류/중분류/페이지` 체계를 통해 대규모 지식도 체계적으로 관리합니다.
- **자동 문서 동기화**: PDF, Word 등 다양한 원본 문서를 AI가 읽기 좋은 Markdown으로 자동 변환합니다.
- **백그라운드 AI 지능 보강**: 로컬 LLM을 통해 저장되는 모든 페이지에 태그와 [[WikiLinks]]를 자동으로 추가합니다.
- **자가 진화 지능**: 사용 패턴과 로그를 분석하여 AI 행동 지침을 스스로 업데이트합니다.
- **안전 부트스트랩 및 초기화**: 가이드 문서를 위키에 자동 배치하고, `ResetSystemDocs`로 상시 초기화가 가능합니다.
- **시맨틱 도구 도구**: 지식 간의 연결성 분석 및 그래프 시각화 정보를 제공합니다.

### 📁 핵심 문서
시스템 아키텍처 및 자율 지능 작동 방식에 대한 상세 가이드는 다음 경로에서 확인할 수 있습니다:
- **[System Intelligence Manual](docs/system/Intelligence.md)**: AI 자율 보강 및 유지보수 규칙.
- **[Setup & User Guide](docs/system/UserGuide.md)**: 설치, 설정 및 도구 활용 가이드.

### 사용법
AI 에이전트(Claude, Gemini 등)에게 자연어로 명령하여 지식을 관리할 수 있습니다.
- "오늘 회의록을 위키의 프로젝트A 분류에 정리해줘."
- "이 문서와 연결된 다른 지식들이 뭐가 있지?"
- "위키 전체에서 AI 관련 내용을 요약해서 리포트 작성해줘."

### 설치 가이드

#### 방법 1. 직접 실행 (Local Python)
빠른 개발과 테스트가 필요할 때 권장합니다.
1.  **의존성 설치**: `pip install -r requirements.txt`
2.  **환경 설정**: `.env.example`을 `.env`로 복사하고 설정값을 수정합니다.
3.  **실행**: `PYTHONPATH=src python src/server.py`

#### 방법 2. 도커 실행 (Docker - 권장)
격리된 환경에서 안정적으로 운영하고 싶을 때 권장합니다.
1.  **환경 설정**: `.env.example`을 `.env`로 복사합니다.
2.  **컨테이너 빌드 및 실행**:
    ```bash
    docker-compose up --build -d
    ```

### MCP 등록 가이드

#### 1. STDIO 방식 (로컬 에이전트용)
Claude Desktop 등 로컬 앱에서 연동할 때 사용합니다.

**[도커 실행 시]**
```json
"ConnectWiki": {
  "command": "docker",
  "args": ["exec", "-i", "connect-wiki-mcp", "python", "src/server.py"]
}
```

#### 2. SSE 방식 (클라우드 서비스용)
Perplexity 등 클라우드 서비스에 서버를 등록할 때 사용합니다.
1.  **.env 설정**: `MCP_TRANSPORT=hybrid` 또는 `sse`로 설정합니다.
2.  **포트 개방**: `8000` 포트가 열려 있어야 합니다.
3.  **외부 노출**: `ngrok http 8000` 등을 통해 외부 주소를 생성합니다.
4.  **등록**: 클라우드 서비스에 HTTPS 주소(예: `https://abcd.ngrok-free.app/sse`)를 등록합니다.

---

## 📄 License
MIT License

> **ConnectWikiMCP** - *AI and Humans building a better knowledge garden together.*
