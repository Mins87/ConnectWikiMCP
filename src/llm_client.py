from __future__ import annotations

import json
from typing import Any

import httpx

from config import config_manager


class LocalLlmClient:
    def __init__(self) -> None:
        self._timeout = 120.0

    async def complete_text(self, prompt: str, *, system_prompt: str | None = None) -> str:
        cfg = config_manager.get_config()
        if cfg.local_llm_type == "ollama":
            return await self._complete_ollama(prompt=prompt, system_prompt=system_prompt)
        if cfg.local_llm_type == "llamacpp":
            return await self._complete_llamacpp(prompt=prompt, system_prompt=system_prompt)
        if cfg.local_llm_type == "external":
            return await self._complete_external(prompt=prompt, system_prompt=system_prompt)
        raise ValueError(f"Unsupported LLM type: {cfg.local_llm_type}")

    async def generate_wiki_page(self, raw_content: str) -> str:
        prompt = (
            "Convert the following raw notes into a structured Markdown wiki page. "
            "Use concise headings, bullet points, and tables only when they add clarity.\n\n"
            f"RAW NOTES:\n{raw_content}"
        )
        return await self.complete_text(prompt, system_prompt="You are a professional Wiki compiler.")

    async def generate_json(self, prompt: str, *, system_prompt: str | None = None) -> dict[str, Any]:
        response = await self.complete_text(prompt, system_prompt=system_prompt)
        return self._extract_json(response)

    async def get_embedding(self, text: str) -> list[float]:
        """Generate a vector embedding for the given text using Ollama's embedding API.
        Returns an empty list if the embedding model is unavailable."""
        cfg = config_manager.get_config()
        if cfg.local_llm_type != "ollama":
            return []
        url = f"{cfg.local_llm_api_url.rstrip('/')}/api/embed"
        payload = {"model": cfg.embedding_model, "input": text[:4096]}
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, json=payload)
                response.raise_for_status()
                data = response.json()
                # Ollama returns {"embeddings": [[...]], "model": ...}
                embeddings = data.get("embeddings") or data.get("embedding")
                if isinstance(embeddings, list) and embeddings:
                    vec = embeddings[0] if isinstance(embeddings[0], list) else embeddings
                    return [float(v) for v in vec]
        except Exception:
            pass
        return []

    def _extract_json(self, response: str) -> dict[str, Any]:
        response = response.strip()
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            pass

        start = response.find("{")
        end = response.rfind("}")
        if start == -1 or end == -1 or end <= start:
            raise ValueError("Model did not return JSON.")
        return json.loads(response[start:end + 1])

    async def _complete_ollama(self, *, prompt: str, system_prompt: str | None = None) -> str:
        cfg = config_manager.get_config()
        url = f"{cfg.local_llm_api_url.rstrip('/')}/api/generate"
        payload = {
            "model": cfg.local_llm_model,
            "prompt": prompt,
            "system": system_prompt or "",
            "stream": False,
        }
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            return response.json().get("response", "")

    async def _complete_llamacpp(self, *, prompt: str, system_prompt: str | None = None) -> str:
        cfg = config_manager.get_config()
        url = f"{cfg.local_llm_api_url.rstrip('/')}/completion"
        full_prompt = f"{system_prompt}\n\n{prompt}" if system_prompt else prompt
        payload = {"prompt": full_prompt, "n_predict": 2048}
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            data = response.json()
            return data.get("content") or data.get("response") or ""

    async def _complete_external(self, *, prompt: str, system_prompt: str | None = None) -> str:
        cfg = config_manager.get_config()
        url = f"{cfg.local_llm_api_url.rstrip('/')}/v1/chat/completions"
        headers = {"Content-Type": "application/json"}
        if cfg.local_llm_api_key:
            headers["Authorization"] = f"Bearer {cfg.local_llm_api_key}"

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        payload = {"model": cfg.local_llm_model, "messages": messages, "temperature": 0.2}

        async with httpx.AsyncClient(timeout=self._timeout) as client:
            response = await client.post(url, json=payload, headers=headers)
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"]


llm_client = LocalLlmClient()
