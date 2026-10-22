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

@dataclass
class TestResult:
    status: str
