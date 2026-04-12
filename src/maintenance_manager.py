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

        if status == "Success" and tool_name in {"SaveWikiContent", "SynthesizeKnowledge"}:
            page_name = (metadata or {}).get("name") or (metadata or {}).get("target_page_name")
            if page_name:
                self._schedule_enrichment(page_name)

    def _schedule_enrichment(self, page_name: str) -> None:
        task = asyncio.create_task(self._enrich_page_with_ai(page_name))
        self._active_tasks.add(task)
        task.add_done_callback(lambda done: self._active_tasks.discard(done))

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
        logs_path = self.wiki.pages_dir / "Project" / "ConnectWiki" / "Logs"
        if not logs_path.exists():
            return
        logs = [path for path in logs_path.rglob("*.md") if path.is_file() and path.name.lower() != "index.md"]
        if not logs:
            return
        logs.sort(key=lambda path: path.name, reverse=True)

        lines = [
            "# Project Activity Logs Index",
            "",
            "> [!NOTE]",
            "> 이 페이지는 시스템에 의해 자동으로 관리됩니다.",
            "",
        ]
        for log in logs:
            rel = log.relative_to(self.wiki.pages_dir).with_suffix("")
            name = rel.as_posix()
            lines.append(f"- [[{name}|{log.stem}]]")
        self.wiki.write_page("Project/ConnectWiki/Logs/Index", "\n".join(lines) + "\n")

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


maintenance_manager = MaintenanceManager()
