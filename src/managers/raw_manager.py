from __future__ import annotations

import asyncio
import logging
from pathlib import Path

from config.config import config_manager
from config.llm_client import llm_client

logger = logging.getLogger("connect-wiki.raw")

class RawManager:
    """Stage 1 Manager: Responsible for monitoring raw sources and dispatching work."""
    
    def __init__(self, raw_dir: Path) -> None:
        self.raw_dir = raw_dir
        # Ensure raw directories exist
        self.raw_dir.mkdir(parents=True, exist_ok=True)
        for sub in ("files", "memos", "conversations"):
            (self.raw_dir / sub).mkdir(parents=True, exist_ok=True)

    def list_raw(self) -> list[str]:
        """List all files in the raw folder by their relative paths."""
        if not self.raw_dir.exists():
            return []
        return sorted(
            path.relative_to(self.raw_dir).as_posix()
            for path in self.raw_dir.rglob("*")
            if path.is_file()
        )

    async def run_worker(self, output_queue: asyncio.Queue[Path], transform_manager: Any) -> None:
        """Internal worker loop that monitors raw sources and pushes jobs to transform_queue."""
        # Default to 60s for high responsiveness, but can be overridden by config
        interval = 60
        
        logger.info("Stage 1 (Scouting): Monitoring raw/ every %d seconds.", interval)
        
        while True:
            try:
                # Stage 1: Scout for files needing transformation
                for rel_path in self.list_raw():
                    abs_raw_path = self.raw_dir / rel_path
                    transformed_path = transform_manager.get_transformed_path(rel_path)
                    
                    # Check if conversion is needed (now returns Tuple[bool, str])
                    needs, reason = transform_manager._needs_conversion(abs_raw_path, transformed_path)
                    
                    if needs:
                        logger.info("[Stage 1] Dispatching '%s' to pipeline. (Reason: %s)", rel_path, reason)
                        await output_queue.put(abs_raw_path)
                    else:
                        # Log periodically or just debug to avoid noise
                        logger.debug("Raw Manager: Skip '%s' (%s)", rel_path, reason)
                        
            except Exception:
                logger.exception("Raw Manager Worker cycle failed")
            
            await asyncio.sleep(interval)

from typing import Any
