import asyncio
import json
import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Any

from config.config import config_manager
from config.llm_client import llm_client

logger = logging.getLogger("connect-wiki.hierarchy")

HEADING_RE = re.compile(r"^(#+)\s+(.+)$", re.MULTILINE)
SINGLE_PAGE_THRESHOLD = 4000  # Chars

class HierarchyManager:
    """Stage 3 Manager: Responsible for semantic hierarchization and wiki creation (Transformed -> Wiki)."""
    
    def __init__(self, pages_dir: Path, transformed_dir: Path) -> None:
        self.pages_dir = pages_dir
        self.transformed_dir = transformed_dir
        # Ensure pages directory exists
        self.pages_dir.mkdir(parents=True, exist_ok=True)

    async def compile_transformed(self, md_path: Path, target_root: str | None = None) -> list[str]:
        """Stage 2 -> Stage 3 transition: Synthesize wiki structure from MD workpiece."""
        if not md_path.exists():
            logger.error("Transformed file not found: %s", md_path)
            return []

        content = await asyncio.to_thread(md_path.read_text, encoding="utf-8")
        if not content or len(content.strip()) < 10:
            return []

        if not target_root:
            target_root = self._derive_target_root(md_path)

        if len(content) < SINGLE_PAGE_THRESHOLD:
            pages = await self._compile_single(content, target_root)
        else:
            pages = await self._compile_hierarchical_semantic(content, target_root)

        logger.info("Synthesized '%s' -> %d page(s) under '%s'", md_path.name, len(pages), target_root)
        return pages

    def _derive_target_root(self, md_path: Path) -> str:
        """Derive wiki path prefix from filename or structure."""
        stem = md_path.stem
        # Simplified for now: use stem as root, or put in Archive/Unclassified
        safe_stem = re.sub(r"[^\w\s-]", "", stem).strip().replace(" ", "_")
        return f"Archive/{safe_stem}"

    async def _compile_single(self, content: str, target_root: str) -> list[str]:
        """Wrap small content into a single wiki page."""
        page_name = f"{target_root}/Index"
        # Since I can't reach wiki_manager here easily, 
        # I'll rely on a shared utility or pass the writer.
        # [Refinement]: Hierarchizer should have its own writer or use a shared one.
        # For now, I'll implement internal write_page logic.
        self.write_page(page_name, content)
        return [page_name]

    async def _compile_hierarchical_semantic(self, content: str, target_root: str) -> list[str]:
        """Use LLM to split content into logical semantic sections."""
        logger.info("Analyzing semantic structure for '%s'...", target_root)
        
        headings_list = "\n".join([f"- {m.group(2)}" for m in HEADING_RE.finditer(content[:50000])])
        prompt = (
            "Analyze the following document structure. Suggest a descriptive TOC in JSON list format. "
            "Return: [{\"title\": \"...\", \"summary\": \"...\"}]\n\n"
            f"HEADINGS:\n{headings_list}\n\nCONTENT PREVIEW:\n{content[:1000]}"
        )
        
        try:
            semantic_map = await llm_client.generate_json(prompt, system_prompt="You are a senior Wiki architect.")
            sections_plan = semantic_map if isinstance(semantic_map, list) else semantic_map.get("sections", [])
        except Exception:
            sections_plan = []

        # Fallback split logic
        sections = self._split_by_headings(content)
        created_pages: list[str] = []
        
        for i, section in enumerate(sections):
            title = sections_plan[i].get("title", section["title"]) if i < len(sections_plan) else section["title"]
            page_name = f"{target_root}/{self._slugify(title) or f'Section_{i+1}'}"
            
            breadcrumb = f"> 📍 [[{target_root}/Index|← Index]] / **{title}**\n\n"
            full_content = breadcrumb + f"# {title}\n\n" + section["content"]
            self.write_page(page_name, full_content)
            created_pages.append(page_name)

        # Index page
        index_content = f"# {target_root.split('/')[-1]}\n\n## Table of Contents\n\n"
        for i, p in enumerate(created_pages):
            index_content += f"{i+1}. [[{p}|{p.split('/')[-1]}]]\n"
        
        self.write_page(f"{target_root}/Index", index_content)
        created_pages.insert(0, f"{target_root}/Index")
        return created_pages

    def write_page(self, name: str, content: str) -> None:
        """Write a page to the wiki pages directory."""
        import os
        safe_path = Path(name.replace("/", os.sep) + ".md")
        abs_path = self.pages_dir / safe_path
        abs_path.parent.mkdir(parents=True, exist_ok=True)
        abs_path.write_text(content, encoding="utf-8")

    def read_page(self, name: str) -> dict[str, Any] | None:
        """Load a wiki page by its name."""
        import os
        safe_path = Path(name.replace("/", os.sep) + ".md")
        file_path = self.pages_dir / safe_path
        if not file_path.exists() or file_path.is_dir():
            return None
        content = file_path.read_text(encoding="utf-8")
        mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
        return {"name": name, "content": content, "mtime": mtime}

    def list_pages(self) -> list[str]:
        """List all wiki page titles found in the pages directory."""
        if not self.pages_dir.exists():
            return []
        return sorted(
            path.relative_to(self.pages_dir).with_suffix("").as_posix()
            for path in self.pages_dir.rglob("*.md")
            if path.is_file()
        )

    def extract_links(self, content: str) -> list[str]:
        """Extract all unique [[WikiLinks]] from markdown content."""
        WIKILINK_RE = re.compile(r"\[\[([^|\]]+)(?:\|[^\]]+)?\]\]")
        return sorted({match.strip() for match in WIKILINK_RE.findall(content) if match.strip()})

    def get_graph_data(self) -> dict[str, Any]:
        """Generate a structured graph including virtual folder centroids and page links."""
        pages = set(self.list_pages())
        nodes_dict: dict[str, dict] = {}
        links: list[dict] = []
        
        for name in sorted(pages):
            nodes_dict[name] = {"id": name, "type": "page", "val": 1}
            
        folders = set()
        for name in pages:
            parts = name.split("/")
            for i in range(2, len(parts)):
                folder_path = "/".join(parts[:i]) + "/"
                folders.add(folder_path)
        
        for folder in sorted(folders):
            nodes_dict[folder] = {"id": folder, "type": "folder", "val": 2}
            
        for name in nodes_dict:
            if "/" not in name or name == "/":
                continue
            parts = name.rstrip("/").split("/")
            if len(parts) > 2:
                parent_path = "/".join(parts[:-1]) + "/"
                if parent_path in nodes_dict:
                    links.append({"source": name, "target": parent_path, "type": "hierarchical"})
            elif not name.endswith("/") and len(parts) > 1:
                parent_path = "/".join(parts[:-1]) + "/"
                if parent_path in nodes_dict:
                    links.append({"source": name, "target": parent_path, "type": "hierarchical"})

        for name in sorted(pages):
            page_data = self.read_page(name)
            if not page_data:
                continue
            for link in self.extract_links(page_data["content"]):
                if link in pages:
                    links.append({"source": name, "target": link, "type": "wiki"})
        
        for link in links:
            if link["source"] in nodes_dict:
                nodes_dict[link["source"]]["val"] += 1
            if link["target"] in nodes_dict:
                nodes_dict[link["target"]]["val"] += 1
            
        return {"nodes": list(nodes_dict.values()), "links": links}

    def generate_graph_html(self, template_path: Path) -> str:
        """Dynamically generate interactive HTML for the knowledge graph."""
        data = self.get_graph_data()
        if not template_path.exists():
            return "<html><body><h1>Template Not Found</h1></body></html>"
            
        template = template_path.read_text(encoding="utf-8")
        html = template.replace("{json_data}", json.dumps(data, ensure_ascii=False)) \
                       .replace("{{node_count}}", str(len(data['nodes']))) \
                       .replace("{{link_count}}", str(len(data['links'])))
        return html

    def rebuild_index(self) -> str:
        """Regenerate the master index.md from all existing wiki pages."""
        pages = self.list_pages()
        if not pages:
            content = "# 📚 Knowledge Index\n\n> No pages yet.\n"
            self.write_page("index", content)
            return content

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
                if node[key]:
                    lines.append(f"{indent}- **{key}/**")
                    lines.extend(_render(node[key], depth + 1, full_path))
                else:
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

    def _split_by_headings(self, content: str) -> list[dict[str, str]]:
        sections = []
        last_pos = 0
        last_title = "Overview"
        for match in HEADING_RE.finditer(content):
            sections.append({"title": last_title, "content": content[last_pos:match.start()].strip()})
            last_title = match.group(2)
            last_pos = match.start()
        sections.append({"title": last_title, "content": content[last_pos:].strip()})
        return [s for s in sections if s["content"]]

    def _slugify(self, text: str) -> str:
        return re.sub(r"[^\w]+", "_", text).strip("_")

    async def run_worker(self, input_queue: asyncio.Queue[Path]) -> None:
        """Internal worker loop that consumes hierarchy_queue and creates wiki pages."""
        logger.info("Hierarchy Manager Worker started: waiting for notifications...")
        while True:
            transformed_path = await input_queue.get()
            try:
                logger.info("Stage 3 (Hierarchizing): %s", transformed_path.name)
                pages = await self.compile_transformed(transformed_path)
                logger.info("Stage 3 Done: %d pages synthesized.", len(pages))
            except Exception:
                logger.exception("Hierarchy Manager failed for '%s'", transformed_path)
            finally:
                input_queue.task_done()

import os
