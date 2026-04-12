# System Intelligence Manual (Kernel Edition v1.3.0)

This manual defines the autonomous intelligence and operational logic of ConnectWikiMCP.

## 🧠 Autonomous Intelligence Enrichment
The system automatically employs the local LLM to enrich information for every knowledge storage request.

### 1. Operational Logic
- When `SaveWikiContent` or `SynthesizeKnowledge` tools are called, the system kernel detects the action.
- The `IntelligenceEngine` runs in the background to analyze the content.
- Analysis results (Tags, Cross-links) are automatically appended to the bottom of the page.

### 2. Automatic Enrichment Items
- **#Hashtags**: Extracts core topics from the content and registers them as hashtags.
- **[[WikiLinks]]**: Compares with the existing knowledge base to suggest or add links for contextual cross-referencing.

## 🛠️ Maintenance Protocol (Kernel Enforcement)
- **Spec-Drift Detection**: Detects discrepancies between source code and specifications, displaying status on the dashboard ([[Project/ConnectWiki/Status]]).
- **Automatic Log Indexing**: All session logs are aggregated in real-time within the [[Project/ConnectWiki/Logs/Index]].

## 📝 User Collaboration Guide
- If AI-generated tags or links are unsatisfactory, users can edit them directly. The system avoids creating duplicate tags.
- While large-scale synchronization might increase local LLM load, asynchronous processing ensures no impact on tool response times.

---
**Last Updated**: 2026-04-12
**System Status**: Autopilot Mode Enabled (Level 3: Logic Enforcement)
