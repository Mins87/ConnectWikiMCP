from __future__ import annotations

import json
import logging
import os
import sys
from pathlib import Path
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

# Ensure logging goes to stderr as early as possible to protect MCP stdout stream
import logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    stream=sys.stderr,
)
logger = logging.getLogger("connect-wiki.config")

LocalLlmType = Literal["ollama", "llamacpp", "external"]


class Config(BaseModel):
    """Pydantic model for system-wide configuration settings."""
    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    wiki_root_path: str = Field(default=str(Path.cwd() / "wiki"), alias="wikiRootPath")
    local_llm_type: LocalLlmType = "ollama"
    local_llm_api_url: str = "http://localhost:11434"
    local_llm_model: str = "gemma4-E4B-it"
    local_llm_api_key: Optional[str] = None
    embedding_model: str = "nomic-embed-text"          # Ollama embedding model
    mcp_port: int = 8000
    python_command: str = "python"
    brain_watch_path: str = ""                          # Antigravity brain dir; empty = disabled
    conversation_watch_interval_minutes: int = 30      # 0 = disabled


class ConfigManager:
    """Manages configuration state by merging environment variables and JSON storage."""
    def __init__(self) -> None:
        """Initialize version and load bootstrap configuration from environment."""
        self.version = "1.0.1"
        self.config = self._load_from_env()

    def _load_from_env(self) -> Config:
        """Hydrate a Config object exclusively from OS environment variables."""
        root = os.getenv("WIKI_ROOT_PATH", str(Path.cwd() / "wiki"))
        return Config(
            wiki_root_path=root,
            local_llm_type=os.getenv("LOCAL_LLM_TYPE", "ollama"),
            local_llm_api_url=os.getenv("LOCAL_LLM_API_URL", "http://localhost:11434"),
            local_llm_model=os.getenv("LOCAL_LLM_MODEL", "gemma4-E4B-it"),
            local_llm_api_key=os.getenv("LOCAL_LLM_API_KEY"),
            embedding_model=os.getenv("EMBEDDING_MODEL", "nomic-embed-text"),
            mcp_port=int(os.getenv("MCP_PORT", "8000")),
            python_command=os.getenv("PYTHON_COMMAND", "python"),
            brain_watch_path=os.getenv("BRAIN_WATCH_PATH", ""),
            conversation_watch_interval_minutes=int(os.getenv("CONVERSATION_WATCH_INTERVAL", "30")),
        )

    def initialize(self) -> None:
        """Perform the full initialization handshake: merge storage, validate paths, and save."""
        # 1. Start with Env-based config
        base_config = self._load_from_env()
        
        # 2. Try to merge from config.json if it exists
        config_file = self._config_file_for(base_config.wiki_root_path)
        if config_file.exists():
            try:
                stored_data = json.loads(config_file.read_text(encoding="utf-8"))
                
                # Normalize paths in stored_data to avoid cross-platform issues
                if os.name != "nt" and "wikiRootPath" in stored_data:
                    val = str(stored_data["wikiRootPath"])
                    if ":" in val or "\\" in val:
                        logger.warning("Detected Windows-style path in Linux environment. Normalizing to current environment defaults.")
                        del stored_data["wikiRootPath"]
                
                # Merge: File values are base, but Environment Variables TAKE PRECEDENCE
                merged_data = {**stored_data, **base_config.model_dump(exclude_unset=True)}
                self.config = Config(**merged_data)
            except Exception:
                logger.exception("Failed to load or normalize config.json")
        else:
            self.config = base_config

        self._ensure_layout(Path(self.config.wiki_root_path))
        self._save_config()

    def _ensure_layout(self, root_path: Path) -> None:
        """Create the necessary directory structure if it does not exist."""
        root_path.mkdir(parents=True, exist_ok=True)
        for name in ("pages", "raw", "transformed", "logs", "digests"):
            (root_path / name).mkdir(parents=True, exist_ok=True)
        # Raw 3-source input architecture
        for sub in ("files", "memos", "conversations"):
            (root_path / "raw" / sub).mkdir(parents=True, exist_ok=True)

    def _config_file_for(self, wiki_root_path: str | Path) -> Path:
        return Path(wiki_root_path) / "config.json"

    def _save_config(self) -> None:
        root = Path(self.config.wiki_root_path)
        self._ensure_layout(root)
        config_file = self._config_file_for(root)
        config_file.write_text(
            json.dumps(self.config.model_dump(by_alias=True), indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    def get_config(self) -> Config:
        """Retrieve the current active configuration."""
        return self.config

    def update_config(self, updates: dict) -> Config:
        """Apply a partial update to the configuration and persist it to disk."""
        new_data = self.config.model_dump()
        new_data.update({k: v for k, v in updates.items() if v is not None})
        self.config = Config(**new_data)
        self._save_config()
        return self.config


config_manager = ConfigManager()
