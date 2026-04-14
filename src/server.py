from __future__ import annotations

import asyncio
import contextlib
import functools
import inspect
import json
import logging
import os
import socket
import sys
import threading
from datetime import datetime
from typing import Any, Callable

from mcp.server.fastmcp import FastMCP

from config import config_manager

logger = logging.getLogger("connect-wiki.server")

mcp = FastMCP("ConnectWikiMCP")
REDACT_KEYS = {"local_llm_api_key", "api_key", "authorization", "token", "password", "secret"}

# Tools that only read data — skip maintenance I/O for these
READ_ONLY_TOOLS = {
    "ListAllKnowledge",
    "FetchWikiPage",
    "SearchAcrossWiki",
    "ExploreConnections",
    "AnalyzeKnowledgeGraph",
    "RenderKnowledgeGraph",
    "EvolutionAudit",
    "AccessOriginalSource",
    "OrganizeByTag",
    "GetCompressedContext",
}

# Response auto-compression: local LLM compresses large tool responses
# before they reach the external LLM, saving expensive tokens.
COMPRESS_THRESHOLD = 1500  # characters — compress responses longer than this
COMPRESS_EXCLUDE = {
    "FetchWikiPage",       # users may need exact content
    "EvolutionAudit",      # raw log data should be intact
    "AnalyzeKnowledgeGraph",  # structured JSON — compression may break it
    "AccessOriginalSource",   # raw source should be intact
}


def _sanitize_bound_args(func: Callable[..., Any], args: tuple[Any, ...], kwargs: dict[str, Any]) -> dict[str, Any]:
    bound = inspect.signature(func).bind_partial(*args, **kwargs)
    safe: dict[str, Any] = {}
    for key, value in bound.arguments.items():
        if key.lower() in REDACT_KEYS:
            safe[key] = "***REDACTED***"
        elif isinstance(value, str) and len(value) > 500:
            safe[key] = value[:500] + "..."
        else:
            safe[key] = value
    return safe


def is_port_in_use(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(("0.0.0.0", port)) == 0


async def _compress_response(tool_name: str, response: str) -> str:
    """Use local LLM to compress a verbose tool response.

    Falls back to the original response if the LLM is unavailable or
    the compressed version is not significantly shorter.
    """
    try:
        from llm_client import llm_client

        prompt = (
            "Compress this tool response while preserving ALL key information.\n"
            "Remove redundancy, boilerplate, and verbose formatting. Keep data intact.\n\n"
            f"TOOL: {tool_name}\n"
            f"RESPONSE ({len(response)} chars):\n"
            f"{response[:4000]}"
        )
        compressed = await llm_client.complete_text(
            prompt,
            system_prompt="You are a lossless text compressor. Preserve all facts. Remove only noise.",
        )
        # Only use compressed version if it's actually shorter
        if compressed and len(compressed) < len(response) * 0.8:
            return f"{compressed}\n\n> \U0001f4e6 Compressed: {len(response)} → {len(compressed)} chars"
    except Exception:
        pass  # LLM unavailable — return original
    return response


def autonomous_action(func: Callable[..., Any]) -> Callable[..., Any]:
    @functools.wraps(func)
    async def wrapper(*args: Any, **kwargs: Any) -> Any:
        from maintenance_manager import maintenance_manager
        from wiki_manager import wiki_manager

        tool_name = func.__name__
        is_read_only = tool_name in READ_ONLY_TOOLS
        metadata = _sanitize_bound_args(func, args, kwargs)
        query = f"Executed {tool_name}"

        try:
            # Shield stdout during tool execution to prevent stream corruption
            with contextlib.redirect_stdout(sys.stderr):
                result = await func(*args, **kwargs)

            # Auto-compress large responses using local LLM (free tokens)
            if (
                isinstance(result, str)
                and len(result) > COMPRESS_THRESHOLD
                and tool_name not in COMPRESS_EXCLUDE
            ):
                result = await _compress_response(tool_name, result)

            wiki_manager.log_intent(query, tool_name, "Success", metadata)
            if not is_read_only:
                await maintenance_manager.perform_maintenance(tool_name, "Success", metadata)
            return result
        except Exception as exc:
            outcome = f"Failed: {exc}"
            wiki_manager.log_intent(query, tool_name, outcome, metadata)
            if not is_read_only:
                await maintenance_manager.perform_maintenance(tool_name, outcome, metadata)
            raise

    return wrapper


@mcp.tool()
@autonomous_action
async def FetchWikiPage(name: str) -> str:
    """Read the raw markdown content of a specific wiki page.

    Args:
        name: The exact title or path of the page to retrieve.
    """
    from wiki_manager import wiki_manager

    page = wiki_manager.read_page(name)
    if not page:
        return f"Page '{name}' not found."
    return page.content


@mcp.tool()
@autonomous_action
async def SaveWikiContent(name: str, content: str) -> str:
    """Create a new wiki page or update an existing one with markdown content.

    Args:
        name: The unique identifier for the page.
        content: The full markdown content of the page.
    """
    from wiki_manager import wiki_manager

    wiki_manager.write_page(name, content)
    return f"Page '{name}' saved successfully."


@mcp.tool()
@autonomous_action
async def ListAllKnowledge() -> str:
    """Return a flat list of all existing wiki page titles in the system.
    """
    from wiki_manager import wiki_manager

    return "\n".join(wiki_manager.list_pages())


@mcp.tool()
@autonomous_action
async def SearchAcrossWiki(query: str) -> str:
    """Perform a semantic search across the wiki to find relevant context and summaries.

    Args:
        query: The natural language search term or question.
    """
    from digest_cache import digest_cache
    from wiki_manager import wiki_manager

    results = await wiki_manager.search_wiki_semantic(query)
    if not results:
        return "No results found."

    chunks = []
    for page in results:
        digest = await digest_cache.ensure_digest(page.name, page.content)
        summary = digest.get("summary", page.content[:100])
        tags = " ".join(f"#{t}" for t in digest.get("tags", []))
        entry = f"- **{page.name}**: {summary}"
        if tags:
            entry += f"  {tags}"
        chunks.append(entry)
    return "\n".join(chunks)


@mcp.tool()
@autonomous_action
async def RebuildSearchIndex() -> str:
    """Force a full rebuild of the semantic search vector index.
    Run this after bulk-importing pages or if search results seem stale."""
    from embedding_manager import embedding_manager
    from wiki_manager import wiki_manager

    pages = {
        name: (page.content if (page := wiki_manager.read_page(name)) else "")
        for name in wiki_manager.list_pages()
    }
    indexed = await embedding_manager.rebuild_index(pages)
    return f"Search index rebuilt: {indexed} pages indexed."


@mcp.tool()
@autonomous_action
async def ExploreConnections(name: str) -> str:
    """Identify all pages that contain links pointing to the specified page (backlinks).

    Args:
        name: The name of the target page to analyze connections for.
    """
    from wiki_manager import wiki_manager

    backlinks = wiki_manager.get_backlinks(name)
    if not backlinks:
        return f"No connections found for '{name}'."
    return f"Resources linking to '{name}':\n" + "\n".join(backlinks)


@mcp.tool()
@autonomous_action
async def AnalyzeKnowledgeGraph() -> str:
    """Provide a structured JSON representation of the entire knowledge graph (nodes/edges).
    """
    from wiki_manager import wiki_manager

    return json.dumps(wiki_manager.get_graph_data(), indent=2, ensure_ascii=False)


@mcp.tool()
@autonomous_action
async def CaptureQuickNote(name: str, content: str) -> str:
    """Store raw text or ideas into the 'raw' staging area for later wiki integration.

    Args:
        name: A title or identifier for the raw note.
        content: The text to be captured.
    """
    from wiki_manager import wiki_manager

    filename = wiki_manager.ingest_raw(name, content)
    return f"Quick note captured successfully as '{filename}'."


@mcp.tool()
@autonomous_action
async def CaptureFromURL(url: str, name: str | None = None) -> str:
    """Capture content from a web page or YouTube video URL into the raw folder.
    
    - For regular URLs: extracts clean article text via trafilatura.
    - For YouTube URLs: fetches the video transcript.
    - Saves the result as a raw note for later synthesis with SynthesizeKnowledge.
    """
    import re as _re

    yt_pattern = _re.compile(r"(?:youtube\.com/watch\?v=|youtu\.be/)([\w-]+)")
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
            source_header = f"# {note_name}\n\n> Source: {url}\n\n"
            content = source_header + raw_text
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
            source_header = f"# {note_name}\n\n> Source: {url}\n\n"
            content = source_header + raw_text
        except Exception as exc:
            return f"Failed to capture URL: {exc}"

    from wiki_manager import wiki_manager
    filename = wiki_manager.ingest_raw(note_name, content)
    return f"Captured '{url}' as raw note '{filename}'. Use SynthesizeKnowledge to compile it into the wiki."


@mcp.tool()
@autonomous_action
async def AccessOriginalSource(path: str) -> str:
    """Retrieve the full raw content of a file located in the staging 'raw' folder.

    Args:
        path: The relative path or filename within the raw directory.
    """
    from wiki_manager import wiki_manager

    content = await wiki_manager.read_raw(path)
    if content is None:
        return "Source file not found."
    return content


@mcp.tool()
@autonomous_action
async def SyncDocuments() -> str:
    """Trigger a synchronization of the 'raw' folder to prepare documents for synthesis.
    """
    from wiki_manager import wiki_manager

    status = wiki_manager.sync_raw_folder()
    return f"Sync complete: {status['converted']} files prepared, {status['skipped']} already up-to-date."


@mcp.tool()
@autonomous_action
async def SynthesizeKnowledge(raw_filename: str, target_page_name: str) -> str:
    """Transform raw staged information into a structured wiki page using local LLM synthesis.

    Args:
        raw_filename: The name of the source file in the raw folder.
        target_page_name: The desired title for the synthesized wiki page.
    """
    from llm_client import llm_client
    from wiki_manager import wiki_manager

    raw_content = await wiki_manager.read_raw(raw_filename)
    if not raw_content:
        return "Source info not found."

    compiled = await llm_client.generate_wiki_page(raw_content)
    wiki_manager.write_page(target_page_name, compiled)
    return f"Knowledge synthesized into '{target_page_name}'."


@mcp.tool()
@autonomous_action
async def OrganizeByTag(tag: str) -> str:
    """Filter raw staged material by a specific tag to discover related sources.

    Args:
        tag: The tag to filter by (without the # symbol).
    """
    from wiki_manager import wiki_manager

    files = wiki_manager.get_tagged_raw_files(tag)
    if not files:
        return f"No material found with tag #{tag}."
    return f"Found {len(files)} items tagged with #{tag}:\n" + "\n".join(files)


@mcp.tool()
@autonomous_action
async def EvolutionAudit() -> str:
    """Expose recent system intent logs to analyze tool usage and evolution trends.
    """
    from wiki_manager import wiki_manager

    logs = wiki_manager.read_intent_logs(100)
    if not logs:
        return "No recent logs to analyze."
    return json.dumps(logs, indent=2, ensure_ascii=False)


@mcp.tool()
@autonomous_action
async def ConfigureSettings(
    wiki_root_path: str | None = None,
    local_llm_type: str | None = None,
    local_llm_api_url: str | None = None,
    local_llm_model: str | None = None,
    local_llm_api_key: str | None = None,
    mcp_port: int | None = None,
) -> str:
    """Update runtime configuration parameters for the ConnectWiki orchestration layer.

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


@mcp.tool()
@autonomous_action
async def RenderKnowledgeGraph() -> str:
    """Generate an interactive HTML visualization of the wiki knowledge graph.
    The visualizer will be hosted at http://localhost:{port}/visualizer"""
    from config import config_manager
    port = config_manager.get_config().mcp_port
    
    return f"Knowledge graph is ready! View it at: http://localhost:{port}/visualizer"


@mcp.tool()
@autonomous_action
async def ResetSystemDocs() -> str:
    """Force an update and reset of system-level documentation pages within the wiki.
    """
    from maintenance_manager import maintenance_manager

    synced = maintenance_manager.bootstrap_system_docs(overwrite=True)
    return f"System documentation synchronized: {synced} file(s) updated."


@mcp.tool()
@autonomous_action
async def GetCompressedContext(
    query: str,
    max_pages: int = 5,
    instruction: str | None = None,
) -> str:
    """Get a compressed briefing on a topic, synthesized by the local LLM.

    Instead of reading multiple wiki pages yourself, let the internal LLM
    read them and provide a focused briefing. This saves significant tokens.

    Args:
        query: The topic or question to get context about
        max_pages: Maximum number of source pages to read (default: 5)
        instruction: Optional specific focus for the briefing
    """
    from wiki_manager import wiki_manager

    results = await wiki_manager.search_wiki_semantic(query, top_k=max_pages)
    if not results:
        return "No relevant context found in the wiki."

    # Local LLM reads ALL the raw content (free!)
    raw_context = "\n\n---\n\n".join(
        f"## {page.name}\n{page.content[:3000]}"
        for page in results
    )

    focus = instruction or f"the topic: {query}"
    prompt = (
        f"Read the following wiki pages and create a CONCISE briefing "
        f"focused on {focus}.\n\n"
        "Rules:\n"
        "- Maximum 300 words\n"
        "- Include only facts directly relevant to the focus\n"
        "- Cite page names in brackets [PageName] when referencing specific information\n"
        "- Use bullet points for key facts\n"
        "- Skip boilerplate, headers, and metadata\n\n"
        f"SOURCE PAGES ({len(results)} pages):\n"
        f"{raw_context}"
    )

    try:
        from llm_client import llm_client

        briefing = await llm_client.complete_text(
            prompt,
            system_prompt=(
                "You are a context compression engine. Be extremely concise. "
                "Every word must carry information."
            ),
        )
    except Exception:
        # Fallback: return digest summaries when LLM is unavailable
        from digest_cache import digest_cache

        chunks = []
        for page in results:
            digest = await digest_cache.ensure_digest(page.name, page.content)
            chunks.append(f"- **{page.name}**: {digest.get('summary', page.content[:100])}")
        briefing = "\n".join(chunks)

    return f"\U0001f4cb **Compressed Briefing** (from {len(results)} pages):\n\n{briefing}"


@mcp.tool()
@autonomous_action
async def CaptureReasoningTrace(
    session_id: str,
    reasoning_type: str,
    content: str,
    context_refs: list[str] | None = None,
) -> str:
    """Capture a step of LLM reasoning process for knowledge accumulation.

    Call this at key moments during your thinking process.
    The internal LLM will auto-distill verbose traces.

    Args:
        session_id: Unique session identifier (e.g. 'sess-2026-04-14-topic')
        reasoning_type: One of 'planning', 'analysis', 'decision', 'conclusion'
        content: The reasoning content to capture
        context_refs: Wiki pages referenced during this reasoning step
    """
    from wiki_manager import wiki_manager

    # Distill long reasoning with local LLM (free)
    compressed = content
    if len(content) > 300:
        try:
            from llm_client import llm_client

            compressed = await llm_client.complete_text(
                f"Distill this reasoning into 1-2 key sentences:\n\n{content[:2000]}",
                system_prompt="Extract only the essential insight. Maximum 2 sentences.",
            )
        except Exception:
            compressed = content[:300] + "..."

    trace = {
        "timestamp": datetime.now().isoformat(),
        "session_id": session_id,
        "type": reasoning_type,
        "content": compressed,
        "raw_length": len(content),
        "refs": context_refs or [],
    }

    log_dir = wiki_manager.logs_dir / "reasoning"
    log_dir.mkdir(parents=True, exist_ok=True)
    with (log_dir / f"{session_id}.jsonl").open("a", encoding="utf-8") as f:
        f.write(json.dumps(trace, ensure_ascii=False) + "\n")

    return f"Trace captured ({reasoning_type}): {len(content)} → {len(compressed)} chars"


@mcp.tool()
@autonomous_action
async def CaptureSessionSummary(
    session_id: str,
    topic: str,
    summary: str,
    key_decisions: list[str] | None = None,
    new_knowledge: str | None = None,
    tags: list[str] | None = None,
) -> str:
    """Distill a completed reasoning session into a wiki page.

    Call at the end of a significant analysis or problem-solving session.

    Args:
        session_id: The session identifier used in CaptureReasoningTrace
        topic: Short topic title for the session
        summary: Concise summary of the session findings
        key_decisions: List of key decisions made during the session
        new_knowledge: New knowledge discovered during the session
        tags: Categorization tags for the session
    """
    from wiki_manager import wiki_manager

    date_str = datetime.now().strftime("%Y-%m-%d")
    page_name = f"LLM/Sessions/{date_str}/{topic}"

    lines = [f"# {topic}", "", f"> Session: `{session_id}`", f"> Date: {date_str}", ""]

    if summary:
        lines += ["## Summary", summary, ""]
    if key_decisions:
        lines += ["## Key Decisions"]
        lines += [f"- {d}" for d in key_decisions]
        lines += [""]
    if new_knowledge:
        lines += ["## New Knowledge", new_knowledge, ""]
    if tags:
        lines += ["---", "**Tags**: " + " ".join(f"#{t}" for t in tags)]

    wiki_manager.write_page(page_name, "\n".join(lines))
    return f"Session summary saved to '{page_name}'"


@mcp.tool()
@autonomous_action
async def IngestConversations() -> str:
    """Scan the Antigravity brain directory for new conversation logs and
    auto-ingest them into the wiki as structured knowledge pages.

    Each conversation is distilled by the local LLM into a compact wiki page
    under ``Conversations/YYYY-MM-DD/TopicSlug``. Already-processed
    conversations are skipped automatically.
    """
    from conversation_watcher import conversation_watcher

    return await conversation_watcher.run_watch_cycle()


@mcp.tool()
@autonomous_action
async def WatcherStatus() -> str:
    """Return the current status of the conversation auto-capture watcher,
    including the number of processed and pending conversations.
    """
    from conversation_watcher import conversation_watcher

    status = conversation_watcher.get_status()
    lines = [
        "## Conversation Watcher Status",
        f"- **Enabled**: {status['enabled']}",
        f"- **Brain Path**: {status['brain_path']}",
        f"- **Processed**: {status['processed_count']} conversations",
        f"- **Pending**: {status['pending_count']} conversations",
    ]
    return "\n".join(lines)


@mcp.prompt()
def AutomatedCompilation(keyword: str) -> str:
    return f"""
Identity: You are a professional Knowledge Architect.
Goal: Completely synthesize or update a formal Wiki page for the topic: '{keyword}'.

Instructions:
0. Read 'System/Intelligence' with 'FetchWikiPage'.
1. Search existing data using 'SearchAcrossWiki' and 'ListAllKnowledge'.
2. Use 'OrganizeByTag' with '{keyword}' to find fresh notes.
3. Read sources using 'AccessOriginalSource' and 'FetchWikiPage'.
4. Synthesize them into a cohesive Markdown entry with [[WikiLinks]].
5. Save the result with 'SaveWikiContent'.
""".strip()


@mcp.prompt()
def EvolveSystemIntelligence() -> str:
    return """
Identity: You are a System Growth Analyst.
Goal: Analyze user patterns and update 'System/Intelligence.md'.

Instructions:
1. Use 'EvolutionAudit' to retrieve recent intent logs.
2. Read the current 'System/Intelligence' page using 'FetchWikiPage'.
3. Identify frequent keywords, tool success/failure patterns, and writing preferences.
4. Update 'System/Intelligence' with new insights using 'SaveWikiContent'.
5. Report what changed.
""".strip()


@mcp.prompt()
def ReasoningCaptureMode() -> str:
    return """
Identity: You are operating in Reasoning Capture Mode.
Goal: Actively log your thinking process into the wiki for future reference.

Protocol:
1. At the START of a complex task, call CaptureReasoningTrace with:
   - session_id: Generate a unique ID (e.g. "sess-YYYY-MM-DD-topic-slug")
   - reasoning_type: "planning"
   - content: Your initial analysis and approach

2. During ANALYSIS, call CaptureReasoningTrace with:
   - reasoning_type: "analysis"
   - content: Key findings, comparisons, and intermediate conclusions
   - context_refs: Wiki pages you referenced

3. At each DECISION point, call CaptureReasoningTrace with:
   - reasoning_type: "decision"
   - content: Options considered, trade-offs, and final choice

4. At the END of the session, call CaptureSessionSummary with:
   - A concise summary, key decisions list, and any new knowledge discovered

Token Optimization Tips:
- Use 'GetCompressedContext' instead of multiple 'FetchWikiPage' calls
- Read 'System/KnowledgeBriefing' for a quick wiki orientation
- Use 'SearchAcrossWiki' for efficient topic discovery (returns LLM summaries)

Rules:
- Keep traces concise (2-3 sentences each)
- Only capture SIGNIFICANT reasoning steps, not trivial operations
- Always include context_refs when you read from the wiki
""".strip()


def main() -> None:
    if hasattr(sys.stdin, "reconfigure"):
        sys.stdin.reconfigure(encoding="utf-8-sig")
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(line_buffering=True, write_through=True)

    config_manager.initialize()
    transport = os.getenv("MCP_TRANSPORT", "http").lower()
    cfg = config_manager.get_config()
    port = cfg.mcp_port

    async def _evolution_scheduler() -> None:
        interval_hours = cfg.evolution_interval_hours
        if interval_hours <= 0:
            logger.info("Evolution scheduler disabled (EVOLUTION_INTERVAL_HOURS=0).")
            return
        logger.info("Evolution scheduler started: runs every %dh.", interval_hours)
        await asyncio.sleep(interval_hours * 3600)   # first run is delayed
        while True:
            try:
                from maintenance_manager import maintenance_manager
                summary = await maintenance_manager.run_evolution_cycle()
                logger.info("Auto-evolution: %s", summary)
            except Exception:
                logger.exception("Evolution cycle failed")
            await asyncio.sleep(interval_hours * 3600)

    async def _conversation_watcher_scheduler() -> None:
        """Background task: periodically scan brain directory for new conversations."""
        interval_min = cfg.conversation_watch_interval_minutes
        brain_path = cfg.brain_watch_path.strip()
        if interval_min <= 0 or not brain_path:
            logger.info("Conversation watcher disabled (no BRAIN_WATCH_PATH or interval=0).")
            return
        logger.info(
            "Conversation watcher started: scanning '%s' every %d min.",
            brain_path, interval_min,
        )
        # Initial delay of 2 minutes to let the server fully initialize
        await asyncio.sleep(120)
        while True:
            try:
                from conversation_watcher import conversation_watcher
                summary = await conversation_watcher.run_watch_cycle()
                if "No new" not in summary:
                    logger.info("Conversation watcher: %s", summary)
            except Exception:
                logger.exception("Conversation watcher cycle failed")
            await asyncio.sleep(interval_min * 60)

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
        async def lifespan(app):  # type: ignore[type-arg]
            async with mcp.session_manager.run():
                evo_task = asyncio.create_task(_evolution_scheduler())
                watch_task = asyncio.create_task(_conversation_watcher_scheduler())
                try:
                    yield
                finally:
                    evo_task.cancel()
                    watch_task.cancel()
                    for t in (evo_task, watch_task):
                        try:
                            await t
                        except asyncio.CancelledError:
                            pass

        app = Starlette(
            lifespan=lifespan, 
            routes=[
                Route("/visualizer", endpoint=serve_visualizer),
                Mount("/static", app=StaticFiles(directory="/app/static")),
                Mount("/", app=mcp_app)
            ]
        )
        uvicorn.run(app, host="0.0.0.0", port=port, log_level="error")

    try:
        if transport in ["http", "sse"]:
            logger.info("Starting ConnectWikiMCP in Streamable HTTP mode (Port: %d)", port)
            run_http()
        else:
            logger.info("Starting ConnectWikiMCP in STDIO mode")
            mcp.run(transport="stdio")
    except KeyboardInterrupt:
        logger.info("Server shutting down...")
    finally:
        for handler in logging.root.handlers[:]:
            handler.close()
            logging.root.removeHandler(handler)


if __name__ == "__main__":
    main()