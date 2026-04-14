# 🚀 ConnectWikiMCP v2.0 (Intelligence Edition)

[English](#-english) | [한국어](#-한국어)

---

## 🇺🇸 English

### Definition
ConnectWikiMCP is a high-efficiency **AI-optimized Long-term Memory Engine**. Inspired by Andrej Karpathy's "LLM Wiki" philosophy, it replaces fragmented RAG tools with a unified **"Compile-First, Navigate-Second"** architecture. It transforms raw information into a structured, interlinked, and hierarchical wiki that AI agents can navigate as easily as a human researcher.

### ✨ v2.0 Core Features
- **Unified Ingestion (Write)**: A single entry point for all data. Input a URL, a YouTube link, or raw text — the system automatically captures it into a non-destructive `raw/` staging area.
- **Hierarchical Compilation (CompileEngine)**: An autonomous background pipeline that transforms raw sources into structured wiki pages. It preserves 100% of the original detail while optimizing for navigation (not just lossy summarization).
- **Global Knowledge Index (Read)**: AI agents start at `_index` to see a full hierarchical map of knowledge, allowing for precise navigation via `[[WikiLinks]]` instead of costly repetitive semantic searches.
- **Autonomous Scheduler**: Periodically scans `raw/files`, `raw/memos`, and `raw/conversations` to trigger the compilation pipeline automatically.
- **Premium Graph Visualizer (SSR)**: Real-time interactive knowledge map via `/visualizer`. Visually track how your "second brain" grows and connects.

### 🛠 Available MCP Tools (The 4 Pillars)

| Tool | Description |
|---|---|
| `Write(input, name?)` | Unified ingestion: Text or URL → Staged for compilation |
| `Read(name)` | Knowledge access: `_index` for the map, `_list` for all pages, or specific page name |
| `SystemStatus()` | Health dashboard: View stats, queue size, and **Visualizer Link** |
| `ConfigureSettings(...)` | Runtime config: Update LLM endpoints, ports, and paths |

### 📁 Directory Structure
- `wiki/raw/`: Immutable source storage (files, memos, conversations).
- `wiki/pages/`: Compiled knowledge base (standardized, linked markdown).
- `wiki/pages/index.md`: The master map of all knowledge.

### Installation & Registration
Use the **Streamable HTTP** transport (Port: 15252) for the most stable experience.

---

## 🇰🇷 한국어

### 정의
ConnectWikiMCP는 고효율 **AI 전용 장기기억 엔진**입니다. Andrej Karpathy의 "LLM Wiki" 철학을 계승하여, 기존의 파편화된 RAG 도구들을 통합된 **"선-컴파일, 후-탐색(Compile-First, Navigate-Second)"** 아키텍처로 대체했습니다. 원본 정보를 구조화되고 상호 연결된 위키로 자동 가공하여, AI 에이전트가 숙련된 연구원처럼 지식을 탐색할 수 있게 합니다.

### ✨ v2.0 핵심 특징
- **통합 주입 (Write)**: 모든 데이터의 단일 진입점입니다. URL, 유튜브 링크, 또는 일반 텍스트를 입력하면 시스템이 `raw/` 스테이징 영역에 안전하게 보관합니다.
- **계층형 컴파일 (CompileEngine)**: 원본 소스를 구조화된 위키 페이지로 변환하는 자율 파이프라인입니다. 정보 손실을 최소화하면서 탐색에 최적화된 구조(헤딩 분할, 목차 생성)로 정돈합니다.
- **지식 지도 (Read)**: AI 에이전트는 `_index`를 통해 전체 지식의 계층 지도를 먼저 확인합니다. 반복적인 시맨틱 검색 대신 `[[내부링크]]`를 통한 정밀한 지식 탐색이 가능합니다.
- **자율 스케줄러**: `raw/files`, `raw/memos`, `raw/conversations` 폴더를 주기적으로 감시하여 새로운 정보를 자동으로 위키에 반영합니다.
- **프리미엄 그래프 시각화 (SSR)**: `/visualizer`를 통해 "초기억"이 어떻게 성장하고 연결되는지 실시간 인터랙티브 맵으로 확인할 수 있습니다.

### 🛠 사용 가능한 MCP 도구 (4대 핵심 도구)

| 도구 | 설명 |
|---|---|
| `Write(input, name?)` | 통합 주입: 텍스트 또는 URL 입력 → 자율 가공 대기열 등록 |
| `Read(name)` | 지식 접근: `_index`(지도), `_list`(목록), 또는 특정 페이지 읽기 |
| `SystemStatus()` | 상태 대시보드: 시스템 통계, 처리 대기열, **비주얼라이저 링크** 확인 |
| `ConfigureSettings(...)` | 실시간 설정: LLM 엔드포인트, 포트, 경로 등 업데이트 |

### 📁 디렉토리 구조
- `wiki/raw/`: 불변 원본 저장소 (files, memos, conversations).
- `wiki/pages/`: 컴파일된 지식 베이스 (표준화 및 링크가 완료된 마크다운).
- `wiki/pages/index.md`: 전체 지식의 실시간 마스터 인덱스.

### 설치 및 등록
가장 안정적인 연결을 위해 **Streamable HTTP** 방식(Port: 15252)을 권장합니다.

---

## 📄 License
MIT License

> **ConnectWikiMCP v2.0** - *The high-fidelity memory engine for the agentic era.*
