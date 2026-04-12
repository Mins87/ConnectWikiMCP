import logging
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

def main():
    config_manager.initialize()
    mcp.run()

if __name__ == "__main__":
    main()
