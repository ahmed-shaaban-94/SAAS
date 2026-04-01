"""Pydantic models for the report template engine."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field


class ParameterType(StrEnum):
    """Supported parameter types for report templates."""

    text = "text"
    number = "number"
    date = "date"
    select = "select"


class ReportParameter(BaseModel):
    """A configurable parameter for a report template."""

    name: str = Field(..., description="Parameter identifier")
    label: str = Field(..., description="Display label")
    param_type: ParameterType = Field(..., description="Input type")
    default: str | int | float | None = None
    options: list[str] = Field(default_factory=list, description="Options for select type")
    required: bool = True


class SectionType(StrEnum):
    """Types of report sections."""

    text = "text"
    query = "query"
    kpi = "kpi"


class ReportSection(BaseModel):
    """A single section within a report template."""

    section_type: SectionType
    title: str = ""
    text: str = ""
    sql: str = ""
    chart_type: str = "table"


class ReportTemplate(BaseModel):
    """A report template with parameters and sections."""

    id: str = Field(..., description="Unique template ID")
    name: str = Field(..., description="Template name")
    description: str = ""
    parameters: list[ReportParameter] = Field(default_factory=list)
    sections: list[ReportSection] = Field(default_factory=list)


class RenderedSection(BaseModel):
    """A rendered section with data."""

    section_type: SectionType
    title: str = ""
    text: str = ""
    columns: list[str] = Field(default_factory=list)
    rows: list[list] = Field(default_factory=list)
    row_count: int = 0
    chart_type: str = "table"


class RenderedReport(BaseModel):
    """A fully rendered report."""

    template_id: str
    template_name: str
    parameters: dict[str, str | int | float] = Field(default_factory=dict)
    sections: list[RenderedSection] = Field(default_factory=list)
