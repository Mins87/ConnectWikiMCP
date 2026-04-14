from __future__ import annotations

import asyncio
import hashlib
import json
import logging
from pathlib import Path
from typing import Any, Dict

from config.config import config_manager

logger = logging.getLogger("connect-wiki.managers.transform")

class TransformManager:
    """Stage 2 Manager: Responsible for physical high-fidelity extraction (Raw -> Transformed).
    Uses SHA-256 hashing to track content changes and avoid redundant processing.
    """
    
    def __init__(self, raw_dir: Path, transformed_dir: Path) -> None:
        self.raw_dir = raw_dir
        self.transformed_dir = transformed_dir
        self._mid: Any = None
        self._state: Dict[str, str] = {}  # rel_path -> last_hash
        self._state_loaded = False
        
        # Ensure directories exist
        self.raw_dir.mkdir(parents=True, exist_ok=True)
        self.transformed_dir.mkdir(parents=True, exist_ok=True)

    @property
    def _state_file(self) -> Path:
        """JSON file for persisting transformation state (hashes)."""
        root = Path(config_manager.get_config().wiki_root_path)
        return root / "logs" / "transform_state.json"

    def _load_state(self) -> None:
        """Load stored hashes from disk."""
        if self._state_loaded:
            return
        if self._state_file.exists():
            try:
                self._state = json.loads(self._state_file.read_text(encoding="utf-8"))
                logger.debug("Loaded %d file hashes from state.", len(self._state))
            except Exception:
                logger.warning("Failed to load transform state, starting fresh.")
                self._state = {}
        self._state_loaded = True

    def _save_state(self) -> None:
        """Save current hashes to disk."""
        try:
            self._state_file.parent.mkdir(parents=True, exist_ok=True)
            self._state_file.write_text(json.dumps(self._state, indent=2), encoding="utf-8")
        except Exception:
            logger.exception("Failed to save transform state.")

    def _calculate_hash(self, file_path: Path) -> str:
        """Calculate SHA-256 hash of a file's content."""
        sha256 = hashlib.sha256()
        with file_path.open("rb") as f:
            while chunk := f.read(8192):
                sha256.update(chunk)
        return sha256.hexdigest()

    def get_transformed_path(self, relative_path: str) -> Path:
        """Calculate target path for converted markdown in the transformed directory.
        Strictly replaces extensions to avoid double dots like .pdf.md.
        """
        path = Path(relative_path)
        # with_suffix replaces the extension; result: files/my.md (from files/my.pdf)
        return self.transformed_dir / path.with_suffix(".md")

    def _needs_conversion(self, source_path: Path, target_path: Path) -> bool:
        """Decide if conversion is needed based on existence, mtime (optional fallback), and Hash."""
        # 1. If target missing, ALWAYS convert
        if not target_path.exists():
            return True, "Target file missing"

        # 2. Compare against stored hash
        self._load_state()
        rel_path = source_path.relative_to(self.raw_dir).as_posix()
        current_hash = self._calculate_hash(source_path)
        last_hash = self._state.get(rel_path)

        if current_hash != last_hash:
            return True, f"Content changed (Hash mismatch: {current_hash[:8]} vs {str(last_hash)[:8]})"

        return False, "Already up to date (Hash match)"

    async def process_raw_to_transformed(self, abs_raw_path: Path) -> Path:
        """Stage 1 -> Stage 2 transition: Transform raw data into standard MD."""
        self._load_state()
        rel_path = abs_raw_path.relative_to(self.raw_dir).as_posix()
        transformed_path = self.get_transformed_path(rel_path)
        
        needs, reason = self._needs_conversion(abs_raw_path, transformed_path)
        if not needs:
            return transformed_path

        logger.info("Stage 2 (Transforming): %s -> %s (%s)", rel_path, transformed_path.name, reason)
        transformed_path.parent.mkdir(parents=True, exist_ok=True)
        
        if abs_raw_path.suffix.lower() == ".md":
            import shutil
            await asyncio.to_thread(shutil.copy2, abs_raw_path, transformed_path)
        else:
            await asyncio.to_thread(self.convert_file_to_md, abs_raw_path, transformed_path)
            
        # Update hash state
        self._state[rel_path] = self._calculate_hash(abs_raw_path)
        self._save_state()
        
        return transformed_path

    def convert_file_to_md(self, source_path: Path, target_path: Path) -> None:
        """Utilize MarkItDown with local LLM assistance for high-fidelity conversion."""
        target_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            if self._mid is None:
                from markitdown import MarkItDown
                from openai import OpenAI
                
                cfg = config_manager.get_config()
                llm_client = OpenAI(
                    base_url=f"{cfg.local_llm_api_url.rstrip('/')}/v1",
                    api_key=cfg.local_llm_api_key or "ollama"
                )
                self._mid = MarkItDown(llm_client=llm_client, llm_model=cfg.local_llm_model)

            result = self._mid.convert(str(source_path.absolute()))
            target_path.write_text(result.text_content, encoding="utf-8")
        except Exception as exc:
            raise RuntimeError(f"MarkItDown conversion failed for {source_path.name}: {exc}") from exc

    async def run_worker(self, input_queue: asyncio.Queue[Path], output_queue: asyncio.Queue[Path]) -> None:
        """Internal worker loop that consumes transform_queue and notifies hierarchy_queue."""
        logger.info("Transform Manager Worker started: waiting for jobs...")
        while True:
            abs_raw_path = await input_queue.get()
            try:
                # Note: logging handled inside process_raw_to_transformed for clarity
                transformed_path = await self.process_raw_to_transformed(abs_raw_path)
                await output_queue.put(transformed_path)
            except Exception:
                logger.exception("Transform Manager failed for '%s'", abs_raw_path)
            finally:
                input_queue.task_done()
