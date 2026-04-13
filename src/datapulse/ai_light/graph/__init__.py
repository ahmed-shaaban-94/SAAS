"""AI-Light LangGraph orchestration package.

This package introduces LangGraph as the orchestration engine behind the existing
``ai_light`` endpoints.  It is loaded lazily (only when
``settings.ai_light_use_langgraph`` is True) so the optional ``[ai]`` dependencies
are not required for the default runtime.

Public API
----------
``build_graph``   — compile the LangGraph state-machine once at startup.
``AILightState``  — typed state dict shared across all graph nodes.
"""

# Placeholder — populated in Phase A (summary path).
# from datapulse.ai_light.graph.builder import build_graph  # noqa: F401
# from datapulse.ai_light.graph.state import AILightState    # noqa: F401

__all__: list[str] = []
