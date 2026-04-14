from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING, List

from config.config import config_manager

if TYPE_CHECKING:
    from managers.hierarchy_manager import HierarchyManager
    from watchers.base import BaseWatcher

logger = logging.getLogger("connect-wiki.managers.maintenance")

class MaintenanceManager:
    """Orchestrator for system health and background knowledge watchers.
    Managed by the server's main scheduler.
    """

    def __init__(self) -> None:
        self.watchers: List[BaseWatcher] = []

    def register_watcher(self, watcher: BaseWatcher) -> None:
        """Register a new watcher to be executed during maintenance cycles."""
        self.watchers.append(watcher)
        logger.info("Registered watcher: %s", watcher.__class__.__name__)

    async def perform_maintenance(self, hierarchy: HierarchyManager) -> None:
        """Run periodic housekeeping tasks and execute all registered watchers."""
        logger.info("Starting maintenance/watch cycle")
        
        # 1. Update system visualizer and index
        self._update_visualizer(hierarchy)
        hierarchy.rebuild_index()

        # 2. Run all registered watchers (e.g., AntigravityWatcher)
        for watcher in self.watchers:
            try:
                await watcher.watch(hierarchy)
            except Exception:
                logger.exception("Watcher %s failed during cycle", watcher.__class__.__name__)

        logger.info("Maintenance/watch cycle complete")

    def _update_visualizer(self, hierarchy: HierarchyManager) -> None:
        """Regenerate the interactive graph visualizer HTML."""
        try:
            # Note: Being in src/managers, the templates folder is at ../templates
            template_path = Path(__file__).parent.parent / "templates" / "visualizer.html"
            html = hierarchy.generate_graph_html(template_path)
            
            # Save to the wiki root (level above pages_dir)
            output_path = hierarchy.pages_dir.parent / "visualizer.html"
            output_path.write_text(html, encoding="utf-8")
            logger.debug("Visualizer updated at %s", output_path)
        except Exception:
            logger.exception("Failed to update visualizer")

maintenance_manager = MaintenanceManager()
