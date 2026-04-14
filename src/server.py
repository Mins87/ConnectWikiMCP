"""ConnectWikiMCP v2.0 — AI Long-term Memory Engine.

Exposes exactly 4 MCP tools:
  - Write: Store information (text or URL) into raw sources
  - Read:  Retrieve compiled wiki pages
  - SystemStatus: View system health and visualizer link
  - ConfigureSettings: Update runtime configuration
"""
from __future__ import annotations

import asyncio
import contextlib
import json
import logging
import os
import re
import sys
import socket
from datetime import datetime
from typing import Any, Optional
from pathlib import Path
from contextlib import asynccontextmanager

from mcp.server.fastmcp import FastMCP

# New Architecture Imports
from config.config import config_manager
from managers.raw_manager import RawManager
from managers.transform_manager import TransformManager
from managers.hierarchy_manager import HierarchyManager
from managers.maintenance_manager import maintenance_manager
from watchers.antigravity import AntigravityWatcher

logger = logging.getLogger("connect-wiki.server")

mcp = FastMCP("ConnectWikiMCP")

def is_port_in_use(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(("127.0.0.1", port)) == 0

# ── Core Tools ───────────────────────────────────────────────

@mcp.tool()
async def Write(input: str, name: Optional[str] = None) -> str:
    """Store information into the knowledge base for processing.
    Accepts raw text or a URL. 
    """
    if not raw_manager:
        return "Error: RawManager not initialized."

    input_stripped = input.strip()

    # ── URL detection ──
    if re.match(r"https?://", input_stripped):
        return await _ingest_url(input_stripped, name)

    # ── Raw text / memo ──
    note_name = name or f"memo_{datetime.now().strftime('%Y%h%d_%H%M%S')}"
    safe_name = re.sub(r"[^\w\s-]", "", note_name)
    safe_name = re.sub(r"[\s]+", "_", safe_name).strip("_")

    timestamp = datetime.now().strftime("%Y-%m-%dT%H-%M-%S")
    filename = f"{timestamp}-{safe_name}.md"
    
    # Corrected: Use raw_manager's structure instead of legacy wiki_manager
    filepath = raw_manager.raw_dir / "memos" / filename
    filepath.parent.mkdir(parents=True, exist_ok=True)
    filepath.write_text(f"# {note_name}\n\n{input_stripped}", encoding="utf-8")

    _log_intent("Write", "Success", {"name": note_name, "type": "memo", "size": len(input_stripped)})
    return f"Memo '{note_name}' saved to raw/memos. It will be processed by the 3-layer pipeline."

async def _ingest_url(url: str, name: str | None) -> str:
    """Extract content from a URL and save to raw/files/."""
    yt_pattern = re.compile(r"(?:youtube\.com/watch\?v=|youtu\.be/)([\w-]+)")
    yt_match = yt_pattern.search(url)

    if yt_match:
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

    if raw_manager:
        safe_name = re.sub(r"[^\w\s-]", "", note_name)
        safe_name = re.sub(r"[\s]+", "_", safe_name).strip("_")
        timestamp = datetime.now().strftime("%Y-%m-%dT%H-%M-%S")
        filename = f"{timestamp}-{safe_name}.md"
        filepath = raw_manager.raw_dir / "files" / filename
        filepath.parent.mkdir(parents=True, exist_ok=True)
        filepath.write_text(content, encoding="utf-8")
        
        _log_intent("Write", "Success", {"name": note_name, "type": "url", "url": url})
        return f"Captured '{url}' as '{note_name}'. It will be processed by the 3-layer pipeline."
    return "Error: RawManager not initialized."

@mcp.tool()
async def Read(name: str) -> str:
    """Read a compiled wiki page from the knowledge base."""
    if not hierarchy_manager:
        return "Error: HierarchyManager not initialized."

    if name == "_list":
        pages = hierarchy_manager.list_pages()
        if not pages:
            return "No pages in the wiki yet."
        _log_intent("Read", "Success", {"type": "list", "count": len(pages)})
        return "\n".join(pages)

    if name == "_index":
        page = hierarchy_manager.read_page("index")
        if not page:
            content = hierarchy_manager.rebuild_index()
            _log_intent("Read", "Success", {"type": "index", "generated": True})
            return content
        _log_intent("Read", "Success", {"type": "index"})
        return page["content"]

    page = hierarchy_manager.read_page(name)
    if not page:
        return f"Page '{name}' not found. Use Read('_list') to see available pages."
    _log_intent("Read", "Success", {"name": name})
    return page["content"]

@mcp.tool()
async def SystemStatus() -> str:
    """View system health and unified watcher status."""
    if not hierarchy_manager or not raw_manager:
        return "Error: Managers not initialized."

    cfg = config_manager.get_config()
    pages = hierarchy_manager.list_pages()
    graph = hierarchy_manager.get_graph_data()
    
    # Count pending raw files via RawManager's knowledge
    pending = len(raw_manager.list_raw())

    status = (
        "## 📊 ConnectWikiMCP Status\n\n"
        f"- **Wiki Pages**: {len(pages)}\n"
        f"- **Graph Nodes**: {len(graph['nodes'])}\n"
        f"- **Graph Links**: {len(graph['links'])}\n"
        f"- **Raw Queue**: {pending} file(s) in staging\n"
        f"- **LLM Backend**: {cfg.local_llm_type} ({cfg.local_llm_model})\n"
        f"- **Antigravity Watch**: {'Enabled' if cfg.brain_watch_path else 'Disabled'}\n"
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
    """Update runtime configuration parameters."""
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

def _log_intent(tool_name: str, outcome: str, metadata: dict[str, Any] | None = None) -> None:
    """Lightweight intent logging."""
    try:
        log_dir = Path(config_manager.get_config().wiki_root_path) / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        entry = {
            "timestamp": datetime.now().isoformat(),
            "tool": tool_name,
            "outcome": outcome,
            "metadata": metadata or {},
        }
        log_file = log_dir / "intent_history.jsonl"
        with log_file.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except Exception:
        pass

# ── Managed 3-Layer Pipeline & Orchestration ─────────────────

raw_manager: RawManager = None
transform_manager: TransformManager = None
hierarchy_manager: HierarchyManager = None

transform_queue: asyncio.Queue[Path] = asyncio.Queue()
hierarchy_queue: asyncio.Queue[Path] = asyncio.Queue()

async def _orchestrated_maintenance_scheduler() -> None:
    """Unified background task: Maintenance + Watchers."""
    cfg = config_manager.get_config()
    interval = cfg.antigravity_watch_interval_minutes

    if interval <= 0:
        # Maintenance still runs but at a fixed interval if watching is disabled
        interval = 30

    logger.info("Unified Maintenance Scheduler started: cycle every %d min.", interval)
    # Initial delay to let server settle
    await asyncio.sleep(10)

    while True:
        try:
            if hierarchy_manager:
                # Execute Maintenance + All Registered Watchers
                await maintenance_manager.perform_maintenance(hierarchy_manager)
        except Exception:
            logger.exception("Unified maintenance cycle failed")
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
        from starlette.applications import Starlette
        from starlette.routing import Mount, Route
        from starlette.responses import HTMLResponse
        from starlette.staticfiles import StaticFiles

        if is_port_in_use(port):
            logger.error("Port %d is already in use. Cannot start HTTP server.", port)
            return

        mcp_app = mcp.streamable_http_app()

        async def serve_visualizer(request):
            # Point to the physical file generated by MaintenanceManager
            viz_file = Path(config_manager.get_config().wiki_root_path) / "visualizer.html"
            if viz_file.exists():
                return HTMLResponse(content=viz_file.read_text(encoding="utf-8"))
            return HTMLResponse(content="<html><body><h1>Visualizer not ready yet.</h1></body></html>")

        @asynccontextmanager
        async def lifespan(app):
            async with mcp.session_manager.run():
                global raw_manager, transform_manager, hierarchy_manager
                
                # 1. Initialize Specialized Managers
                root = Path(config_manager.get_config().wiki_root_path)
                raw_manager = RawManager(root / "raw")
                transform_manager = TransformManager(root / "raw", root / "transformed")
                hierarchy_manager = HierarchyManager(root / "pages", root / "transformed")
                
                # 2. Register Watchers (Dynamic Plugin Registry)
                ag_watcher = AntigravityWatcher()
                maintenance_manager.register_watcher(ag_watcher)
                
                # 3. Start Pipeline internal workers
                raw_task = asyncio.create_task(raw_manager.run_worker(transform_queue, transform_manager))
                transform_task = asyncio.create_task(transform_manager.run_worker(transform_queue, hierarchy_queue))
                hierarchy_task = asyncio.create_task(hierarchy_manager.run_worker(hierarchy_queue))
                
                # 4. Start Unified Maintenance Scheduler
                maint_task = asyncio.create_task(_orchestrated_maintenance_scheduler())
                
                try:
                    yield
                finally:
                    for t in (raw_task, transform_task, hierarchy_task, maint_task):
                        t.cancel()
                        with contextlib.suppress(asyncio.CancelledError):
                            await t

        app = Starlette(
            lifespan=lifespan,
            routes=[
                Route("/visualizer", endpoint=serve_visualizer),
                Mount("/static", app=StaticFiles(directory=str(Path(__file__).parent / "templates"))),
                Mount("/", app=mcp_app),
            ],
        )
        uvicorn.run(app, host="0.0.0.0", port=port, log_level="error")

    try:
        if transport in ["http", "sse"]:
            logger.info("Starting ConnectWikiMCP v2.1 in HTTP mode (Port: %d)", port)
            run_http()
        else:
            logger.info("Starting ConnectWikiMCP v2.1 in STDIO mode")
            mcp.run(transport="stdio")
    except KeyboardInterrupt:
        logger.info("Server shutting down...")
    finally:
        for handler in logging.root.handlers[:]:
            handler.close()
            logging.root.removeHandler(handler)

if __name__ == "__main__":
    main()