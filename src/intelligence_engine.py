import json
import logging
import re
from typing import List, Dict, Optional
from llm_client import llm_client
from wiki_manager import wiki_manager

logger = logging.getLogger("intelligence-engine")

class IntelligenceEngine:
    def __init__(self):
        self.wiki = wiki_manager

    async def analyze_and_enrich(self, page_name: str, content: str) -> Optional[str]:
        """
        Analyze content, extract tags/links, and return an enriched version of the content.
        Returns None if no enrichment was possible or needed.
        """
        logger.info(f"Analyzing page '{page_name}' for enrichment...")
        
        # 1. Get existing pages for link suggestion
        all_pages = self.wiki.list_pages()
        # Remove current page from suggestions
        existing_pages = [p for p in all_pages if p != page_name]
        
        prompt = f"""
You are an AI Knowledge Architect. Analyze the following wiki content.
Task:
1. Identify key topics and suggest 3-5 hashtags.
2. Identify mentions of existing pages from the 'KNOWLEDGE_LIST' and suggest where to add [[WikiLinks]].

KNOWLEDGE_LIST: {", ".join(existing_pages)}

CONTENT TO ANALYZE:
---
{content}
---

Return ONLY a JSON object with this structure:
{{
  "suggested_tags": ["tag1", "tag2"],
  "suggested_links": ["PageName1", "PageName2"],
  "summary": "one sentence summary"
}}
"""
        try:
            response_text = await llm_client.generate_wiki_page(prompt)
            # Try to find JSON in the response
            match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if not match:
                logger.warning(f"No JSON found in AI response for '{page_name}'")
                return None
                
            data = json.loads(match.group())
            tags = data.get("suggested_tags", [])
            links = data.get("suggested_links", [])
            
            # 2. Apply enrichment
            modified = False
            enriched_content = content.strip()
            
            # Add Tags if they don't exist
            current_tags = self.wiki.extract_tags(content)
            new_tags = [t for t in tags if t.lower() not in [ct.lower() for ct in current_tags]]
            
            if new_tags:
                tag_str = " ".join([f"#{t}" for t in new_tags])
                enriched_content += f"\n\n---\n**AI Generated Tags**: {tag_str}"
                modified = True
                
            # Add suggested links as a footer if they aren't already linked
            current_links = self.wiki.extract_links(content)
            unlinked = [l for l in links if l not in current_links and l in all_pages]
            
            if unlinked:
                link_str = ", ".join([f"[[{l}]]" for l in unlinked])
                if not modified:
                    enriched_content += "\n\n---"
                enriched_content += f"\n**AI Suggested Connections**: {link_str}"
                modified = True
                
            if modified:
                logger.info(f"Page '{page_name}' enriched with AI intelligence.")
                return enriched_content
            
            return None
            
        except Exception as e:
            logger.error(f"Intelligence analysis failed for '{page_name}': {e}")
            return None

intelligence_engine = IntelligenceEngine()
