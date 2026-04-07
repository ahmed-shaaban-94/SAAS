"""Pydantic models for data lineage."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class LineageNode(BaseModel):
    model_config = ConfigDict(frozen=True)

    name: str
    layer: str  # "bronze", "silver", "gold"
    model_type: str  # "source", "staging", "dimension", "fact", "aggregate", "feature"


class LineageEdge(BaseModel):
    model_config = ConfigDict(frozen=True)

    source: str
    target: str


class LineageGraph(BaseModel):
    model_config = ConfigDict(frozen=True)

    nodes: list[LineageNode]
    edges: list[LineageEdge]
