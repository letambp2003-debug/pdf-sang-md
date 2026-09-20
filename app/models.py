from typing import Literal
from pydantic import BaseModel, Field


class JobOptions(BaseModel):
    engine: Literal["auto", "mineru", "pymupdf"] = "auto"
    mineru_tier: Literal["flash", "basic", "standard", "advanced"] = "standard"
    ocr_mode: Literal["off", "auto", "force"] = "auto"
    ocr_languages: str = "vie+eng"
    gemini_qa: bool = False
    gemini_qa_scope: Literal["flagged", "all"] = "flagged"
    auto_apply_safe_fixes: bool = False
    safe_fix_min_confidence: float = Field(default=0.985, ge=0.90, le=1.0)
    render_dpi: int = Field(default=240, ge=120, le=350)
    preserve_page_renders: bool = True
    build_datapack: bool = True
    subject: str = ""
    grade: str = ""
    book_set: str = ""


class QAIssue(BaseModel):
    page: int
    error_type: Literal[
        "missing_text",
        "wrong_text",
        "reading_order",
        "table",
        "formula",
        "image",
        "caption",
        "heading",
        "other",
    ]
    severity: Literal["low", "medium", "high", "critical"]
    evidence: str
    correction: str = ""
    original: str = ""
    replacement: str = ""
    confidence: float = Field(ge=0, le=1)
    safe_to_apply: bool = False


class PageQA(BaseModel):
    page: int
    status: Literal["PASS", "REVIEW"]
    issues: list[QAIssue] = []


class QAResult(BaseModel):
    pages: list[PageQA]
