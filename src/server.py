"""ConnectWikiMCP v2.0 — AI Long-term Memory Engine.

Exposes exactly 4 MCP tools:
  - Write: Store information (text or URL) into raw sources
  - Read:  Retrieve compiled wiki pages
  - SystemStatus: View system health and visualizer link
  - ConfigureSettings: Update runtime configuration

All compilation from raw → wiki is handled internally by the
local LLM pipeline (CompileEngine + Scheduler). External AI agents
only consume the finished wiki product.
"""
from __future__ import annotations

import asyncio
import contextlib
import json
import logging
import os
import re
import socket
import sys
from datetime import datetime
from typing import Any, Optional

from mcp.server.fastmcp import FastMCP

from config import config_manager

logger = logging.getLogger("connect-wiki.server")

mcp = FastMCP("ConnectWikiMCP")


def is_port_in_use(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(("0.0.0.0", port)) == 0


# ── Core Tools ───────────────────────────────────────────────


@mcp.tool()
async def Write(input: str, name: Optional[str] = None) -> str:
    """Store information into the knowledge base for processing.

    Accepts raw text or a URL. URLs are automatically detected and
    their content is extracted:
    - Regular web pages: text extraction via trafilatura
    - YouTube URLs: transcript extraction via YouTube API

    The data is saved to the raw staging area. A background scheduler
    will compile it into structured wiki pages automatically.

    Args:
        input: Text content or a URL to capture.
        name: Optional title/identifier for the entry.
    """
    from wiki_manager import wiki_manager

    input_stripped = input.strip()

    # ── URL detection ──
    if re.match(r"https?://", input_stripped):
        return await _ingest_url(input_stripped, name)

    # ── Raw text / memo ──
    note_name = name or f"memo_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    safe_name = re.sub(r"[^\w\s-]", "", note_name)
    safe_name = re.sub(r"[\s]+", "_", safe_name).strip("_")

    timestamp = datetime.now().strftime("%Y-%m-%dT%H-%M-%S")
    filename = f"{timestamp}-{safe_name}.md"
    filepath = wiki_manager.raw_memos_dir / filename
    filepath.parent.mkdir(parents=True, exist_ok=True)
    filepath.write_text(f"# {note_name}\n\n{input_stripped}", encoding="utf-8")

    _log_intent("Write", "Success", {"name": note_name, "type": "memo", "size": len(input_stripped)})
    return f"Memo '{note_name}' saved. It will be compiled into the wiki automatically."


async def _ingest_url(url: str, name: str | None) -> str:
    """Extract content from a URL and save to raw/files/."""
    from wiki_manager import wiki_manager

    yt_pattern = re.compile(r"(?:youtube\.com/watch\?v=|youtu\.be/)([\w-]+)")
    yt_match = yt_pattern.search(url)

    if yt_match:
        # YouTube transcript
        video_id = yt_match.group(1)
        try:
            from youtube_transcript_api import YouTubeTranscriptApi
            transcript_list = await asyncio.to_thread(
                YouTubeTranscriptApi.get_transcript, video_id, languages=["ko", "en"]
            )
            raw_text = " ".join(entry["text"] for entry in transcript_list)
            note_name = name or f"youtube_{video_id}"
            content = f"# {note_name}\n\n> Source: {url}\n\n{raw_text}"
        except Exception as exc:
            return f"Failed to fetch YouTube transcript: {exc}"
    else:
        # Regular web page
        try:
            import trafilatura
            downloaded = await asyncio.to_thread(trafilatura.fetch_url, url)
            if not downloaded:
                return f"Failed to download URL: {url}"
            raw_text = await asyncio.to_thread(
                trafilatura.extract, downloaded,
                include_comments=False, include_tables=True
            )
            if not raw_text:
                return f"Could not extract readable content from: {url}"
            note_name = name or url.split("//")[-1].split("/")[0]
            content = f"# {note_name}\n\n> Source: {url}\n\n{raw_text}"
        except Exception as exc:
            return f"Failed to capture URL: {exc}"

    # Save to raw/files/
    safe_name = re.sub(r"[^\w\s-]", "", note_name)
    safe_name = re.sub(r"[\s]+", "_", safe_name).strip("_")
    timestamp = datetime.now().strftime("%Y-%m-%dT%H-%M-%S")
    filename = f"{timestamp}-{safe_name}.md"
    filepath = wiki_manager.raw_files_dir / filename
    filepath.parent.mkdir(parents=True, exist_ok=True)
    filepath.write_text(content, encoding="utf-8")

    _log_intent("Write", "Success", {"name": note_name, "type": "url", "url": url})
    return f"Captured '{url}' as '{note_name}'. It will be compiled into the wiki automatically."


@mcp.tool()
async def Read(name: str) -> str:
    """Read a compiled wiki page from the knowledge base.

    Special names:
    - "_list": Returns all page titles in the wiki
    - "_index": Returns the master knowledge index (start here!)

    Args:
        name: Page path (e.g., "Project/ClaudeCode/Guidebook") or special command.
    """
    from wiki_manager import wiki_manager

    # Special: list all pages
    if name == "_list":
        pages = wiki_manager.list_pages()
        if not pages:
            return "No pages in the wiki yet."
        _log_intent("Read", "Success", {"type": "list", "count": len(pages)})
        return "\n".join(pages)

    # Special: master index
    if name == "_index":
        page = wiki_manager.read_page("index")
        if not page:
            # Auto-generate index if missing
            content = wiki_manager.rebuild_index()
            _log_intent("Read", "Success", {"type": "index", "generated": True})
            return content
        _log_intent("Read", "Success", {"type": "index"})
        return page.content

    # Normal page read
    page = wiki_manager.read_page(name)
    if not page:
        return f"Page '{name}' not found. Use Read('_list') to see available pages."
    _log_intent("Read", "Success", {"name": name})
    return page.content


@mcp.tool()
async def SystemStatus() -> str:
    """View system health, processing queue, and knowledge graph visualizer link."""
    from wiki_manager import wiki_manager

    cfg = config_manager.get_config()
    pages = wiki_manager.list_pages()
    graph = wiki_manager.get_graph_data()

    # Count pending raw files
    pending = 0
    for sub in ("files", "memos", "conversations"):
        sub_dir = wiki_manager.raw_dir / sub
        if sub_dir.exists():
            pending += sum(1 for f in sub_dir.rglob("*") if f.is_file())

    status = (
        "## 📊 ConnectWikiMCP Status\n\n"
        f"- **Wiki Pages**: {len(pages)}\n"
        f"- **Graph Nodes**: {len(graph['nodes'])}\n"
        f"- **Graph Links**: {len(graph['links'])}\n"
        f"- **Raw Queue**: {pending} file(s) in staging\n"
        f"- **LLM Backend**: {cfg.local_llm_type} ({cfg.local_llm_model})\n"
        f"- **LLM URL**: {cfg.local_llm_api_url}\n"
        f"\n"
        f"🔗 **Visualizer**: http://localhost:{cfg.mcp_port}/visualizer\n"
    )

    _log_intent("SystemStatus", "Success", {"pages": len(pages)})
    return status


@mcp.tool()
async def ConfigureSettings(
    wiki_root_path: Optional[str] = None,
    local_llm_type: Optional[str] = None,
    local_llm_api_url: Optional[str] = None,
    local_llm_model: Optional[str] = None,
    local_llm_api_key: Optional[str] = None,
    mcp_port: Optional[int] = None,
) -> str:
    """Update runtime configuration parameters for the ConnectWiki system.

    Args:
        wiki_root_path: The local filesystem path for wiki data.
        local_llm_type: Backend type (e.g., 'ollama', 'llamacpp').
        local_llm_api_url: Connection URL for local inference.
        local_llm_model: Target model identifier.
        local_llm_api_key: Optional token for inference APIs.
        mcp_port: Networking port for the MCP interface.
    """
    updates = {
        "wiki_root_path": wiki_root_path,
        "local_llm_type": local_llm_type,
        "local_llm_api_url": local_llm_api_url,
        "local_llm_model": local_llm_model,
        "local_llm_api_key": local_llm_api_key,
        "mcp_port": mcp_port,
    }
    config_manager.update_config(updates)
    return "Settings updated."


# ── Internal helpers ─────────────────────────────────────────


def _log_intent(tool_name: str, outcome: str, metadata: dict[str, Any] | None = None) -> None:
    """Lightweight intent logging without triggering heavy maintenance."""
    try:
        from wiki_manager import wiki_manager
        wiki_manager.log_intent(f"Executed {tool_name}", tool_name, outcome, metadata or {})
    except Exception:
        pass


# ── Scheduler & Server ──────────────────────────────────────


async def _compile_scheduler() -> None:
    """Background task: watch raw folders for changes and trigger compilation.

    Scans raw/files/, raw/memos/, raw/conversations/ for unprocessed files.
    Uses a simple tracker file to avoid reprocessing.
    """
    from compile_engine import compile_engine
    from wiki_manager import wiki_manager

    tracker_path = wiki_manager.logs_dir / "compiled_files.json"

    def _load_tracker() -> set[str]:
        if tracker_path.exists():
            try:
                return set(json.loads(tracker_path.read_text(encoding="utf-8")))
            except Exception:
                pass
        return set()

    def _save_tracker(compiled: set[str]) -> None:
        tracker_path.parent.mkdir(parents=True, exist_ok=True)
        tracker_path.write_text(
            json.dumps(sorted(compiled), indent=2), encoding="utf-8"
        )

    cfg = config_manager.get_config()
    interval = max(cfg.conversation_watch_interval_minutes, 5) * 60  # reuse existing config

    logger.info("Compile scheduler started: scanning every %d seconds.", interval)
    await asyncio.sleep(60)  # initial delay

    while True:
        try:
            compiled = _load_tracker()
            new_count = 0

            for sub_dir in (wiki_manager.raw_files_dir, wiki_manager.raw_memos_dir, wiki_manager.raw_conversations_dir):
                if not sub_dir.exists():
                    continue
                for raw_file in sorted(sub_dir.rglob("*")):
                    if raw_file.is_dir():
                        continue
                    file_key = raw_file.relative_to(wiki_manager.raw_dir).as_posix()
                    if file_key in compiled:
                        continue

                    try:
                        pages = await compile_engine.compile(raw_file)
                        if pages:
                            compiled.add(file_key)
                            new_count += 1
                            logger.info("Compiled '%s' → %s", file_key, pages)
                    except Exception:
                        logger.exception("Failed to compile '%s'", file_key)

            if new_count:
                _save_tracker(compiled)
                logger.info("Compile cycle: %d new file(s) processed.", new_count)

        except Exception:
            logger.exception("Compile scheduler cycle failed")

        await asyncio.sleep(interval)


async def _conversation_watcher_scheduler() -> None:
    """Background task: scan brain directory for new conversations."""
    cfg = config_manager.get_config()
    brain_path = cfg.brain_watch_path.strip()
    interval = cfg.conversation_watch_interval_minutes

    if interval <= 0 or not brain_path:
        logger.info("Conversation watcher disabled.")
        return

    logger.info("Conversation watcher started: scanning '%s' every %d min.", brain_path, interval)
    await asyncio.sleep(120)

    while True:
        try:
            from conversation_watcher import conversation_watcher
            summary = await conversation_watcher.run_watch_cycle()
            if "No new" not in summary:
                logger.info("Conversation watcher: %s", summary)
        except Exception:
            logger.exception("Conversation watcher cycle failed")
        await asyncio.sleep(interval * 60)


def main() -> None:
    if hasattr(sys.stdin, "reconfigure"):
        sys.stdin.reconfigure(encoding="utf-8-sig")
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(line_buffering=True, write_through=True)

    config_manager.initialize()
    transport = os.getenv("MCP_TRANSPORT", "http").lower()
    cfg = config_manager.get_config()
    port = cfg.mcp_port

    def run_http() -> None:
        import uvicorn
        from contextlib import asynccontextmanager
        from starlette.applications import Starlette
        from starlette.routing import Mount, Route
        from starlette.responses import HTMLResponse
        from starlette.staticfiles import StaticFiles

        if is_port_in_use(port):
            logger.error("Port %d is already in use. Cannot start HTTP server.", port)
            return

        mcp_app = mcp.streamable_http_app()

        async def serve_visualizer(request):
            from wiki_manager import wiki_manager
            html = wiki_manager.generate_graph_html()
            return HTMLResponse(content=html)

        @asynccontextmanager
        async def lifespan(app):
            async with mcp.session_manager.run():
                compile_task = asyncio.create_task(_compile_scheduler())
                watch_task = asyncio.create_task(_conversation_watcher_scheduler())
                try:
                    yield
                finally:
                    compile_task.cancel()
                    watch_task.cancel()
                    for t in (compile_task, watch_task):
                        try:
                            await t
                        except asyncio.CancelledError:
                            pass

        app = Starlette(
            lifespan=lifespan,
            routes=[
                Route("/visualizer", endpoint=serve_visualizer),
                Mount("/static", app=StaticFiles(directory="/app/static")),
                Mount("/", app=mcp_app),
            ],
        )
        uvicorn.run(app, host="0.0.0.0", port=port, log_level="error")

    try:
        if transport in ["http", "sse"]:
            logger.info("Starting ConnectWikiMCP v2.0 in HTTP mode (Port: %d)", port)
            run_http()
        else:
            logger.info("Starting ConnectWikiMCP v2.0 in STDIO mode")
            mcp.run(transport="stdio")
    except KeyboardInterrupt:
        logger.info("Server shutting down...")
    finally:
        for handler in logging.root.handlers[:]:
            handler.close()
            logging.root.removeHandler(handler)


if __name__ == "__main__":
    main()