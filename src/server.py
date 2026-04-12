from __future__ import annotations

import functools
import inspect
import json
import logging
import os
import sys
import threading
import contextlib
import socket
from typing import Any, Callable

from mcp.server.fastmcp import FastMCP

from config import config_manager

logger = logging.getLogger("connect-wiki.server")

mcp = FastMCP("ConnectWikiMCP")
REDACT_KEYS = {"local_llm_api_key", "api_key", "authorization", "token", "password", "secret"}


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


def autonomous_action(func: Callable[..., Any]) -> Callable[..., Any]:
    @functools.wraps(func)
    async def wrapper(*args: Any, **kwargs: Any) -> Any:
        from maintenance_manager import maintenance_manager
        from wiki_manager import wiki_manager

        tool_name = func.__name__
        metadata = _sanitize_bound_args(func, args, kwargs)
        query = f"Executed {tool_name}"

        try:
            # Shield stdout during tool execution to prevent stream corruption
            with contextlib.redirect_stdout(sys.stderr):
                result = await func(*args, **kwargs)
            wiki_manager.log_intent(query, tool_name, "Success", metadata)
            await maintenance_manager.perform_maintenance(tool_name, "Success", metadata)
            return result
        except Exception as exc:
            outcome = f"Failed: {exc}"
            wiki_manager.log_intent(query, tool_name, outcome, metadata)
            await maintenance_manager.perform_maintenance(tool_name, outcome, metadata)
            raise

    return wrapper


@mcp.tool()
@autonomous_action
async def FetchWikiPage(name: str) -> str:
    from wiki_manager import wiki_manager

    page = wiki_manager.read_page(name)
    if not page:
        return f"Page '{name}' not found."
    return page.content


@mcp.tool()
@autonomous_action
async def SaveWikiContent(name: str, content: str) -> str:
    from wiki_manager import wiki_manager

    wiki_manager.write_page(name, content)
    return f"Page '{name}' saved successfully."


@mcp.tool()
@autonomous_action
async def ListAllKnowledge() -> str:
    from wiki_manager import wiki_manager

    return "\n".join(wiki_manager.list_pages())


@mcp.tool()
@autonomous_action
async def SearchAcrossWiki(query: str) -> str:
    from wiki_manager import wiki_manager

    results = wiki_manager.search_wiki(query)
    if not results:
        return "No results found."

    chunks = []
    for page in results:
        preview = page.content[:200] + "..." if len(page.content) > 200 else page.content
        chunks.append(f"## {page.name}\n{preview}")
    return "\n\n".join(chunks)


@mcp.tool()
@autonomous_action
async def ExploreConnections(name: str) -> str:
    from wiki_manager import wiki_manager

    backlinks = wiki_manager.get_backlinks(name)
    if not backlinks:
        return f"No connections found for '{name}'."
    return f"Resources linking to '{name}':\n" + "\n".join(backlinks)


@mcp.tool()
@autonomous_action
async def AnalyzeKnowledgeGraph() -> str:
    from wiki_manager import wiki_manager

    return json.dumps(wiki_manager.get_graph_data(), indent=2, ensure_ascii=False)


@mcp.tool()
@autonomous_action
async def CaptureQuickNote(name: str, content: str) -> str:
    from wiki_manager import wiki_manager

    filename = wiki_manager.ingest_raw(name, content)
    return f"Quick note captured successfully as '{filename}'."


@mcp.tool()
@autonomous_action
async def AccessOriginalSource(path: str) -> str:
    from wiki_manager import wiki_manager

    content = await wiki_manager.read_raw(path)
    if content is None:
        return "Source file not found."
    return content


@mcp.tool()
@autonomous_action
async def SyncDocuments() -> str:
    from wiki_manager import wiki_manager

    status = wiki_manager.sync_raw_folder()
    return f"Sync complete: {status['converted']} files prepared, {status['skipped']} already up-to-date."


@mcp.tool()
@autonomous_action
async def SynthesizeKnowledge(raw_filename: str, target_page_name: str) -> str:
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
    from wiki_manager import wiki_manager

    files = wiki_manager.get_tagged_raw_files(tag)
    if not files:
        return f"No material found with tag #{tag}."
    return f"Found {len(files)} items tagged with #{tag}:\n" + "\n".join(files)


@mcp.tool()
@autonomous_action
async def EvolutionAudit() -> str:
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
async def ResetSystemDocs() -> str:
    from maintenance_manager import maintenance_manager

    synced = maintenance_manager.bootstrap_system_docs(overwrite=True)
    return f"System documentation synchronized: {synced} file(s) updated."


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


def main() -> None:
    if hasattr(sys.stdin, "reconfigure"):
        sys.stdin.reconfigure(encoding="utf-8-sig")
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(line_buffering=True, write_through=True)

    config_manager.initialize()
    transport = os.getenv("MCP_TRANSPORT", "http").lower()
    port = config_manager.get_config().mcp_port

    def run_http() -> None:
        import uvicorn

        if is_port_in_use(port):
            logger.error("Port %d is already in use. Cannot start HTTP server.", port)
            return

        app = mcp.streamable_http_app()
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