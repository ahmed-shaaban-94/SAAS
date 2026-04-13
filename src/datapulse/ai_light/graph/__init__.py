"""AI-Light LangGraph package — Phase A-2 (summary path).

Public symbols are NOT imported here to avoid mypy following the import chain
into graph/ subpackage (which triggers a mypy int64 cache crash on Linux CI
due to Annotated[..., callable] type aliases). Import directly from submodules:
    from datapulse.ai_light.graph.builder import build_graph
    from datapulse.ai_light.graph.state import AILightState
"""

__all__: list[str] = []
