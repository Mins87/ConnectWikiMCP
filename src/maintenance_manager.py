from __future__ import annotations

import asyncio
import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Any

from intelligence_engine import intelligence_engine
from wiki_manager import wiki_manager

logger = logging.getLogger("connect-wiki.maintenance")


class MaintenanceManager:
    def __init__(self) -> None:
        self.wiki = wiki_manager
        self._active_tasks: set[asyncio.Task] = set()

    async def perform_maintenance(self, tool_name: str, status: str, metadata: dict[str, Any] | None = None) -> None:
        logger.info("System maintenance triggered by %s (%s)", tool_name, status)
        drift = self._detect_spec_drift()
        self._update_logs_index()
        self._update_status_page(drift_detected=drift)
        self._update_visualizer()

        if status == "Success" and tool_name in {"SaveWikiContent", "SynthesizeKnowledge"}:
            page_name = (metadata or {}).get("name") or (metadata or {}).get("target_page_name")
            if page_name:
                self._schedule_enrichment(page_name)
                self._schedule_embedding(page_name)

    def _schedule_enrichment(self, page_name: str) -> None:
        task = asyncio.create_task(self._enrich_page_with_ai(page_name))
        self._active_tasks.add(task)
        task.add_done_callback(lambda done: self._active_tasks.discard(done))

    def _schedule_embedding(self, page_name: str) -> None:
        task = asyncio.create_task(self._embed_page(page_name))
        self._active_tasks.add(task)
        task.add_done_callback(lambda done: self._active_tasks.discard(done))

    async def _embed_page(self, page_name: str) -> None:
        try:
            from embedding_manager import embedding_manager

            page = self.wiki.read_page(page_name)
            if not page:
                return
            await embedding_manager.index_page(page_name, page.content)
        except Exception:
            logger.exception("Embedding indexing failed for '%s'", page_name)

    async def _enrich_page_with_ai(self, page_name: str) -> None:
        try:
            await asyncio.sleep(0.25)
            page = self.wiki.read_page(page_name)
            if not page:
                return
            enriched_content = await intelligence_engine.analyze_and_enrich(page_name, page.content)
            if enriched_content and enriched_content != page.content:
                self.wiki.write_page(page_name, enriched_content)
                logger.info("AI enrichment applied to '%s'", page_name)
        except Exception:
            logger.exception("AI enrichment failed for '%s'", page_name)

    def _update_logs_index(self) -> None:
        """Auto-index any directory containing date-prefixed log pages (YYYY-MM-DD_*)."""
        date_pattern = re.compile(r"^\d{4}-\d{2}-\d{2}[_-]")
        log_dirs: dict[Path, list[Path]] = {}

        for md_file in self.wiki.pages_dir.rglob("*.md"):
            if md_file.is_file() and date_pattern.match(md_file.stem) and md_file.name.lower() != "index.md":
                log_dirs.setdefault(md_file.parent, []).append(md_file)

        for log_dir, logs in log_dirs.items():
            logs.sort(key=lambda p: p.name, reverse=True)
            rel_dir = log_dir.relative_to(self.wiki.pages_dir)
            index_page_name = (rel_dir / "Index").as_posix()

            lines = [
                f"# {rel_dir.name} Log Index",
                "",
                "> [!NOTE]",
                "> This index is automatically managed by the system.",
                "",
            ]
            for log in logs:
                rel = log.relative_to(self.wiki.pages_dir).with_suffix("")
                name = rel.as_posix()
                lines.append(f"- [[{name}|{log.stem}]]")
            self.wiki.write_page(index_page_name, "\n".join(lines) + "\n")


    def _detect_spec_drift(self) -> bool:
        spec_page = self.wiki.pages_dir / "Project" / "ConnectWiki" / "Specification.md"
        if not spec_page.exists():
            return True
        spec_mtime = spec_page.stat().st_mtime
        src_dir = Path(__file__).parent
        return any(src_file.stat().st_mtime > spec_mtime for src_file in src_dir.glob("*.py"))

    def _update_status_page(self, *, drift_detected: bool) -> None:
        page_name = "Project/ConnectWiki/Status"
        existing = self.wiki.read_page(page_name)
        content = existing.content if existing else "# Project Status Dashboard\n"
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        drift_msg = "⚠️ UPDATE REQUIRED (Code Drift Detected)" if drift_detected else "✅ SYNCHRONIZED"
        block = (
            "## 🛠️ System Sync Status\n"
            f"- **Last Maintenance**: {timestamp}\n"
            f"- **Sync State**: {drift_msg}\n"
            "- **Kernel Mode**: Managed"
        )
        pattern = r"## 🛠️ System Sync Status.*?(?=\n\n##|\Z)"
        if re.search(pattern, content, flags=re.DOTALL):
            content = re.sub(pattern, block + "\n", content, flags=re.DOTALL)
        else:
            content = content.rstrip() + "\n\n" + block + "\n"
        self.wiki.write_page(page_name, content)
    
    def _update_visualizer(self) -> None:
        """Automatically regenerate the interactive graph visualizer."""
        try:
            html = self.wiki.generate_graph_html()
            output_path = self.wiki.root_dir / "visualizer.html"
            output_path.write_text(html, encoding="utf-8")
            logger.info("Knowledge graph visualizer auto-updated at %s", output_path)
        except Exception:
            logger.exception("Failed to auto-update knowledge graph visualizer")

    def bootstrap_system_docs(self, overwrite: bool = False) -> int:
        project_root = Path(__file__).parent.parent
        docs_src = project_root / "docs" / "system"
        if not docs_src.exists():
            raise FileNotFoundError(f"Official docs source folder not found at {docs_src}")

        synced = 0
        for doc_file in docs_src.glob("*.md"):
            page_name = f"System/{doc_file.stem}"
            dest_page = self.wiki.pages_dir / f"{page_name}.md"
            if overwrite or not dest_page.exists():
                self.wiki.write_page(page_name, doc_file.read_text(encoding="utf-8"))
                synced += 1
        return synced

    async def run_evolution_cycle(self) -> str:
        """Analyze intent logs and auto-update System/Intelligence.md.
        
        Returns a summary of what was updated, or a reason why it was skipped.
        """
        from llm_client import llm_client

        logs = self.wiki.read_intent_logs(200)
        if not logs:
            return "No logs to analyze."

        intelligence_page = self.wiki.read_page("System/Intelligence")
        current_docs = intelligence_page.content if intelligence_page else "(empty)"

        log_summary = "\n".join(
            f"[{e['timestamp']}] {e['tool']} → {e['outcome']}"
            for e in logs[-100:]
        )

        prompt = f"""You are a System Growth Analyst for a personal knowledge management wiki.
Analyze the recent usage logs and identify actionable insights to improve the system's intelligence guidelines.

CURRENT INTELLIGENCE DOCS:
{current_docs[:2000]}

RECENT USAGE LOGS (last 100 events):
{log_summary}

Instructions:
1. Identify the top 3-5 patterns (frequently used tools, common topics, failure modes).
2. Suggest concrete improvements or rules to add to the intelligence document.
3. Return ONLY a Markdown section titled '## 🤖 Auto-Evolution Insights (YYYY-MM-DD)' with your findings.
Do NOT rewrite the full document. Output only the new section to append."""

        try:
            new_section = await llm_client.complete_text(
                prompt,
                system_prompt="You are a concise system analyst. Output only valid Markdown.",
            )
        except Exception as exc:
            logger.error("Evolution cycle LLM call failed: %s", exc)
            return f"LLM unavailable: {exc}"

        timestamp = datetime.now().strftime("%Y-%m-%d")
        new_section = new_section.strip().replace(
            "YYYY-MM-DD", timestamp
        )

        updated = (current_docs.rstrip() + "\n\n" + new_section + "\n") if current_docs else new_section
        self.wiki.write_page("System/Intelligence", updated)

        # Log the evolution event
        self.wiki.log_intent("Auto evolution cycle", "EvolutionCycle", "Success", {"logs_analyzed": len(logs)})
        logger.info("Evolution cycle completed: updated System/Intelligence.md")
        return f"Evolution complete: analyzed {len(logs)} events and appended new insights."


maintenance_manager = MaintenanceManager()
