import os
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict
from markitdown import MarkItDown
from config import config_manager

class WikiPage:
    def __init__(self, name: str, content: str, mtime: datetime):
        self.name = name
        self.content = content
        self.mtime = mtime

class WikiManager:
    def __init__(self):
        self.mid = MarkItDown()

    @property
    def pages_dir(self) -> Path:
        return Path(config_manager.get_config().wiki_root_path) / "pages"

    @property
    def raw_dir(self) -> Path:
        return Path(config_manager.get_config().wiki_root_path) / "raw"

    @property
    def transformed_dir(self) -> Path:
        return Path(config_manager.get_config().wiki_root_path) / "transformed"

    def get_transformed_path(self, relative_raw_path: str) -> Path:
        return self.transformed_dir / f"{relative_raw_path}.md"

    def read_page(self, name: str) -> Optional[WikiPage]:
        file_path = self.pages_dir / f"{name}.md"
        if not file_path.exists():
            return None
        
        content = file_path.read_text(encoding="utf-8")
        mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
        return WikiPage(name, content, mtime)

    def write_page(self, name: str, content: str):
        file_path = self.pages_dir / f"{name}.md"
        file_path.write_text(content, encoding="utf-8")

    def delete_page(self, name: str):
        file_path = self.pages_dir / f"{name}.md"
        if file_path.exists():
            file_path.unlink()

    def list_pages(self) -> List[str]:
        return [f.stem for f in self.pages_dir.glob("*.md")]

    def search_wiki(self, query: str) -> List[WikiPage]:
        results = []
        for name in self.list_pages():
            page = self.read_page(name)
            if page and (query.lower() in page.content.lower() or query.lower() in page.name.lower()):
                results.append(page)
        return results

    def ingest_raw(self, name: str, content: str):
        timestamp = datetime.now().isoformat().replace(":", "-").replace(".", "-")
        filename = f"{timestamp}-{name}.md"
        (self.raw_dir / filename).write_text(content, encoding="utf-8")

    async def read_raw(self, relative_path: str) -> Optional[str]:
        abs_raw_path = self.raw_dir / relative_path
        if not abs_raw_path.exists() or abs_raw_path.is_dir():
            return None

        # Handle .md directly
        if abs_raw_path.suffix.lower() == ".md":
            return abs_raw_path.read_text(encoding="utf-8")

        # Handle binary via MarkItDown
        transformed_path = self.get_transformed_path(relative_path)
        should_convert = True

        if transformed_path.exists():
            raw_mtime = abs_raw_path.stat().st_mtime
            transformed_mtime = transformed_path.stat().st_mtime
            if raw_mtime <= transformed_mtime:
                should_convert = False

        if should_convert:
            self.convert_file_to_md(abs_raw_path, transformed_path)

        return transformed_path.read_text(encoding="utf-8")

    def convert_file_to_md(self, source_path: Path, target_path: Path):
        target_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            result = self.mid.convert(str(source_path.absolute()))
            target_path.write_text(result.text_content, encoding="utf-8")
        except Exception as e:
            raise RuntimeError(f"MarkItDown conversion failed for {source_path.name}: {e}")

    def sync_raw_folder(self) -> Dict[str, int]:
        converted = 0
        skipped = 0

        for file_path in self.raw_dir.rglob("*"):
            if file_path.is_dir():
                continue
            
            relative_path = file_path.relative_to(self.raw_dir)
            if file_path.suffix.lower() == ".md":
                skipped += 1
                continue

            transformed_path = self.get_transformed_path(str(relative_path))
            needs_conversion = True

            if transformed_path.exists():
                if file_path.stat().st_mtime <= transformed_path.stat().st_mtime:
                    needs_conversion = False

            if needs_conversion:
                self.convert_file_to_md(file_path, transformed_path)
                converted += 1
            else:
                skipped += 1

        return {"converted": converted, "skipped": skipped}

    def list_raw(self) -> List[str]:
        return [str(f.relative_to(self.raw_dir)) for f in self.raw_dir.rglob("*") if f.is_file()]

wiki_manager = WikiManager()
