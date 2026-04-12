import logging
import json
from mcp.server.fastmcp import FastMCP
from config import config_manager
from wiki_manager import wiki_manager
from llm_client import llm_client

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("connect-wiki-mcp")

# Initialize FastMCP server
mcp = FastMCP("ConnectWikiMCP")

def _log(query: str, tool: str, outcome: str):
    """Helper to log internal intents."""
    wiki_manager.log_intent(query, tool, outcome)

@mcp.tool()
async def FetchWikiPage(name: str) -> str:
    """
    Read a finalized Wiki page content.
    위키 페이지의 내용을 읽어옵니다. (예: "프로젝트A 읽어줘", "내용 조회")
    """
    page = wiki_manager.read_page(name)
    if not page:
        _log(f"Fetch page '{name}'", "FetchWikiPage", "Failed: Not found")
        return f"Page '{name}' not found."
    _log(f"Fetch page '{name}'", "FetchWikiPage", "Success")
    return page.content

@mcp.tool()
async def SaveWikiContent(name: str, content: str) -> str:
    """
    Create or update a structured Wiki page.
    위키 페이지를 생성하거나 수정합니다. 지식을 정리하여 저장할 때 사용합니다.
    """
    wiki_manager.write_page(name, content)
    _log(f"Save page '{name}'", "SaveWikiContent", "Success")
    return f"Page '{name}' saved successfully."

@mcp.tool()
async def ListAllKnowledge() -> str:
    """
    List all finalized Wiki nodes/pages.
    현재 위키에 정리된 모든 지식 목록을 확인합니다.
    """
    pages = wiki_manager.list_pages()
    return "\n".join(pages)

@mcp.tool()
async def SearchAcrossWiki(query: str) -> str:
    """
    Search for information across the entire Wiki knowledge base.
    위키 전체에서 특정 키워드나 내용을 검색합니다. (예: "A에 대해 찾아봐")
    """
    results = wiki_manager.search_wiki(query)
    _log(f"Search for '{query}'", "SearchAcrossWiki", f"Success: {len(results)} matches")
    if not results:
        return "No results found."
    
    text_results = []
    for r in results:
        preview = r.content[:200] + "..." if len(r.content) > 200 else r.content
        text_results.append(f"## {r.name}\n{preview}")
        
    return "\n\n".join(text_results)

@mcp.tool()
async def ExploreConnections(name: str) -> str:
    """
    Discover which pages reference or link to the specified topic (Backlinks).
    현재 주제를 언급하거나 연결된 다른 지식들(백링크)을 탐색합니다. (예: "뭐랑 연결돼있어?")
    """
    backlinks = wiki_manager.get_backlinks(name)
    _log(f"Explore connections for '{name}'", "ExploreConnections", f"Success: {len(backlinks)} found")
    if not backlinks:
        return f"No connections found for '{name}'."
    return f"Resources linking to '{name}':\n" + "\n".join(backlinks)

@mcp.tool()
async def AnalyzeKnowledgeGraph() -> str:
    """
    Retrieve the full relationship map of the knowledge base.
    전체 지식의 연결망(그래프) 구조를 분석하여 반환합니다.
    """
    graph = wiki_manager.get_graph_data()
    return json.dumps(graph, indent=2)

@mcp.tool()
async def CaptureQuickNote(name: str, content: str) -> str:
    """
    Quickly save unprocessed thoughts or raw information for later.
    나중에 정리할 아이디어나 날것의 정보를 빠르게 메모로 남깁니다. (예: "메모해둬", "이거 기록해")
    """
    wiki_manager.ingest_raw(name, content)
    _log(f"Capture note '{name}'", "CaptureQuickNote", "Success")
    return "Quick note captured successfully."

@mcp.tool()
async def AccessOriginalSource(path: str) -> str:
    """
    Read original notes or converted source documents (PDF, Word, etc.).
    아직 정제되지 않은 원본 문서나 메모 내용을 읽어옵니다.
    """
    content = await wiki_manager.read_raw(path)
    if content is None:
        return "Source file not found."
    return content

@mcp.tool()
async def SyncDocuments() -> str:
    """
    Synchronize and convert all new source files to readable Markdown.
    새로 추가된 문서(PDF, Docx 등)를 AI가 읽을 수 있도록 동기화하고 변환합니다.
    """
    status = wiki_manager.sync_raw_folder()
    return f"Sync complete: {status['converted']} files prepared, {status['skipped']} already up-to-date."

@mcp.tool()
async def SynthesizeKnowledge(raw_filename: str, target_page_name: str) -> str:
    """
    Use autonomous intelligence to compile raw notes into a formal Wiki page.
    원본 메모의 파편화된 정보를 분석하여 완성도 높은 위키 페이지로 합성/요약합니다. (예: "정리해줘", "합쳐줘")
    """
    raw_content = await wiki_manager.read_raw(raw_filename)
    if not raw_content:
        return "Source info not found."
    
    compiled = await llm_client.generate_wiki_page(raw_content)
    wiki_manager.write_page(target_page_name, compiled)
    _log(f"Synthesize '{raw_filename}' to '{target_page_name}'", "SynthesizeKnowledge", "Success")
    return f"Knowledge synthesized into '{target_page_name}'."

@mcp.tool()
async def OrganizeByTag(tag: str) -> str:
    """
    Find and group all notes associated with a specific hashtag.
    특정 태그(#)가 달린 모든 메모를 찾아 그룹화합니다. (예: "프로젝트A 태그된거 다 보여줘")
    """
    files = wiki_manager.get_tagged_raw_files(tag)
    _log(f"Organize by tag '{tag}'", "OrganizeByTag", f"Success: {len(files)} files found")
    if not files:
        return f"No material found with tag #{tag}."
    return f"Found {len(files)} items tagged with #{tag}:\n" + "\n".join(files)

@mcp.tool()
async def EvolutionAudit() -> str:
    """
    Analyze recent intent logs to identify user patterns and preferences.
    최근 사용 기록을 분석하여 사용자가 자주 사용하는 표현이나 선호하는 작업 방식을 추출합니다.
    """
    logs = wiki_manager.read_intent_logs(100)
    if not logs:
        return "No recent logs to analyze."
    return json.dumps(logs, indent=2, ensure_ascii=False)

@mcp.tool()
async def ConfigureSettings(
    wiki_root_path: str = None,
    local_llm_type: str = None,
    local_llm_api_url: str = None,
    local_llm_model: str = None,
    local_llm_api_key: str = None,
    mcp_port: int = None
) -> str:
    """Update system behavior and connection settings."""
    updates = {}
    if wiki_root_path: updates["wiki_root_path"] = wiki_root_path
    if local_llm_type: updates["local_llm_type"] = local_llm_type
    if local_llm_api_url: updates["local_llm_api_url"] = local_llm_api_url
    if local_llm_model: updates["local_llm_model"] = local_llm_model
    if local_llm_api_key: updates["local_llm_api_key"] = local_llm_api_key
    if mcp_port: updates["mcp_port"] = mcp_port
    
    config_manager.update_config(updates)
    return "Settings updated."

# --- Smart AI Workflows (Prompts) ---

@mcp.prompt()
def AutomatedCompilation(keyword: str) -> str:
    """Initiates an automated journey to synthesize knowledge for a specific topic."""
    return f"""
Identity: You are a professional Knowledge Architect.
Goal: Completely synthesize or update a formal Wiki page for the topic: "{keyword}".

Instructions:
0. MUST Read 'System/Intelligence' using 'FetchWikiPage' to learn the user's latest preferences and mapping rules.
1. Search for ANY existing data using 'SearchAcrossWiki' and 'ListAllKnowledge'.
2. Use 'OrganizeByTag' with "{keyword}" to find fresh, unorganized notes.
3. Read all identified sources using 'AccessOriginalSource' and 'FetchWikiPage'.
4. Critically synthesize the disparate information into a cohesive, perfectly structured Markdown entry.
5. Save your masterpiece using 'SaveWikiContent'.

Tone: Expert, organized, and proactive. Use [[WikiLinks]] for cross-referencing.
"""

@mcp.prompt()
def EvolveSystemIntelligence() -> str:
    """Triggers a self-improvement cycle by analyzing intent logs and updating the Intelligence manual."""
    return """
Identity: You are a System Growth Analyst.
Goal: Analyze user patterns and update 'System/Intelligence.md' to make the system smarter.

Instructions:
1. Use 'EvolutionAudit' to retrieve the latest user intent logs.
2. Read the current 'System/Intelligence' page using 'FetchWikiPage'.
3. Identify:
   - Frequent keywords the user uses (e.g., "정리해", "마법사", "요약").
   - Success/Failure patterns in tool selection.
   - User's preferred writing style or structure.
4. Update 'System/Intelligence' with NEW insights using 'SaveWikiContent'.
   - Add a 'Preferred Mappings' section.
   - Refine the 'Behavioral Rules'.
5. Report back what you learned and how the system has evolved.

Be statistical and precise. The goal is recursion: the system gets better at understanding the user with every audit.
"""

def main():
    import os
    import threading
    config_manager.initialize()
    
    transport = os.getenv("MCP_TRANSPORT", "stdio").lower()
    port = config_manager.get_config().mcp_port
    logger.info(f"DEBUG: Selected Transport = {transport}")
    logger.info(f"DEBUG: Selected Port = {port}")

    def run_sse():
        logger.info(f"Starting ConnectWikiMCP SSE background server on port {port}")
        import uvicorn
        app = mcp.sse_app()
        uvicorn.run(app, host="0.0.0.0", port=port, log_level="error")

    if transport == "hybrid":
        logger.info("Starting ConnectWikiMCP in HYBRID mode (STDIO + SSE)")
        # Start SSE in a background thread
        sse_thread = threading.Thread(target=run_sse, daemon=True)
        sse_thread.start()
        # Run STDIO in the main thread
        mcp.run(transport="stdio")
    elif transport == "sse":
        logger.info(f"Starting ConnectWikiMCP in SSE mode on port {port}")
        import uvicorn
        app = mcp.sse_app()
        uvicorn.run(app, host="0.0.0.0", port=port)
    else:
        logger.info("Starting ConnectWikiMCP in STDIO mode")
        mcp.run(transport="stdio")

if __name__ == "__main__":
    main()
