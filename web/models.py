"""Pydantic response models for the Financial Analysis Web UI backend."""

from enum import Enum

from pydantic import BaseModel


class StatementStatusEnum(str, Enum):
    """Status of an individual statement extraction or the overall analysis."""

    pending = "pending"
    processing = "processing"
    completed = "completed"
    error = "error"


class StatementResult(BaseModel):
    """Status and result for a single financial statement extraction."""

    status: StatementStatusEnum = StatementStatusEnum.pending
    page_num: int | None = None
    result: dict | None = None  # JSON from existing save_json structure
    error: str | None = None
    cached: bool = False  # True when result was loaded from cache


class ConsolidatedResult(BaseModel):
    """Status and result for the consolidated cross-statement analysis."""

    status: StatementStatusEnum = StatementStatusEnum.pending
    result: dict | None = None


class AnalysisRecord(BaseModel):
    """Full record for a single PDF analysis, keyed by analysis_id in the in-memory store."""

    analysis_id: str
    filename: str
    status: StatementStatusEnum = StatementStatusEnum.processing
    statements: dict[str, StatementResult]  # keys: balance_sheet, income_statement, cash_flow
    consolidated: ConsolidatedResult = ConsolidatedResult()
    pdf_path: str  # temp file path for page rendering
    pdf_stem: str = ""  # PDF filename without extension for output directory identification


class AnalysisItem(BaseModel):
    """A single analysis item in the sidebar list."""

    id: str  # The pdf_stem (directory name)
    display_name: str  # Same as id (directory name)
    has_results: bool  # True if at least one JSON result exists


class AnalysisListResponse(BaseModel):
    """Response model for the analysis list endpoint."""

    analyses: list[AnalysisItem]


class RenameRequest(BaseModel):
    """Request model for renaming an analysis directory."""

    current_id: str  # Current directory name (pdf_stem)
    new_name: str  # New directory name


class RenameResponse(BaseModel):
    """Response model for the rename endpoint."""

    success: bool
    new_id: str | None = None
    error: str | None = None
