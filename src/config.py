import json
import os
from pathlib import Path
from typing import Optional, Literal
from pydantic import BaseModel, Field

LocalLlmType = Literal['ollama', 'llamacpp', 'external']

class Config(BaseModel):
    wiki_root_path: str = Field(default=str(Path.cwd() / "wiki"), alias="wikiRootPath")
    local_llm_type: LocalLlmType = "ollama"
    local_llm_api_url: str = "http://localhost:11434"
    local_llm_model: str = "gemma4-E4B-it"
    local_llm_api_key: Optional[str] = None
    mcp_port: int = 8000
    python_command: str = "python"

    model_config = {
        "populate_by_name": True
    }

class ConfigManager:
    def __init__(self):
        self.config = self._load_initial_config()

    def _load_initial_config(self) -> Config:
        # Load from environment variables if present
        root = os.getenv("WIKI_ROOT_PATH", str(Path.cwd() / "wiki"))
        
        return Config(
            wiki_root_path=root,
            local_llm_type=os.getenv("LOCAL_LLM_TYPE", "ollama"),
            local_llm_api_url=os.getenv("LOCAL_LLM_API_URL", "http://localhost:11434"),
            local_llm_model=os.getenv("LOCAL_LLM_MODEL", "gemma4-E4B-it"),
            local_llm_api_key=os.getenv("LOCAL_LLM_API_KEY"),
            mcp_port=int(os.getenv("MCP_PORT", "8000")),
        )

    def initialize(self):
        root_path = Path(self.config.wiki_root_path)
        root_path.mkdir(parents=True, exist_ok=True)
        (root_path / "pages").mkdir(exist_ok=True)
        (root_path / "raw").mkdir(exist_ok=True)
        (root_path / "transformed").mkdir(exist_ok=True)

        config_file = root_path / "config.json"
        if config_file.exists():
            try:
                with open(config_file, "r", encoding="utf-8") as f:
                    stored_data = json.load(f)
                    self.config = Config(**stored_data)
            except Exception as e:
                print(f"Error loading config.json: {e}")
        else:
            self._save_config()

    def _save_config(self):
        config_file = Path(self.config.wiki_root_path) / "config.json"
        with open(config_file, "w", encoding="utf-8") as f:
            json.dump(self.config.model_dump(), f, indent=2, ensure_ascii=False)

    def get_config(self) -> Config:
        return self.config

    def update_config(self, updates: dict):
        new_data = self.config.model_dump()
        new_data.update(updates)
        self.config = Config(**new_data)
        self._save_config()

config_manager = ConfigManager()
