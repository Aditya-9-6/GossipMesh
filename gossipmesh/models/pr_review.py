from pydantic import BaseModel, Field
from typing import Optional, List, Literal
from enum import Enum

class Verdict(str, Enum):
    APPROVED = "APPROVED"
    ACTION_REQUIRED = "ACTION_REQUIRED"
    REJECTED = "REJECTED"

class Severity(str, Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    INFO = "INFO"

class Confidence(str, Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"

class UsageSchema(BaseModel):
    prompt_tokens: int = Field(ge=0)
    completion_tokens: int = Field(ge=0)
    total_tokens: int = Field(ge=0)

class Citation(BaseModel):
    source: str
    url: Optional[str] = None

class Evidence(BaseModel):
    description: str
    code_snippet: Optional[str] = None
    citations: Optional[List[Citation]] = None

class Remediation(BaseModel):
    description: str
    auto_patch: Optional[str] = None

class SecurityFinding(BaseModel):
    id: str
    file_path: str = Field(..., min_length=1)
    line: int = Field(..., gt=0)
    side: str
    commit_sha: str
    severity: str
    message: str
    evidence: Optional[str] = None
    evidence_structured: Optional[Evidence] = None
    confidence_score: Optional[int] = Field(None, ge=0, le=100)
    confidence: Optional[Confidence] = None
    is_ai_generated: bool = False
    remediation: Optional[Remediation] = None
    usage: Optional[UsageSchema] = None
    paths: Optional[List[str]] = None
    lines: Optional[List[int]] = None

class ReviewResponse(BaseModel):
    verdict: Verdict
    findings: List[SecurityFinding]
    usage: Optional[UsageSchema] = None

class TestResult(BaseModel):
    status: str
