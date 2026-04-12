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
    name: str
    content: str
    mtime: datetime


class WikiManager:
    def __init__(self) -> None:
        self._mid = None

    @property
    def root_dir(self) -> Path:
        return Path(config_manager.get_config().wiki_root_path)

    @property
    def pages_dir(self) -> Path:
        return self.root_dir / "pages"

    @property
    def raw_dir(self) -> Path:
        return self.root_dir / "raw"

    @property
    def transformed_dir(self) -> Path:
        return self.root_dir / "transformed"

    @property
    def logs_dir(self) -> Path:
        return self.root_dir / "logs"

    def _safe_relative(self, relative_path: str) -> Path:
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
        return self.transformed_dir / f"{self._safe_relative(relative_raw_path).as_posix()}.md"

    def read_page(self, name: str) -> WikiPage | None:
        file_path = self.pages_dir / f"{name}.md"
        if not file_path.exists() or file_path.is_dir():
            return None
        content = file_path.read_text(encoding="utf-8")
        mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
        return WikiPage(name=name, content=content, mtime=mtime)

    def write_page(self, name: str, content: str) -> None:
        file_path = self.pages_dir / f"{name}.md"
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(content, encoding="utf-8")

    def delete_page(self, name: str) -> None:
        file_path = self.pages_dir / f"{name}.md"
        if file_path.exists() and file_path.is_file():
            file_path.unlink()

    def list_pages(self) -> list[str]:
        if not self.pages_dir.exists():
            return []
        return sorted(
            path.relative_to(self.pages_dir).with_suffix("").as_posix()
            for path in self.pages_dir.rglob("*.md")
            if path.is_file()
        )

    def search_wiki(self, query: str) -> list[WikiPage]:
        needle = query.lower().strip()
        results: list[WikiPage] = []
        for name in self.list_pages():
            page = self.read_page(name)
            if page and (needle in page.name.lower() or needle in page.content.lower()):
                results.append(page)
        return results

    def extract_links(self, content: str) -> list[str]:
        return sorted({match.strip() for match in WIKILINK_RE.findall(content) if match.strip()})

    def extract_tags(self, content: str) -> list[str]:
        return sorted({match.strip() for match in TAG_RE.findall(content) if match.strip()})

    def get_backlinks(self, target_page: str) -> list[str]:
        backlinks: list[str] = []
        for name in self.list_pages():
            if name == target_page:
                continue
            page = self.read_page(name)
            if page and target_page in self.extract_links(page.content):
                backlinks.append(name)
        return backlinks

    def get_graph_data(self) -> dict[str, Any]:
        pages = set(self.list_pages())
        nodes = [{"id": name, "type": "page"} for name in sorted(pages)]
        edges = []
        for name in sorted(pages):
            page = self.read_page(name)
            if not page:
                continue
            for link in self.extract_links(page.content):
                if link in pages:
                    edges.append({"source": name, "target": link})
        return {"nodes": nodes, "edges": edges}

    def get_tagged_raw_files(self, tag: str) -> list[str]:
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
        log_file = self.logs_dir / "intent_history.jsonl"
        if not log_file.exists():
            return []
        lines = log_file.read_text(encoding="utf-8").splitlines()
        return [json.loads(line) for line in lines[-limit:] if line.strip()]

    def ingest_raw(self, name: str, content: str) -> str:
        timestamp = datetime.now().isoformat().replace(":", "-").replace(".", "-")
        safe_name = Path(name).name
        filename = f"{timestamp}-{safe_name}.md"
        self.raw_dir.mkdir(parents=True, exist_ok=True)
        (self.raw_dir / filename).write_text(content, encoding="utf-8")
        return filename

    async def read_raw(self, relative_path: str) -> str | None:
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
        if not self.raw_dir.exists():
            return []
        return sorted(
            path.relative_to(self.raw_dir).as_posix()
            for path in self.raw_dir.rglob("*")
            if path.is_file()
        )


wiki_manager = WikiManager()
