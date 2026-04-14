"""Pre-computed page digest cache powered by local LLM.

On every wiki page write, the local LLM generates a compact digest
(summary, key entities, tags) and caches it as JSON.  MCP tools like
SearchAcrossWiki use these digests instead of raw content previews,
drastically reducing the number of tokens the external LLM needs to read.

When the local LLM is unavailable the module falls back to basic text
extraction (first sentence) so no feature is ever blocked.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

from config import config_manager

logger = logging.getLogger("connect-wiki.digest")


class DigestCache:
    """Manages pre-computed summaries for wiki pages.

    Digest schema (stored as ``wiki/digests/{page_name}.json``)::

        {
            "summary": "1-2 sentence summary",
            "key_entities": ["entity1", "entity2"],
            "tags": ["tag1", "tag2"],
            "generated_at": "ISO timestamp",
            "source_length": 2500
        }
    """

    @property
    def _digest_dir(self) -> Path:
        """The directory where pre-computed JSON digests are stored."""
        return Path(config_manager.get_config().wiki_root_path) / "digests"

    # ── Read ──────────────────────────────────────────────

    def get_digest(self, page_name: str) -> dict[str, Any] | None:
        """Return the cached digest for *page_name*, or ``None``."""
        path = self._digest_dir / f"{page_name}.json"
        if not path.exists():
            return None
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return None

    def get_summary(self, page_name: str) -> str | None:
        """Convenience: return only the summary string."""
        digest = self.get_digest(page_name)
        return digest.get("summary") if digest else None

    # ── Write / Generate ──────────────────────────────────

    async def generate_digest(self, page_name: str, content: str) -> dict[str, Any]:
        """Use the local LLM to generate a compact digest of *content*.

        Falls back to a simple first-sentence extraction when the LLM is
        unavailable, so callers are never blocked.
        """
        data = await self._llm_digest(page_name, content)

        data["generated_at"] = datetime.now().isoformat()
        data["source_length"] = len(content)

        path = self._digest_dir / f"{page_name}.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
        )

        logger.info(
            "Digest generated for '%s': %s",
            page_name,
            data.get("summary", "")[:80],
        )
        return data

    async def ensure_digest(self, page_name: str, content: str) -> dict[str, Any]:
        """Return the existing digest if still fresh, otherwise regenerate."""
        existing = self.get_digest(page_name)
        if existing and existing.get("source_length") == len(content):
            return existing  # cache hit
        return await self.generate_digest(page_name, content)

    # ── Internal helpers ──────────────────────────────────

    async def _llm_digest(self, page_name: str, content: str) -> dict[str, Any]:
        """Try the local LLM; fall back to heuristic extraction."""
        try:
            from llm_client import llm_client

            prompt = (
                "Analyze this wiki page and return JSON only:\n"
                "{\n"
                '  "summary": "1-2 sentence summary capturing the key point",\n'
                '  "key_entities": ["up to 5 main concepts/entities mentioned"],\n'
                '  "tags": ["up to 5 lowercase categorization tags"]\n'
                "}\n\n"
                f"PAGE: {page_name}\n"
                f"CONTENT (first 2000 chars):\n{content[:2000]}"
            )
            data = await llm_client.generate_json(
                prompt,
                system_prompt=(
                    "You are a summarization engine. "
                    "Return valid JSON only. Be extremely concise."
                ),
            )
            # Minimal validation
            if "summary" not in data:
                raise ValueError("Missing 'summary' key in LLM response")
            return data
        except Exception as exc:
            logger.warning(
                "LLM digest failed for '%s' (%s), using fallback.", page_name, exc
            )
            return self._fallback_digest(page_name, content)

    @staticmethod
    def _fallback_digest(page_name: str, content: str) -> dict[str, Any]:
        """Heuristic digest generation when the LLM is not available.

        Extracts the first meaningful line as a summary and returns empty
        lists for entities and tags.
        """
        # Extract first meaningful line as summary
        summary = ""
        for line in content.split("\n"):
            stripped = line.strip().lstrip("# ").strip()
            if stripped and not stripped.startswith(">"):
                summary = stripped[:200]
                break
        summary = summary or page_name

        return {
            "summary": summary,
            "key_entities": [],
            "tags": [],
        }


digest_cache = DigestCache()
