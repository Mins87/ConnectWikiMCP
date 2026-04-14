from __future__ import annotations

import asyncio
import json
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from config import config_manager

WIKILINK_RE = re.compile(r"\[\[(.*?)(?:\|.*?)?\]\]")
TAG_RE = re.compile(r"(?<!\w)#([\w-]+)")
REDACT_KEYS = {"local_llm_api_key", "api_key", "authorization", "token", "password", "secret"}


@dataclass(slots=True)
class WikiPage:
    """Represents a single wiki page with its metadata and content."""
    name: str
    content: str
    mtime: datetime


class WikiManager:
    """Manages wiki page storage, retrieval, search, and relationship mapping."""
    def __init__(self) -> None:
        """Initialize the manager and internal state."""
        self._mid = None

    @property
    def root_dir(self) -> Path:
        """The base directory for all wiki data."""
        return Path(config_manager.get_config().wiki_root_path)

    @property
    def pages_dir(self) -> Path:
        """Directory containing formal wiki pages (.md)."""
        return self.root_dir / "pages"

    @property
    def raw_dir(self) -> Path:
        """Directory for raw, unorganized staged content."""
        return self.root_dir / "raw"

    @property
    def raw_files_dir(self) -> Path:
        """Raw files: PDFs, URL captures, uploaded documents."""
        return self.raw_dir / "files"

    @property
    def raw_memos_dir(self) -> Path:
        """Raw memos: AI agent notes and quick captures."""
        return self.raw_dir / "memos"

    @property
    def raw_conversations_dir(self) -> Path:
        """Raw conversations: chat history backups."""
        return self.raw_dir / "conversations"

    @property
    def transformed_dir(self) -> Path:
        """Directory for markdown versions of non-md raw files."""
        return self.root_dir / "transformed"

    @property
    def logs_dir(self) -> Path:
        """Directory for system intent and maintenance logs."""
        return self.root_dir / "logs"

    def _safe_relative(self, relative_path: str) -> Path:
        """Validate and resolve a relative path to prevent directory traversal.

        Args:
            relative_path: User-provided relative path string.

        Returns:
            A safe Path object.

        Raises:
            ValueError: If the path is absolute or attempts traversal.
        """
        relative = Path(relative_path)
        if relative.is_absolute():
            raise ValueError("Absolute paths are not allowed.")
        
        # Resolve path to prevent traversal attacks
        try:
            full_path = (self.root_dir / relative).resolve()
            root_resolved = self.root_dir.resolve()
            if not str(full_path).startswith(str(root_resolved)):
                raise ValueError("Path traversal is not allowed.")
        except (OSError, ValueError):
             # On some systems resolve() can fail if file doesn't exist, 
             # but ".." in parts is still a good fallback for non-existent paths.
             if ".." in relative.parts:
                 raise ValueError("Path traversal is not allowed.")
        
        return relative

    def get_transformed_path(self, relative_raw_path: str) -> Path:
        """Calculate the shadow markdown path for a raw file.

        Args:
            relative_raw_path: The relative path inside the raw directory.
        """
        return self.transformed_dir / f"{self._safe_relative(relative_raw_path).as_posix()}.md"

    def read_page(self, name: str) -> WikiPage | None:
        """Load a wiki page by its name.

        Returns:
            A WikiPage object or None if the page doesn't exist.
        """
        file_path = self.pages_dir / f"{name}.md"
        if not file_path.exists() or file_path.is_dir():
            return None
        content = file_path.read_text(encoding="utf-8")
        mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
        return WikiPage(name=name, content=content, mtime=mtime)

    @property
    def history_dir(self) -> Path:
        """Directory for page versioning/backups."""
        return self.root_dir / "history"

    def write_page(self, name: str, content: str) -> None:
        """Write markdown content to a page, creating a backup if it existed.

        Args:
            name: Page title.
            content: Markdown text.
        """
        file_path = self.pages_dir / f"{name}.md"
        file_path.parent.mkdir(parents=True, exist_ok=True)

        # Back up the existing version before overwriting
        if file_path.exists():
            timestamp = datetime.now().strftime("%Y-%m-%dT%H-%M-%S")
            backup_path = self.history_dir / name / f"{timestamp}.md"
            backup_path.parent.mkdir(parents=True, exist_ok=True)
            backup_path.write_text(file_path.read_text(encoding="utf-8"), encoding="utf-8")

        file_path.write_text(content, encoding="utf-8")

    def delete_page(self, name: str) -> None:
        """Permanently remove a wiki page from the filesystem."""
        file_path = self.pages_dir / f"{name}.md"
        if file_path.exists() and file_path.is_file():
            file_path.unlink()

    def list_pages(self) -> list[str]:
        """List all wiki page titles found in the pages directory."""
        if not self.pages_dir.exists():
            return []
        return sorted(
            path.relative_to(self.pages_dir).with_suffix("").as_posix()
            for path in self.pages_dir.rglob("*.md")
            if path.is_file()
        )

    def search_wiki(self, query: str) -> list[WikiPage]:
        """Keyword-based search (synchronous fallback)."""
        needle = query.lower().strip()
        results: list[WikiPage] = []
        for name in self.list_pages():
            page = self.read_page(name)
            if page and (needle in page.name.lower() or needle in page.content.lower()):
                results.append(page)
        return results

    async def search_wiki_semantic(self, query: str, top_k: int = 10) -> list[WikiPage]:
        """Hybrid semantic→keyword search.

        Tries vector similarity search first. Falls back to keyword search
        if the embedding index is empty or the LLM is unavailable.
        """
        from embedding_manager import embedding_manager

        semantic_names = await embedding_manager.search(query, top_k=top_k)

        if semantic_names:
            results = [p for name in semantic_names if (p := self.read_page(name))]
            if results:
                return results

        # Fallback: keyword search
        return self.search_wiki(query)

    def extract_links(self, content: str) -> list[str]:
        """Extract all unique [[WikiLinks]] from markdown content."""
        return sorted({match.strip() for match in WIKILINK_RE.findall(content) if match.strip()})

    def extract_tags(self, content: str) -> list[str]:
        """Extract all unique #tags from markdown content."""
        return sorted({match.strip() for match in TAG_RE.findall(content) if match.strip()})

    def get_backlinks(self, target_page: str) -> list[str]:
        """Find all pages that link to the given target_page."""
        backlinks: list[str] = []
        for name in self.list_pages():
            if name == target_page:
                continue
            page = self.read_page(name)
            if page and target_page in self.extract_links(page.content):
                backlinks.append(name)
        return backlinks

    def get_graph_data(self) -> dict[str, Any]:
        """Generate a structured graph including virtual folder centroids and page links."""
        pages = set(self.list_pages())
        nodes_dict: dict[str, dict] = {}
        links: list[dict] = []
        
        # 1. Prepare Page Nodes
        for name in sorted(pages):
            nodes_dict[name] = {"id": name, "type": "page", "val": 1}
            
        # 2. Extract Folder Hierarchy and add Folder Nodes (Skip top-level root folders)
        folders = set()
        for name in pages:
            parts = name.split("/")
            # Accumulate parent directory paths starting from depth 2
            # This skips root classification folders like 'Project/', 'Memo/', etc.
            for i in range(2, len(parts)):
                folder_path = "/".join(parts[:i]) + "/"
                folders.add(folder_path)
        
        for folder in sorted(folders):
            nodes_dict[folder] = {"id": folder, "type": "folder", "val": 2}
            
        # 3. Add Structural Hierarchy Links
        for name in nodes_dict:
            if "/" not in name or name == "/":
                continue
            
            parts = name.rstrip("/").split("/")
            # Only build hierarchy links if we are deeper than root level
            if len(parts) > 2:
                parent_path = "/".join(parts[:-1]) + "/"
                if parent_path in nodes_dict:
                    links.append({"source": name, "target": parent_path, "type": "hierarchical"})
            elif not name.endswith("/") and len(parts) > 1:
                # This is a page in a subfolder (e.g., A/B/Page)
                parent_path = "/".join(parts[:-1]) + "/"
                if parent_path in nodes_dict:
                    links.append({"source": name, "target": parent_path, "type": "hierarchical"})

        # 4. Add Cross-Reference wiki links (Page -> Page)
        for name in sorted(pages):
            page = self.read_page(name)
            if not page:
                continue
            for link in self.extract_links(page.content):
                if link in pages:
                    links.append({"source": name, "target": link, "type": "wiki"})
        
        # 5. Finalize node values based on total connectivity
        for link in links:
            if link["source"] in nodes_dict:
                nodes_dict[link["source"]]["val"] += 1
            if link["target"] in nodes_dict:
                nodes_dict[link["target"]]["val"] += 1
            
        return {"nodes": list(nodes_dict.values()), "links": links}

    def get_tagged_raw_files(self, tag: str) -> list[str]:
        """Retrieve all raw source files that contain a specific #tag."""
        target = f"#{tag}"
        matches: list[str] = []
        for rel_path in self.list_raw():
            file_path = self.raw_dir / rel_path
            if file_path.suffix.lower() != ".md":
                continue
            content = file_path.read_text(encoding="utf-8")
            if target in content:
                matches.append(rel_path)
        return matches

    def sanitize_metadata(self, metadata: dict[str, Any]) -> dict[str, Any]:
        """Redact sensitive keys and truncate long strings in log metadata."""
        safe: dict[str, Any] = {}
        for key, value in metadata.items():
            if key.lower() in REDACT_KEYS:
                safe[key] = "***REDACTED***"
            elif isinstance(value, str) and len(value) > 1000:
                safe[key] = value[:1000] + "..."
            else:
                safe[key] = value
        return safe

    def log_intent(self, query: str, tool_name: str, outcome: str, metadata: dict[str, Any] | None = None) -> None:
        """Record an LLM's tool usage intent and outcome for system evolution audits."""
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        entry = {
            "timestamp": datetime.now().isoformat(),
            "query": query,
            "tool": tool_name,
            "outcome": outcome,
            "metadata": self.sanitize_metadata(metadata or {}),
        }
        log_file = self.logs_dir / "intent_history.jsonl"
        with log_file.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(entry, ensure_ascii=False) + "\n")

    def read_intent_logs(self, limit: int = 50) -> list[dict[str, Any]]:
        """Read the most recent entries from the intent history log."""
        log_file = self.logs_dir / "intent_history.jsonl"
        if not log_file.exists():
            return []
        lines = log_file.read_text(encoding="utf-8").splitlines()
        return [json.loads(line) for line in lines[-limit:] if line.strip()]

    def ingest_raw(self, name: str, content: str) -> str:
        """Save raw text into a timestamped file in the staging directory."""
        timestamp = datetime.now().isoformat().replace(":", "-").replace(".", "-")
        safe_name = Path(name).name
        filename = f"{timestamp}-{safe_name}.md"
        self.raw_dir.mkdir(parents=True, exist_ok=True)
        (self.raw_dir / filename).write_text(content, encoding="utf-8")
        return filename

    async def read_raw(self, relative_path: str) -> str | None:
        """Read a file from the raw folder, performing conversion to markdown if needed."""
        rel = self._safe_relative(relative_path)
        abs_raw_path = self.raw_dir / rel
        if not abs_raw_path.exists() or abs_raw_path.is_dir():
            return None
        if abs_raw_path.suffix.lower() == ".md":
            return await asyncio.to_thread(abs_raw_path.read_text, encoding="utf-8")

        transformed_path = self.get_transformed_path(rel.as_posix())
        if self._needs_conversion(abs_raw_path, transformed_path):
            await asyncio.to_thread(self.convert_file_to_md, abs_raw_path, transformed_path)
        return await asyncio.to_thread(transformed_path.read_text, encoding="utf-8")

    def _needs_conversion(self, source_path: Path, target_path: Path) -> bool:
        if not target_path.exists():
            return True
        return source_path.stat().st_mtime > target_path.stat().st_mtime

    def convert_file_to_md(self, source_path: Path, target_path: Path) -> None:
        """Use MarkItDown to convert any file format into a markdown equivalent."""
        target_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            if self._mid is None:
                from markitdown import MarkItDown
                self._mid = MarkItDown()
            result = self._mid.convert(str(source_path.absolute()))
            target_path.write_text(result.text_content, encoding="utf-8")
        except Exception as exc:
            raise RuntimeError(f"MarkItDown conversion failed for {source_path.name}: {exc}") from exc

    def sync_raw_folder(self) -> dict[str, int]:
        """Scan and convert all outdated or new items in the raw folder to transformed markdown."""
        converted = 0
        skipped = 0
        if not self.raw_dir.exists():
            return {"converted": 0, "skipped": 0}

        for file_path in self.raw_dir.rglob("*"):
            if file_path.is_dir():
                continue
            relative_path = file_path.relative_to(self.raw_dir)
            if file_path.suffix.lower() == ".md":
                skipped += 1
                continue
            transformed_path = self.get_transformed_path(relative_path.as_posix())
            if self._needs_conversion(file_path, transformed_path):
                self.convert_file_to_md(file_path, transformed_path)
                converted += 1
            else:
                skipped += 1
        return {"converted": converted, "skipped": skipped}

    def list_raw(self) -> list[str]:
        """List all files in the raw folder by their relative paths."""
        if not self.raw_dir.exists():
            return []
        return sorted(
            path.relative_to(self.raw_dir).as_posix()
            for path in self.raw_dir.rglob("*")
            if path.is_file()
        )


    def generate_graph_html(self) -> str:
        """Dynamically generate a premium interactive HTML for the knowledge graph (SSR)."""
        data = self.get_graph_data()
        
        template_path = Path(__file__).parent / "templates" / "visualizer.html"
        if not template_path.exists():
            return "<html><body><h1>Template Not Found</h1></body></html>"
            
        template = template_path.read_text(encoding="utf-8")
        
        # Safe SSR injection - Matching user's fixed template format
        html = template.replace("{json_data}", json.dumps(data, ensure_ascii=False)) \
                       .replace("{{node_count}}", str(len(data['nodes']))) \
                       .replace("{{link_count}}", str(len(data['links'])))
        
        return html

    def rebuild_index(self) -> str:
        """Regenerate the master index.md from all existing wiki pages.

        The index is a hierarchical TOC that AI agents read first to
        navigate the knowledge base without costly search operations.
        """
        pages = self.list_pages()
        if not pages:
            content = "# 📚 Knowledge Index\n\n> No pages yet.\n"
            self.write_page("index", content)
            return content

        # Build a tree from page paths
        tree: dict = {}
        for page in pages:
            if page == "index":
                continue
            parts = page.split("/")
            node = tree
            for part in parts:
                node = node.setdefault(part, {})

        def _render(node: dict, depth: int = 0, prefix: str = "") -> list[str]:
            lines: list[str] = []
            for key in sorted(node.keys()):
                full_path = f"{prefix}/{key}" if prefix else key
                indent = "  " * depth
                if node[key]:  # has children → category
                    lines.append(f"{indent}- **{key}/**")
                    lines.extend(_render(node[key], depth + 1, full_path))
                else:  # leaf → wiki page link
                    lines.append(f"{indent}- [[{full_path}|{key}]]")
            return lines

        body = _render(tree)
        content = (
            "# 📚 Knowledge Index\n\n"
            f"> {len(pages)} pages | "
            f"Updated: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n"
            + "\n".join(body)
            + "\n"
        )
        self.write_page("index", content)
        return content


wiki_manager = WikiManager()
