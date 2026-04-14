# 🚀 ConnectWikiMCP v2.1

[English](#-english) | [한국어](#-한국어)

---

## 🇺🇸 English

### Definition
ConnectWikiMCP is a high-efficiency **AI-optimized Long-term Memory Engine**. Re-engineered in v2.1 with a **3-Layer Intelligent Pipeline**, it transforms raw information into a structured, interlinked, and hierarchical knowledge base. It replaces fragile RAG with a "Compile-First" architecture, allowing AI agents to navigate your second brain with perfect context.

### ✨ v2.1 Core Features
- **3-Layer Intelligent Pipeline**: Specialized managers handle the full lifecycle:
    - **Stage 1 (Raw)**: Scouts for new data in files, memos, and conversations.
    - **Stage 2 (Transform)**: High-fidelity Markdown extraction via MarkItDown + Local LLM.
    - **Stage 3 (Hierarchy)**: Semantic organization and WikiLink synthesis.
- **Hash-Based Change Detection**: Uses **SHA-256 fingerprints** to track content changes. Rebuilds only happen when content actually changes, saving 90% of LLM processing costs.
- **Antigravity Watcher**: Automatically ingests your AI agent's thinking logs and artifacts into the wiki, creating a self-documenting research environment.
- **Managed Orchestration**: A central `MaintenanceManager` coordinates all background tasks, knowledge indexing, and graph generation.
- **Dynamic Visualizer**: Real-time interactive knowledge map via `/visualizer` with 3rd-layer node grouping.

### 🛠 Available MCP Tools
| Tool | Description |
|---|---|
| `Write(input, name?)` | Unified ingestion: Text or URL → 3-Layer dispatch |
| `Read(name)` | Knowledge access: Semantic maps (`_index`), lists, or specific pages |
| `SystemStatus()` | Health dashboard: Stats, **Hash-detection reasons**, and **Visualizer Link** |
| `ConfigureSettings(...)` | Runtime config: Update LLM endpoints, ports, and paths |

### 📁 Directory Structure
- `wiki/raw/`: Immutable source storage.
- `wiki/transformed/`: Cleaned, high-fidelity markdown workpieces.
- `wiki/pages/`: Compiled hierarchical wiki pages.
- `wiki/logs/`: Persistent state (hashes, intent history).

---

## 🇰🇷 한국어

### 정의
ConnectWikiMCP는 고효율 **AI 전용 장기기억 엔진**입니다. v2.1에서 새롭게 도입된 **'3계층 지능형 파이프라인'**을 통해 원본 정보를 구조화되고 상호 연결된 지식 베이스로 자동 전환합니다. 파편화된 RAG 대신 "선-컴파일" 아키텍처를 채택하여, AI 에이전트가 완벽한 문맥을 바탕으로 지식의 바다를 탐험할 수 있게 합니다.

### ✨ v2.1 핵심 특징
- **3계층 지능형 파이프라인**: 각 단계별 전문 매니저가 지식의 생애주기를 관리합니다:
    - **1단계 (Raw)**: 파일, 메모, 대화 기록 등 새로운 소스를 실시간 감시합니다.
    - **2단계 (Transform)**: MarkItDown과 로컬 LLM을 통한 고정밀 마크다운 추출을 수행합니다.
    - **3단계 (Hierarchy)**: 시맨틱 구조화 및 위키 링크 합성을 통해 최종 페이지를 생성합니다.
- **해시 기반 체인지 디텍션**: **SHA-256 지문**을 사용하여 내용 변화를 추적합니다. 오직 내용이 바뀐 파일만 처리하여 LLM 연산 비용을 90% 이상 절감합니다.
- **Antigravity Watcher**: AI 에이전트의 사고 로그와 결과물(Artifacts)을 자동으로 수집하여 스스로 기록하는 연구 환경을 구축합니다.
- **자율 오케스트레이션**: 중앙역할의 `MaintenanceManager`가 모든 백그라운드 태스크, 지식 인덱싱, 그래프 생성을 지능적으로 조율합니다.
- **다이내믹 비주얼라이저**: `/visualizer`를 통해 계층 구조가 반영된 인터랙티브한 지식 그래프를 실시간으로 확인합니다.

### 🛠 사용 가능한 MCP 도구
| 도구 | 설명 |
|---|---|
| `Write(input, name?)` | 통합 주입: 텍스트 또는 URL → 3계층 파이프라인 즉시 인관 |
| `Read(name)` | 지식 접근: 지식 지도(`_index`), 전체 목록, 또는 특정 페이지 읽기 |
| `SystemStatus()` | 상태 대시보드: 통계, **해시 감지 사유**, **비주얼라이저 링크** 확인 |
| `ConfigureSettings(...)` | 실시간 설정: LLM 엔드포인트, 포트, 경로 등 자유로운 변경 |

### 📁 디렉토리 구조
- `wiki/raw/`: 불변 원본 저장소.
- `wiki/transformed/`: 정제된 고정밀 마크다운 작업물 저장소.
- `wiki/pages/`: 최종 컴파일된 계층형 위키 페이지.
- `wiki/logs/`: 영구 상태 저장소 (해시 값, 인관 이력).

---

## 📄 License
MIT License

> **ConnectWikiMCP v2.1** - *The orchestrated memory engine for the agentic era.*
