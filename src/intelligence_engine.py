from __future__ import annotations

import logging
from typing import Any

from llm_client import llm_client
from wiki_manager import wiki_manager

logger = logging.getLogger("connect-wiki.intelligence")


class IntelligenceEngine:
    def __init__(self) -> None:
        self.wiki = wiki_manager

    async def analyze_and_enrich(self, page_name: str, content: str) -> str | None:
        logger.info("Analyzing page '%s' for enrichment", page_name)
        all_pages = self.wiki.list_pages()
        existing_pages = [page for page in all_pages if page != page_name]

        prompt = f"""
Analyze the wiki page below.
Return JSON only with this schema:
{{
  "suggested_tags": ["tag1", "tag2"],
  "suggested_links": ["Existing/Page"],
  "summary": "one sentence"
}}
Rules:
- suggested_tags: 0 to 5 short lowercase tags without #.
- suggested_links: only items that already exist in KNOWLEDGE_LIST.
- summary: concise plain-text sentence.

KNOWLEDGE_LIST:
{existing_pages}

PAGE_NAME:
{page_name}

CONTENT:
{content}
""".strip()

        try:
            data = await llm_client.generate_json(
                prompt,
                system_prompt="You are an AI Knowledge Architect. Respond with valid JSON only.",
            )
        except Exception as exc:
            logger.error("Intelligence analysis failed for '%s': %s", page_name, exc)
            return None

        return self._apply_enrichment(content=content, all_pages=all_pages, data=data)

    def _apply_enrichment(self, *, content: str, all_pages: list[str], data: dict[str, Any]) -> str | None:
        suggested_tags = [str(tag).strip().lower() for tag in data.get("suggested_tags", []) if str(tag).strip()]
        suggested_links = [str(link).strip() for link in data.get("suggested_links", []) if str(link).strip()]
        summary = str(data.get("summary", "")).strip()

        current_tags = {tag.lower() for tag in self.wiki.extract_tags(content)}
        current_links = set(self.wiki.extract_links(content))
        valid_pages = set(all_pages)

        new_tags = [tag for tag in suggested_tags if tag not in current_tags][:5]
        new_links = [link for link in suggested_links if link in valid_pages and link not in current_links]

        blocks = []
        if summary:
            blocks.append(f"**AI Summary**: {summary}")
        if new_tags:
            blocks.append("**AI Generated Tags**: " + " ".join(f"#{tag}" for tag in new_tags))
        if new_links:
            blocks.append("**AI Suggested Connections**: " + ", ".join(f"[[{link}]]" for link in new_links))

        if not blocks:
            return None

        enriched = content.rstrip() + "\n\n---\n" + "\n".join(blocks)
        return enriched


intelligence_engine = IntelligenceEngine()
