from __future__ import annotations

import json
import logging
import math
from pathlib import Path

from config import config_manager

logger = logging.getLogger("connect-wiki.embeddings")


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    """Compute cosine similarity between two vectors without numpy dependency."""
    dot = sum(x * y for x, y in zip(a, b))
    mag_a = math.sqrt(sum(x * x for x in a))
    mag_b = math.sqrt(sum(x * x for x in b))
    if mag_a == 0.0 or mag_b == 0.0:
        return 0.0
    return dot / (mag_a * mag_b)


class EmbeddingManager:
    """Manages a lightweight vector index for semantic search over wiki pages.

    The index is stored as ``wiki/embeddings.json``:
        { "page_name": [float, float, ...], ... }

    Falls back to keyword search gracefully if the embedding model is
    unavailable (returns an empty list from llm_client.get_embedding).
    """

    def __init__(self) -> None:
        self._index: dict[str, list[float]] = {}
        self._loaded = False

    @property
    def _index_path(self) -> Path:
        """The filesystem path where the vector index is stored."""
        return Path(config_manager.get_config().wiki_root_path) / "embeddings.json"

    def _load(self) -> None:
        """Load the vector index from disk into memory if not already loaded."""
        if self._loaded:
            return
        if self._index_path.exists():
            try:
                self._index = json.loads(self._index_path.read_text(encoding="utf-8"))
            except Exception:
                self._index = {}
        self._loaded = True

    def _save(self) -> None:
        """Serialize the current memory index to disk safely."""
        self._index_path.parent.mkdir(parents=True, exist_ok=True)
        self._index_path.write_text(
            json.dumps(self._index, ensure_ascii=False),
            encoding="utf-8",
        )

    async def index_page(self, name: str, content: str) -> None:
        """Generate and store an embedding for a single page."""
        from llm_client import llm_client

        self._load()
        # Use page name + first 1000 chars as the indexed text
        text = f"{name}\n{content[:1000]}"
        embedding = await llm_client.get_embedding(text)
        if not embedding:
            return  # LLM unavailable — skip silently
        self._index[name] = embedding
        self._save()
        logger.debug("Indexed embedding for '%s'", name)

    async def remove_page(self, name: str) -> None:
        """Remove a page's embedding from the index.

        Args:
            name: The title of the page to remove.
        """
        self._load()
        if name in self._index:
            del self._index[name]
            self._save()

    async def search(self, query: str, top_k: int = 5) -> list[str]:
        """Return the top-k page names most semantically similar to query.

        Returns an empty list if the index is empty or the LLM is unavailable,
        allowing the caller to fall back to keyword search.
        """
        from llm_client import llm_client

        self._load()
        if not self._index:
            return []

        query_vec = await llm_client.get_embedding(query)
        if not query_vec:
            return []  # LLM unavailable

        scores: list[tuple[float, str]] = []
        for page_name, page_vec in self._index.items():
            if len(page_vec) != len(query_vec):
                continue
            score = _cosine_similarity(query_vec, page_vec)
            scores.append((score, page_name))

        scores.sort(key=lambda t: t[0], reverse=True)
        return [name for _, name in scores[:top_k]]

    async def rebuild_index(self, pages: dict[str, str]) -> int:
        """Re-index all pages from scratch. Returns the number of pages indexed."""
        from llm_client import llm_client

        self._index = {}
        indexed = 0
        for name, content in pages.items():
            text = f"{name}\n{content[:1000]}"
            embedding = await llm_client.get_embedding(text)
            if embedding:
                self._index[name] = embedding
                indexed += 1
        if indexed:
            self._save()
        logger.info("Rebuilt search index: %d pages indexed", indexed)
        return indexed

    def is_available(self) -> bool:
        """Returns True if there are any indexed embeddings."""
        self._load()
        return bool(self._index)


embedding_manager = EmbeddingManager()
