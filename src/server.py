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
async def read_page(name: str) -> str:
    """Read a Wiki page by name (without .md)."""
    page = wiki_manager.read_page(name)
    if not page:
        return "Page not found"
    return page.content

@mcp.tool()
async def write_page(name: str, content: str) -> str:
    """Create or update a Wiki page."""
    wiki_manager.write_page(name, content)
    return f"Page '{name}' updated successfully."

@mcp.tool()
async def list_pages() -> str:
    """List all available Wiki pages."""
    pages = wiki_manager.list_pages()
    return "\n".join(pages)

@mcp.tool()
async def search_wiki(query: str) -> str:
    """Search for content across all Wiki pages."""
    results = wiki_manager.search_wiki(query)
    if not results:
        return "No results found"
    
    text_results = []
    for r in results:
        preview = r.content[:200] + "..." if len(r.content) > 200 else r.content
        text_results.append(f"## {r.name}\n{preview}")
        
    return "\n\n".join(text_results)

@mcp.tool()
async def get_backlinks(name: str) -> str:
    """Get all pages that link to the specified page."""
    backlinks = wiki_manager.get_backlinks(name)
    if not backlinks:
        return f"No backlinks found for '{name}'."
    return f"Pages linking to '{name}':\n" + "\n".join(backlinks)

@mcp.tool()
async def get_graph() -> str:
    """Get the full knowledge graph (nodes and edges) in JSON format."""
    graph = wiki_manager.get_graph_data()
    return json.dumps(graph, indent=2)

@mcp.tool()
async def ingest_raw(name: str, content: str) -> str:
    """Save raw information for later compilation."""
    wiki_manager.ingest_raw(name, content)
    return "Raw content ingested successfully."

@mcp.tool()
async def read_raw(path: str) -> str:
    """Read raw content, automatically converting if it's a binary file."""
    content = await wiki_manager.read_raw(path)
    if content is None:
        return "File not found or unreadable"
    return content

@mcp.tool()
async def sync_raw() -> str:
    """Synchronize the raw folder: converts all new or modified non-markdown files to markdown."""
    status = wiki_manager.sync_raw_folder()
    return f"Sync complete: {status['converted']} files converted, {status['skipped']} skipped."

@mcp.tool()
async def compile_with_local_llm(raw_filename: str, target_page_name: str) -> str:
    """Process raw notes into a Wiki page using the local LLM."""
    raw_content = await wiki_manager.read_raw(raw_filename)
    if not raw_content:
        return "Raw file not found"
    
    compiled = await llm_client.generate_wiki_page(raw_content)
    wiki_manager.write_page(target_page_name, compiled)
    return f"Wiki page '{target_page_name}' created from raw content."

@mcp.tool()
async def auto_archive_by_tag(tag: str) -> str:
    """Automatically find all raw notes with a specific #tag and suggest a compilation."""
    files = wiki_manager.get_tagged_raw_files(tag)
    if not files:
        return f"No raw files found with tag #{tag}."
    return f"Found {len(files)} files with tag #{tag}:\n" + "\n".join(files) + "\n\nPlease use these to update the wiki."

@mcp.tool()
async def set_config(
    wiki_root_path: str = None,
    local_llm_type: str = None,
    local_llm_api_url: str = None,
    local_llm_model: str = None,
    local_llm_api_key: str = None
) -> str:
    """Update the server configuration."""
    updates = {}
    if wiki_root_path: updates["wiki_root_path"] = wiki_root_path
    if local_llm_type: updates["local_llm_type"] = local_llm_type
    if local_llm_api_url: updates["local_llm_api_url"] = local_llm_api_url
    if local_llm_model: updates["local_llm_model"] = local_llm_model
    if local_llm_api_key: updates["local_llm_api_key"] = local_llm_api_key
    
    config_manager.update_config(updates)
    return "Configuration updated successfully."

# --- MCP Prompts ---

@mcp.prompt()
def smart_compile(keyword: str) -> str:
    """A prompt to help the AI compile structured knowledge for a specific keyword."""
    return f"""
You are a Knowledge Management Expert. I want to compile or update a Wiki page for the keyword: "{keyword}".

Please follow these steps:
1. Use 'search_wiki' to see if a page for "{keyword}" already exists.
2. Use 'auto_archive_by_tag' with the tag "{keyword}" to find new raw notes.
3. Read the relevant raw files and the existing wiki page (if any).
4. Synthesize all information into a high-quality, structured Markdown Wiki page.
5. Use 'write_page' to save the final result.

Focus on clarity, cross-linking (using [[PageName]]), and capturing all new insights.
"""

@mcp.prompt()
def wiki_audit() -> str:
    """A prompt to ask the AI to audit the wiki and suggest improvements."""
    return """
You are a Knowledge Curator. Please audit the current state of the Wiki.

1. Use 'list_pages' and 'get_graph' to understand the structure.
2. Scan the 'raw/' directory using 'sync_raw' and 'list_raw' to find unprocessed information.
3. Identify gaps, redundant pages, or missing connections.
4. Suggest a list of actions (e.g., 'Compile X', 'Link A to B') to improve the total knowledge base.
"""

def main():
    config_manager.initialize()
    mcp.run()

if __name__ == "__main__":
    main()
