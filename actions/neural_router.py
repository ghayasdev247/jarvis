"""
actions/neural_router.py
Neural LLM Router action for JARVIS.
Allows querying Claude, OpenAI, Groq, Ollama, OpenRouter, or Gemini via prefix or smart routing.
"""

from __future__ import annotations
from typing import Optional
from core.neural_router import NeuralRouter


def handle_route_query(
    query: str,
    provider: Optional[str] = None,
    model: Optional[str] = None,
    system_instruction: Optional[str] = None,
    player=None,
    speak=None,
) -> str:
    if not query:
        return "No query provided to route."

    prov_label = provider.upper() if provider else "AUTO"
    log_msg = f"[Router] Routing query via {prov_label}..."
    print(log_msg)
    if player:
        player.write_log(log_msg)

    response = NeuralRouter.route_query(
        prompt=query,
        system_instruction=system_instruction or "",
        explicit_provider=provider,
        explicit_model=model,
    )
    return response


def router_action(parameters: dict, player=None, speak=None) -> str:
    query = parameters.get("query", "")
    provider = parameters.get("provider")
    model = parameters.get("model")
    system_instruction = parameters.get("system_instruction")
    return handle_route_query(
        query=query,
        provider=provider,
        model=model,
        system_instruction=system_instruction,
        player=player,
        speak=speak,
    )


TOOL = {
    "name": "neural_router",
    "description": (
        "Routes reasoning, coding, translation, or questions to the best LLM provider among 7 supported: "
        "Anthropic Claude (complex coding/reasoning), OpenAI (general intelligence), Groq (instant low-latency), "
        "Ollama (local private), OpenRouter, or Google Gemini. "
        "Supports query prefixes like 'claude:', 'gpt:', 'groq:', 'ollama:'."
    ),
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "query": {
                "type": "STRING",
                "description": "The prompt or query to route (can include prefix like 'claude:', 'groq:').",
            },
            "provider": {
                "type": "STRING",
                "description": "Optional explicit provider: 'anthropic', 'openai', 'groq', 'ollama', 'openrouter', or 'gemini'.",
            },
            "model": {
                "type": "STRING",
                "description": "Optional specific model ID (e.g. 'claude-3-5-sonnet-20241022', 'gpt-4o', 'llama-3.3-70b-versatile').",
            },
            "system_instruction": {
                "type": "STRING",
                "description": "Optional custom system instruction for the targeted model.",
            },
        },
        "required": ["query"],
    },
    "handler": router_action,
}
