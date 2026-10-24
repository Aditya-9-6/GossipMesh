from enum import Enum
from typing import List, Optional, Union
from pydantic import BaseModel, Field, PrivateAttr


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
    prompt_tokens: int = Field(default=0, ge=0)
    completion_tokens: int = Field(default=0, ge=0)
    total_tokens: int = Field(default=0, ge=0)


class Citation(BaseModel):
    source: str
    url: Optional[str] = None


class Evidence(BaseModel):
    description: str
    code_snippet: Optional[str] = None
    citations: Optional[List[Citation]] = None


class RemediationModel(BaseModel):
    description: str
    auto_patch: Optional[str] = None


class SecurityFinding(BaseModel):
    id: str
    file_path: str = Field(..., min_length=1)
    line: int = Field(..., gt=0)
    side: str = "RIGHT"
    commit_sha: str = ""
    severity: str = "MEDIUM"
    message: str = ""
    evidence: Optional[str] = None
    evidence_structured: Optional[Evidence] = None
    confidence_score: Optional[int] = Field(None, ge=0, le=100)
    confidence: Optional[Confidence] = None
    is_ai_generated: bool = False
    fingerprint: str = ""
    remediation: Optional[Union[str, RemediationModel]] = ""
    source_scanner: str = ""
    end_line: Optional[int] = None
    github_comment_id: Optional[str] = None
    usage: Optional[UsageSchema] = None
    paths: Optional[List[str]] = None
    lines: Optional[List[int]] = None
    category: Optional[str] = None
    rule_id: Optional[str] = None
    sources: Optional[List[str]] = None


class ReviewResponse(BaseModel):
    verdict: Verdict
    findings: List[SecurityFinding] = Field(default_factory=list)
    usage: Optional[UsageSchema] = None


class ReviewTestResult(BaseModel):
    status: str


class TestResultRecord(BaseModel):
    __test__ = False
    status: str
    name: Optional[str] = None
    message: Optional[str] = None
    _is_test_class: bool = PrivateAttr(default=False)

    def __init__(self, **data):
        super().__init__(**data)


# Alias for compatibility imports
TestResult = TestResultRecord
