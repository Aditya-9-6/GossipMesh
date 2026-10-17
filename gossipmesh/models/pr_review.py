from dataclasses import dataclass
from typing import Optional

@dataclass
class SecurityFinding:
    id: str
    file_path: str
    line: int
    side: str
    commit_sha: str
    severity: str
    message: str
    evidence: Optional[str] = None
    confidence_score: Optional[int] = None
    is_ai_generated: bool = False
    fingerprint: str = ""
    remediation: str = ""
    source_scanner: str = ""
    end_line: Optional[int] = None
    github_comment_id: Optional[str] = None

@dataclass
class TestResult:
    status: str
