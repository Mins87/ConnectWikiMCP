"""Conversation auto-capture pipeline for Antigravity brain logs.

Watches the Antigravity brain directory for completed conversation logs
and automatically ingests them into the wiki knowledge base. Each
conversation is distilled by the local LLM into a structured wiki page
under ``Conversations/YYYY-MM-DD/TopicSlug``.

The watcher is designed to run as a background coroutine alongside the
MCP server's main event loop, triggered periodically by the evolution
scheduler or on-demand via MCP tools.
"""
from __future__ import annotations

import json
import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Any

from config import config_manager

logger = logging.getLogger("connect-wiki.watcher")


class ConversationWatcher:
    """Monitors the Antigravity brain directory and auto-ingests conversations.

    Workflow per conversation:
        1. Detect unprocessed conversation directories.
        2. Read ``overview.txt`` (full transcript) and any artifacts.
        3. Distill via local LLM into a compact wiki page.
        4. Save under ``Conversations/YYYY-MM-DD/TopicSlug``.
        5. Mark conversation ID as processed to avoid re-ingestion.
    """

    def __init__(self) -> None:
        """Initialize with empty state; paths are resolved lazily from config."""
        self._processed_ids: set[str] = set()
        self._loaded = False

    # ── Path helpers ─────────────────────────────────────

    @property
    def brain_dir(self) -> Path | None:
        """Return the configured brain watch path, or None if disabled."""
        cfg = config_manager.get_config()
        path = cfg.brain_watch_path.strip()
        if not path:
            return None
        p = Path(path)
        return p if p.exists() else None

    @property
    def _tracker_path(self) -> Path:
        """JSON file tracking already-processed conversation IDs."""
        return Path(config_manager.get_config().wiki_root_path) / "logs" / "processed_conversations.json"

    # ── State persistence ────────────────────────────────

    def _load_tracker(self) -> None:
        """Load the set of processed conversation IDs from disk."""
        if self._loaded:
            return
        if self._tracker_path.exists():
            try:
                data = json.loads(self._tracker_path.read_text(encoding="utf-8"))
                self._processed_ids = set(data.get("processed", []))
            except Exception:
                self._processed_ids = set()
        self._loaded = True

    def _save_tracker(self) -> None:
        """Persist the processed conversation IDs to disk."""
        self._tracker_path.parent.mkdir(parents=True, exist_ok=True)
        self._tracker_path.write_text(
            json.dumps({"processed": sorted(self._processed_ids)}, indent=2),
            encoding="utf-8",
        )

    # ── Discovery ────────────────────────────────────────

    def discover_conversations(self) -> list[dict[str, Any]]:
        """Scan the brain directory for unprocessed conversations.

        Returns:
            A list of dicts with keys: conversation_id, overview_path,
            artifacts (list of artifact file paths), and mtime.
        """
        brain = self.brain_dir
        if not brain:
            return []

        self._load_tracker()
        results = []

        for conv_dir in sorted(brain.iterdir()):
            if not conv_dir.is_dir():
                continue
            conv_id = conv_dir.name

            # Skip already processed
            if conv_id in self._processed_ids:
                continue

            # Look for the overview transcript
            overview = conv_dir / ".system_generated" / "logs" / "overview.txt"
            if not overview.exists():
                continue

            # Collect artifacts
            artifacts = []
            for artifact_name in ("implementation_plan.md", "task.md", "walkthrough.md"):
                artifact_path = conv_dir / artifact_name
                if artifact_path.exists() and artifact_path.stat().st_size > 0:
                    artifacts.append(artifact_path)

            results.append({
                "conversation_id": conv_id,
                "overview_path": overview,
                "artifacts": artifacts,
                "mtime": overview.stat().st_mtime,
            })

        # Sort by modification time (oldest first)
        results.sort(key=lambda x: x["mtime"])
        return results

    # ── Ingestion ────────────────────────────────────────

    async def ingest_conversation(self, conv_info: dict[str, Any]) -> str | None:
        """Process a single conversation into a wiki page.

        Args:
            conv_info: Discovery result dict from ``discover_conversations``.

        Returns:
            The wiki page name if successful, None on failure.
        """
        from llm_client import llm_client
        from wiki_manager import wiki_manager

        conv_id = conv_info["conversation_id"]
        overview_path: Path = conv_info["overview_path"]

        try:
            # Read the transcript (cap at 8000 chars for LLM context)
            transcript = overview_path.read_text(encoding="utf-8", errors="replace")
            transcript_preview = transcript[:8000]

            # Read artifact summaries
            artifact_texts = []
            for art_path in conv_info["artifacts"]:
                art_content = art_path.read_text(encoding="utf-8", errors="replace")
                artifact_texts.append(f"### {art_path.name}\n{art_content[:2000]}")
            artifacts_section = "\n\n".join(artifact_texts) if artifact_texts else "(no artifacts)"

            # Distill via local LLM
            prompt = (
                "Analyze this LLM conversation transcript and create a structured wiki page.\n\n"
                "Output format (Markdown):\n"
                "# [Descriptive Title]\n"
                "> Session: `{conv_id}` | Date: {date}\n\n"
                "## Objective\n[What was the user trying to accomplish? 2-3 sentences]\n\n"
                "## Key Decisions\n[Bullet list of important decisions made]\n\n"
                "## Implementation Summary\n[What was actually done? Key files changed?]\n\n"
                "## Insights & Learnings\n[Any reusable knowledge or patterns discovered]\n\n"
                "## Related Topics\n[Suggest [[WikiLinks]] to related wiki pages]\n\n"
                "---\n"
                "**Tags**: #tag1 #tag2\n\n"
                "Rules:\n"
                "- Title should be descriptive, not generic\n"
                "- Keep total output under 500 words\n"
                "- Focus on WHAT was learned, not blow-by-blow details\n"
                "- Tags should be lowercase, max 5\n\n"
                f"CONVERSATION ID: {conv_id}\n\n"
                f"TRANSCRIPT (first 8000 chars):\n{transcript_preview}\n\n"
                f"ARTIFACTS:\n{artifacts_section}"
            )

            wiki_content = await llm_client.complete_text(
                prompt,
                system_prompt=(
                    "You are a Knowledge Archivist. Distill conversations into "
                    "concise, searchable wiki pages. Output valid Markdown only."
                ),
            )

            if not wiki_content or len(wiki_content.strip()) < 50:
                logger.warning("LLM returned insufficient content for conversation %s", conv_id)
                return None

            # Extract title from the generated content for the page name
            title_slug = self._extract_title_slug(wiki_content, conv_id)
            date_str = datetime.fromtimestamp(conv_info["mtime"]).strftime("%Y-%m-%d")
            page_name = f"Conversations/{date_str}/{title_slug}"

            # Save to wiki
            wiki_manager.write_page(page_name, wiki_content)

            # Mark as processed
            self._processed_ids.add(conv_id)
            self._save_tracker()

            logger.info(
                "Conversation '%s' ingested as wiki page '%s' (%d chars)",
                conv_id[:12], page_name, len(wiki_content),
            )
            return page_name

        except Exception as exc:
            logger.error("Failed to ingest conversation '%s': %s", conv_id[:12], exc)
            return None

    # ── Batch processing ─────────────────────────────────

    async def run_watch_cycle(self) -> str:
        """Discover and ingest all new conversations.

        Returns:
            A human-readable summary of what was processed.
        """
        conversations = self.discover_conversations()
        if not conversations:
            return "No new conversations to process."

        ingested = []
        failed = 0
        for conv in conversations:
            page_name = await self.ingest_conversation(conv)
            if page_name:
                ingested.append(page_name)
            else:
                failed += 1

        summary = f"Processed {len(ingested)} conversations"
        if failed:
            summary += f" ({failed} failed)"
        if ingested:
            summary += f": {', '.join(ingested)}"

        logger.info("Watch cycle complete: %s", summary)
        return summary

    # ── Utilities ────────────────────────────────────────

    @staticmethod
    def _extract_title_slug(content: str, fallback_id: str) -> str:
        """Extract a URL-safe title slug from the generated wiki content.

        Looks for the first markdown H1 heading. Falls back to truncated
        conversation ID if no heading is found.
        """
        for line in content.split("\n"):
            line = line.strip()
            if line.startswith("# ") and len(line) > 3:
                title = line[2:].strip()
                # Sanitize for filesystem
                slug = re.sub(r"[^\w\s-]", "", title)
                slug = re.sub(r"[\s]+", "_", slug).strip("_")
                return slug[:80] if slug else fallback_id[:12]
        return fallback_id[:12]

    def get_status(self) -> dict[str, Any]:
        """Return a status summary for diagnostics.

        Returns:
            Dict with brain path, enabled status, processed count,
            and pending count.
        """
        self._load_tracker()
        brain = self.brain_dir
        pending = len(self.discover_conversations()) if brain else 0
        return {
            "enabled": brain is not None,
            "brain_path": str(brain) if brain else "(not configured)",
            "processed_count": len(self._processed_ids),
            "pending_count": pending,
        }


conversation_watcher = ConversationWatcher()
