import os
import re
import logging
import asyncio
from pathlib import Path
from datetime import datetime
from wiki_manager import wiki_manager
from intelligence_engine import intelligence_engine

logger = logging.getLogger("maintenance-manager")

class MaintenanceManager:
    def __init__(self):
        self.wiki = wiki_manager

    async def perform_maintenance(self, tool_name: str, status: str, **kwargs):
        """Main entry point for autonomous maintenance."""
        logger.info(f"System Maintenance Triggered by {tool_name} ({status})")
        
        try:
            # 1. Update Logs Index
            self._update_logs_index()
            
            # 2. Check for Spec Drift (Simple mtime check)
            drift = self._detect_spec_drift()
            
            # 3. Update status page
            self._update_status_page(drift_detected=drift)
            
            # 4. Asynchronous AI Enrichment (New in v1.3.0)
            if tool_name in ["SaveWikiContent", "SynthesizeKnowledge"] and status == "Success":
                page_name = kwargs.get("name") or kwargs.get("target_page_name")
                if page_name:
                    logger.info(f"Scheduling background AI enrichment for '{page_name}'")
                    # Fire and forget background task to avoid blocking the MCP response
                    asyncio.create_task(self._enrich_page_with_ai(page_name))
            
            logger.info("System Maintenance Completed successfully.")
        except Exception as e:
            logger.error(f"Maintenance failed: {e}", exc_info=True)

    async def _enrich_page_with_ai(self, page_name: str):
        """Background task to enrich a page using local LLM."""
        try:
            # Allow some time for the file to be fully written or just for the system to settle
            await asyncio.sleep(1) 
            
            page = self.wiki.read_page(page_name)
            if not page:
                return
                
            enriched_content = await intelligence_engine.analyze_and_enrich(page_name, page.content)
            if enriched_content:
                # Save the enriched content
                self.wiki.write_page(page_name, enriched_content)
                logger.info(f"AI Enrichment applied to '{page_name}'")
        except Exception as e:
            logger.error(f"AI Enrichment failed for '{page_name}': {e}")

    def _update_logs_index(self):
        """Update Project/ConnectWiki/Logs/Index with latest entries."""
        logs_path = self.wiki.pages_dir / "Project" / "ConnectWiki" / "Logs"
        logger.info(f"Updating Logs Index at {logs_path}")
        
        if not logs_path.exists():
            logger.warning(f"Logs directory not found: {logs_path}")
            return
            
        logs = [f for f in logs_path.rglob("*.md") if f.name.lower() != "index.md"]
        logger.info(f"Found {len(logs)} log files.")
        
        if not logs:
            return

        # Sort by filename descending (newest dates first)
        logs.sort(key=lambda x: x.name, reverse=True) 
        
        content = "# Project Activity Logs Index\n\n"
        content += "> [!NOTE]\n"
        content += "> 이 페이지는 시스템에 의해 자동으로 관리됩니다.\n\n"
        
        for log in logs:
            try:
                rel_path = log.relative_to(self.wiki.pages_dir).with_suffix('')
                # Convert backslashes for wiki links
                name = str(rel_path).replace('\\', '/')
                display_name = log.stem
                content += f"- [[{name}|{display_name}]]\n"
            except Exception as e:
                logger.error(f"Failed to process log path {log}: {e}")
        
        self.wiki.write_page("Project/ConnectWiki/Logs/Index", content)
        logger.info("Logs Index updated.")

    def _detect_spec_drift(self) -> bool:
        """Check if any source files are newer than the specification page."""
        spec_page = self.wiki.pages_dir / "Project" / "ConnectWiki" / "Specification.md"
        if not spec_page.exists():
            return True
            
        spec_mtime = spec_page.stat().st_mtime
        src_dir = Path(__file__).parent
        
        for src_file in src_dir.glob("*.py"):
            if src_file.stat().st_mtime > spec_mtime:
                logger.info(f"Drift detected in {src_file.name}")
                return True
        return False

    def _update_status_page(self, drift_detected: bool):
        """Update real-time status dashboard."""
        page_name = "Project/ConnectWiki/Status"
        status_page = self.wiki.read_page(page_name)
        content = status_page.content if status_page else "# Project Status Dashboard\n"
        
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        drift_msg = "⚠️ UPDATE REQUIRED (Code Drift Detected)" if drift_detected else "✅ SYNCHRONIZED"
        
        status_block = f"## 🛠️ System Sync Status\n- **Last Maintenance**: {timestamp}\n- **Sync State**: {drift_msg}\n- **Kernel Mode**: Autopilot (Enforced)"
        
        if "## 🛠️ System Sync Status" in content:
            # Use regex to replace the old block - handle different line endings or spacing
            content = re.sub(r"## 🛠️ System Sync Status.*?(?=\n\n##|\Z)", status_block + "\n", content, flags=re.DOTALL)
        else:
            content += f"\n\n{status_block}\n"
            
        self.wiki.write_page(page_name, content)
        logger.info("Status page updated.")

    def bootstrap_system_docs(self, overwrite: bool = False):
        """
        Copy official docs from project's 'docs/system' to wiki's 'pages/System'.
        If overwrite is False, only new files are copied (Safe Bootstrap).
        """
        try:
            # Identify project root from src/maintenance_manager.py
            project_root = Path(__file__).parent.parent
            docs_src = project_root / "docs" / "system"
            wiki_dest = self.wiki.pages_dir / "System"
            
            logger.info(f"System Bootstrap: Checking {docs_src} -> {wiki_dest}")
            
            if not docs_src.exists():
                logger.warning(f"Official docs source folder not found at {docs_src}")
                return
                
            wiki_dest.mkdir(parents=True, exist_ok=True)
            
            for doc_file in docs_src.glob("*.md"):
                dest_file = wiki_dest / doc_file.name
                if not dest_file.exists() or overwrite:
                    logger.info(f"📌 Bootstrapping missing system doc: {doc_file.name}")
                    page_name = f"System/{doc_file.stem}"
                    content = doc_file.read_text(encoding="utf-8")
                    self.wiki.write_page(page_name, content)
                else:
                    logger.info(f"✅ System doc already exists, skipping: {doc_file.name}")
                    
        except Exception as e:
            logger.error(f"Bootstrap failed: {e}")

maintenance_manager = MaintenanceManager()
