import httpx
from typing import Optional
from config import config_manager

class LocalLlmClient:
    async def generate_wiki_page(self, raw_content: str) -> str:
        cfg = config_manager.get_config()
        
        prompt = (
            "You are a professional Wiki compiler. Convert the following raw notes into a structured, "
            "beautiful Markdown wiki page. Use appropriate headers, bullet points, and tables if necessary.\n\n"
            f"RAW NOTES:\n{raw_content}"
        )

        if cfg.local_llm_type == "ollama":
            return await self._generate_ollama(prompt)
        elif cfg.local_llm_type == "llamacpp":
            return await self._generate_llamacpp(prompt)
        elif cfg.local_llm_type == "external":
            return await self._generate_external(prompt)
        else:
            raise ValueError(f"Unsupported LLM type: {cfg.local_llm_type}")

    async def _generate_ollama(self, prompt: str) -> str:
        cfg = config_manager.get_config()
        url = f"{cfg.local_llm_api_url}/api/generate"
        payload = {
            "model": cfg.local_llm_model,
            "prompt": prompt,
            "stream": False
        }
        
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            return response.json().get("response", "")

    async def _generate_llamacpp(self, prompt: str) -> str:
        cfg = config_manager.get_config()
        url = f"{cfg.local_llm_api_url}/completion"
        payload = {
            "prompt": prompt,
            "n_predict": 2048,
        }
        
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            return response.json().get("content", "")

    async def _generate_external(self, prompt: str) -> str:
        cfg = config_manager.get_config()
        url = f"{cfg.local_llm_api_url}/v1/chat/completions"
        headers = {}
        if cfg.local_llm_api_key:
            headers["Authorization"] = f"Bearer {cfg.local_llm_api_key}"
            
        payload = {
            "model": cfg.local_llm_model,
            "messages": [{"role": "user", "content": prompt}]
        }
        
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(url, json=payload, headers=headers)
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"]

llm_client = LocalLlmClient()
