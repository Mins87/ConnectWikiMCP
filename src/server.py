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

@mcp.tool()
async def FetchWikiPage(name: str) -> str:
    """
    Read a finalized Wiki page content.
    위키 페이지의 내용을 읽어옵니다. (예: "프로젝트A 읽어줘", "내용 조회")
    """
    page = wiki_manager.read_page(name)
    if not page:
        return f"Page '{name}' not found."
    return page.content

@mcp.tool()
async def SaveWikiContent(name: str, content: str) -> str:
    """
    Create or update a structured Wiki page.
    위키 페이지를 생성하거나 수정합니다. 지식을 정리하여 저장할 때 사용합니다.
    """
    wiki_manager.write_page(name, content)
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
    return f"Knowledge synthesized into '{target_page_name}'."

@mcp.tool()
async def OrganizeByTag(tag: str) -> str:
    """
    Find and group all notes associated with a specific hashtag.
    특정 태그(#)가 달린 모든 메모를 찾아 그룹화합니다. (예: "프로젝트A 태그된거 다 보여줘")
    """
    files = wiki_manager.get_tagged_raw_files(tag)
    if not files:
        return f"No material found with tag #{tag}."
    return f"Found {len(files)} items tagged with #{tag}:\n" + "\n".join(files)

@mcp.tool()
async def ConfigureSettings(
    wiki_root_path: str = None,
    local_llm_type: str = None,
    local_llm_api_url: str = None,
    local_llm_model: str = None,
    local_llm_api_key: str = None
) -> str:
    """Update system behavior and connection settings."""
    updates = {}
    if wiki_root_path: updates["wiki_root_path"] = wiki_root_path
    if local_llm_type: updates["local_llm_type"] = local_llm_type
    if local_llm_api_url: updates["local_llm_api_url"] = local_llm_api_url
    if local_llm_model: updates["local_llm_model"] = local_llm_model
    if local_llm_api_key: updates["local_llm_api_key"] = local_llm_api_key
    
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
1. First, search for ANY existing data using 'SearchAcrossWiki' and 'ListAllKnowledge'.
2. Use 'OrganizeByTag' with "{keyword}" to find fresh, unorganized notes.
3. Read all identified sources using 'AccessOriginalSource' and 'FetchWikiPage'.
4. Critically synthesize the disparate information into a cohesive, perfectly structured Markdown entry.
5. Save your masterpiece using 'SaveWikiContent'.

Tone: Expert, organized, and proactive. Use [[WikiLinks]] for cross-referencing.
"""

@mcp.prompt()
def KnowledgeAudit() -> str:
    """Ask the AI to scan the entire project and suggest organizational improvements."""
    return """
Identity: You are a Knowledge Curator.
Goal: Audit the current knowledge base and suggest structural improvements.

Instructions:
1. Examine the overall connectivity using 'AnalyzeKnowledgeGraph'.
2. Look for unprocessed potential knowledge by scanning 'SyncDocuments' results.
3. Identify 'orphaned' pages (no links) or 'dead-ends'.
4. Propose 3-5 high-impact actions to enhance the coherence of this Second Brain.
"""

def main():
    config_manager.initialize()
    mcp.run()

if __name__ == "__main__":
    main()
