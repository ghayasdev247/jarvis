"""
core/parallel_runner.py
Parallel Tool Execution Runner for JARVIS.

Inspired by Jarvis Institute feature specifications:
- Executes independent tool invocations concurrently via asyncio.gather().
- Allows 3x faster tool processing for multi-part tasks.
"""

from __future__ import annotations

import asyncio
from typing import Any, Callable, Dict, List, Optional, Tuple


async def execute_parallel_tools(
    tool_invocations: List[Tuple[Callable, Dict[str, Any], Dict[str, Any]]],
    timeout: float = 60.0,
) -> List[Any]:
    """
    Executes multiple tool calls simultaneously in separate threads/tasks.
    Each item in tool_invocations is: (handler_func, params_dict, ctx_dict).
    """
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    async def _run_single(handler: Callable, params: Dict[str, Any], ctx: Dict[str, Any]) -> Any:
        try:
            # Run in worker thread so sync I/O in actions doesn't block the event loop
            return await loop.run_in_executor(None, lambda: handler(parameters=params, **ctx))
        except Exception as e:
            return f"Error executing tool: {e}"

    tasks = [_run_single(h, p, c) for h, p, c in tool_invocations]
    try:
        results = await asyncio.wait_for(asyncio.gather(*tasks, return_exceptions=True), timeout=timeout)
        return list(results)
    except asyncio.TimeoutError:
        return [f"Tool execution timed out after {timeout}s" for _ in tool_invocations]
