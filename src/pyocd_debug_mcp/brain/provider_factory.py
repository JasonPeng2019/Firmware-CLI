"""Factory for turnkey decision providers."""

from __future__ import annotations

from pyocd_debug_mcp.brain.config import BrainProviderConfig
from pyocd_debug_mcp.brain.provider_anthropic import AnthropicDecisionProvider
from pyocd_debug_mcp.brain.provider_claude_cli import ClaudeCLIDecisionProvider
from pyocd_debug_mcp.brain.provider_codex_cli import CodexCLIDecisionProvider
from pyocd_debug_mcp.brain.provider_openai import OpenAIDecisionProvider
from pyocd_debug_mcp.brain.provider_types import DecisionProvider


def create_decision_provider(config: BrainProviderConfig) -> DecisionProvider:
    if config.provider == "openai-api":
        if config.api_key is None or config.model is None:
            raise RuntimeError("OpenAI API provider requires both api_key and model.")
        return OpenAIDecisionProvider(api_key=config.api_key, model=config.model)

    if config.provider == "anthropic-api":
        if config.api_key is None or config.model is None:
            raise RuntimeError("Anthropic API provider requires both api_key and model.")
        return AnthropicDecisionProvider(api_key=config.api_key, model=config.model)

    if config.provider == "codex-cli":
        return CodexCLIDecisionProvider(model=config.model)

    if config.provider == "claude-cli":
        return ClaudeCLIDecisionProvider(model=config.model)

    raise RuntimeError(f"Unsupported turnkey provider: {config.provider}")
