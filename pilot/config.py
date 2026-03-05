"""Configuration loader for Pilot agent."""

import os
from dataclasses import dataclass, field
from pathlib import Path

import yaml


@dataclass
class APIConfig:
    base_url: str = "http://localhost:1234/v1"
    api_key: str = "lm-studio"
    model: str = "qwen2.5-coder-32b"


@dataclass
class AgentConfig:
    max_iterations: int = 25
    temperature: float = 0.7
    system_prompt: str = "You are Pilot, an AI coding agent."


@dataclass
class Config:
    api: APIConfig = field(default_factory=APIConfig)
    agent: AgentConfig = field(default_factory=AgentConfig)

    @classmethod
    def load(cls, config_path: Path | None = None) -> "Config":
        """Load config from YAML file, then override with env vars."""
        config = cls()

        # Find config file
        if config_path is None:
            config_path = Path(__file__).parent.parent / "config.yaml"

        if config_path.exists():
            with open(config_path, "r", encoding="utf-8") as f:
                raw = yaml.safe_load(f) or {}

            api_raw = raw.get("api", {})
            agent_raw = raw.get("agent", {})

            config.api = APIConfig(
                base_url=api_raw.get("base_url", config.api.base_url),
                api_key=api_raw.get("api_key", config.api.api_key),
                model=api_raw.get("model", config.api.model),
            )
            config.agent = AgentConfig(
                max_iterations=agent_raw.get("max_iterations", config.agent.max_iterations),
                temperature=agent_raw.get("temperature", config.agent.temperature),
                system_prompt=agent_raw.get("system_prompt", config.agent.system_prompt),
            )

        # Env var overrides
        if url := os.environ.get("PILOT_API_URL"):
            config.api.base_url = url
        if key := os.environ.get("PILOT_API_KEY"):
            config.api.api_key = key
        if model := os.environ.get("PILOT_MODEL"):
            config.api.model = model

        return config
