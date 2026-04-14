"""Compile Engine — transforms raw data into structured wiki pages.

This is the core intelligence of ConnectWikiMCP v2.0. It replaces the old
IntelligenceEngine with a pipeline that:
  1. Preserves ALL information (no lossy summarization)
  2. Structures content into navigable, hierarchical wiki pages
  3. Injects cross-references ([[links]]) and breadcrumbs automatically
  4. Updates the master index after every compilation

Golden Rules:
  - NEVER delete or compress information from the source
  - Organize and format, don't rewrite
  - Raw sources are immutable — only the wiki output is generated
"""
from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Any

from config import config_manager

logger = logging.getLogger("connect-wiki.compiler")

# Documents shorter than this are stored as a single wiki page
SINGLE_PAGE_THRESHOLD = 3000  # characters

# Heading pattern for structure detection
HEADING_RE = re.compile(r"^(#{1,3})\s+(.+)$", re.MULTILINE)


class CompileEngine:
    """Transforms raw staged data into structured, navigable wiki pages.

    The engine is called by the scheduler whenever new or updated files
    are detected in any of the three raw source folders.
    """

    async def compile(self, raw_path: Path, target_root: str | None = None) -> list[str]:
        """Main entry point: read a raw file and produce wiki page(s).

        Args:
            raw_path: Absolute path to the raw source file.
            target_root: Optional wiki path prefix (e.g. "Archive/Guidebook").
                         Derived from filename if omitted.

        Returns:
            List of wiki page names that were created or updated.
        """
        from wiki_manager import wiki_manager

        content = await self._read_raw_content(raw_path)
        if not content or len(content.strip()) < 10:
            logger.warning("Skipping empty or trivial file: %s", raw_path.name)
            return []

        # Determine target root from filename if not provided
        if not target_root:
            target_root = self._derive_target_root(raw_path)

        # Decide compilation strategy based on content size
        if len(content) < SINGLE_PAGE_THRESHOLD:
            pages = await self._compile_single(content, target_root)
        else:
            pages = await self._compile_hierarchical(content, target_root)

        # Update master index after compilation
        wiki_manager.rebuild_index()

        logger.info(
            "Compiled '%s' → %d page(s) under '%s'",
            raw_path.name, len(pages), target_root,
        )
        return pages

    # ── Single-page compilation ─────────────────────────────

    async def _compile_single(self, content: str, target_root: str) -> list[str]:
        """Small content → one well-formatted wiki page."""
        from wiki_manager import wiki_manager

        formatted = await self._format_content(content, target_root)
        wiki_manager.write_page(target_root, formatted)

        # Try to inject cross-references
        await self._inject_links(target_root)

        return [target_root]

    # ── Hierarchical compilation ────────────────────────────

    async def _compile_hierarchical(self, content: str, target_root: str) -> list[str]:
        """Large content → index page + sub-pages, preserving all detail."""
        from wiki_manager import wiki_manager

        # Step 1: Detect logical sections from headings
        sections = self._split_by_headings(content)

        if len(sections) <= 1:
            # No clear heading structure — fall back to chunk-based split
            sections = self._split_by_size(content)

        created_pages: list[str] = []

        # Step 2: Create sub-pages for each section
        for i, section in enumerate(sections):
            section_title = section["title"]
            section_content = section["content"]

            # Sanitize title for filesystem
            slug = self._slugify(section_title) or f"Section_{i + 1}"
            page_name = f"{target_root}/{slug}"

            # Add breadcrumb at top
            breadcrumb = f"> 📍 [[{target_root}/Index|← Index]] / **{section_title}**\n\n"
            full_content = breadcrumb + f"# {section_title}\n\n" + section_content

            wiki_manager.write_page(page_name, full_content)
            created_pages.append(page_name)

        # Step 3: Create index page with TOC
        index_lines = [
            f"# {target_root.split('/')[-1]}",
            "",
            f"> {len(created_pages)} sections | Source: compiled from raw data",
            "",
            "## Table of Contents",
            "",
        ]
        for i, section in enumerate(sections):
            slug = self._slugify(section["title"]) or f"Section_{i + 1}"
            page_name = f"{target_root}/{slug}"
            index_lines.append(f"{i + 1}. [[{page_name}|{section['title']}]]")

        index_page = f"{target_root}/Index"
        wiki_manager.write_page(index_page, "\n".join(index_lines) + "\n")
        created_pages.insert(0, index_page)

        # Step 4: Inject cross-references for each page
        for page_name in created_pages:
            await self._inject_links(page_name)

        return created_pages

    # ── Content splitting ───────────────────────────────────

    def _split_by_headings(self, content: str) -> list[dict[str, str]]:
        """Split content at top-level headings (# or ##)."""
        matches = list(HEADING_RE.finditer(content))
        if not matches:
            return []

        # Only split at level 1-2 headings
        split_points = [m for m in matches if len(m.group(1)) <= 2]
        if len(split_points) < 2:
            return []

        sections: list[dict[str, str]] = []
        for i, match in enumerate(split_points):
            title = match.group(2).strip()
            start = match.end()
            end = split_points[i + 1].start() if i + 1 < len(split_points) else len(content)
            body = content[start:end].strip()
            if body:
                sections.append({"title": title, "content": body})

        return sections

    def _split_by_size(self, content: str, chunk_size: int = 4000) -> list[dict[str, str]]:
        """Fallback: split content into roughly equal chunks by paragraph."""
        paragraphs = content.split("\n\n")
        sections: list[dict[str, str]] = []
        current_chunk: list[str] = []
        current_size = 0
        section_num = 1

        for para in paragraphs:
            current_chunk.append(para)
            current_size += len(para)

            if current_size >= chunk_size:
                sections.append({
                    "title": f"Part {section_num}",
                    "content": "\n\n".join(current_chunk),
                })
                current_chunk = []
                current_size = 0
                section_num += 1

        if current_chunk:
            sections.append({
                "title": f"Part {section_num}",
                "content": "\n\n".join(current_chunk),
            })

        return sections

    # ── Formatting & enrichment ─────────────────────────────

    async def _format_content(self, content: str, page_name: str) -> str:
        """Light formatting pass: ensure proper heading, add breadcrumb.

        Does NOT modify the substantive content — only improves structure.
        """
        # Add title heading if not present
        if not content.strip().startswith("#"):
            title = page_name.split("/")[-1].replace("_", " ")
            content = f"# {title}\n\n{content}"

        return content

    async def _inject_links(self, page_name: str) -> None:
        """Scan page content and inject [[links]] to related existing pages.

        Uses the local LLM to identify references. Falls back to no-op
        if the LLM is unavailable.
        """
        from wiki_manager import wiki_manager

        page = wiki_manager.read_page(page_name)
        if not page:
            return

        existing_pages = set(wiki_manager.list_pages())
        existing_pages.discard(page_name)
        current_links = set(wiki_manager.extract_links(page.content))

        # Find pages that are mentioned by name but not yet linked
        new_links: list[str] = []
        for other_page in existing_pages:
            if other_page in current_links:
                continue
            # Check if the page name (or its leaf) appears in content
            leaf = other_page.split("/")[-1].replace("_", " ")
            if leaf.lower() in page.content.lower() and len(leaf) > 3:
                new_links.append(other_page)

        if not new_links:
            return

        # Append suggested links section
        links_section = (
            "\n\n---\n"
            "**Related**: "
            + ", ".join(f"[[{link}]]" for link in new_links[:5])
        )
        wiki_manager.write_page(page_name, page.content + links_section)

    # ── Utilities ───────────────────────────────────────────

    async def _read_raw_content(self, raw_path: Path) -> str | None:
        """Read raw file, converting non-markdown formats via MarkItDown."""
        import asyncio

        if not raw_path.exists():
            return None

        if raw_path.suffix.lower() == ".md":
            return await asyncio.to_thread(raw_path.read_text, encoding="utf-8")

        # Non-markdown: convert via MarkItDown
        from wiki_manager import wiki_manager

        transformed_path = wiki_manager.get_transformed_path(
            raw_path.relative_to(wiki_manager.raw_dir).as_posix()
        )
        if wiki_manager._needs_conversion(raw_path, transformed_path):
            await asyncio.to_thread(
                wiki_manager.convert_file_to_md, raw_path, transformed_path
            )
        return await asyncio.to_thread(transformed_path.read_text, encoding="utf-8")

    @staticmethod
    def _derive_target_root(raw_path: Path) -> str:
        """Generate a wiki path prefix from the raw file's location and name."""
        # Determine category from parent folder
        parent = raw_path.parent.name
        category_map = {
            "files": "Archive",
            "memos": "Memos",
            "conversations": "Conversations",
        }
        category = category_map.get(parent, "Archive")

        # Clean up filename
        stem = raw_path.stem
        # Remove timestamp prefixes like "2026-04-14T12-30-00-"
        stem = re.sub(r"^\d{4}-\d{2}-\d{2}T[\d-]+-", "", stem)
        # Remove file extension artifacts
        stem = re.sub(r"\.(pdf|docx|pptx|xlsx)$", "", stem, flags=re.IGNORECASE)
        # Sanitize
        slug = re.sub(r"[^\w\s-]", "", stem)
        slug = re.sub(r"[\s]+", "_", slug).strip("_")

        return f"{category}/{slug}" if slug else f"{category}/Untitled"

    @staticmethod
    def _slugify(text: str) -> str:
        """Convert a title into a filesystem-safe slug."""
        slug = re.sub(r"[^\w\s-]", "", text)
        slug = re.sub(r"[\s]+", "_", slug).strip("_")
        return slug[:80]


compile_engine = CompileEngine()
