"""Maintenance Manager — background housekeeping for ConnectWikiMCP v2.0.

Simplified from the v1 version: removed AI enrichment, digest generation,
and evolution cycles. The compile engine now handles all intelligence work.

Remaining responsibilities:
  - Update the knowledge graph visualizer HTML
  - Rebuild the master index when pages change
  - Log-based health monitoring
"""
from __future__ import annotations

import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Any

from wiki_manager import wiki_manager

logger = logging.getLogger("connect-wiki.maintenance")


class MaintenanceManager:
    """Lightweight background maintenance for wiki health."""

    def __init__(self) -> None:
        self.wiki = wiki_manager

    async def perform_maintenance(self) -> None:
        """Run periodic housekeeping tasks."""
        logger.info("Running maintenance cycle")
        self._update_visualizer()
        self.wiki.rebuild_index()

    def _update_visualizer(self) -> None:
        """Regenerate the interactive graph visualizer HTML."""
        try:
            html = self.wiki.generate_graph_html()
            output_path = self.wiki.root_dir / "visualizer.html"
            output_path.write_text(html, encoding="utf-8")
            logger.info("Visualizer updated at %s", output_path)
        except Exception:
            logger.exception("Failed to update visualizer")


maintenance_manager = MaintenanceManager()
