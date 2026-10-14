import logging
from typing import List, Dict, Any, Optional
from gossipmesh.models.pr_review import SecurityFinding, TestResult

logger = logging.getLogger(__name__)

class GitHubIntegration:
    def __init__(self, owner: str = "", repo: str = "", pr_number: int = 0, github_pr_service: Optional[Any] = None):
        self.owner = owner
        self.repo = repo
        self.pr_number = pr_number
        self.github_pr_service = github_pr_service
        self.posted_finding_ids = set()

    async def generate_inline_comments(self, findings: List[SecurityFinding]):
        """
        Generates inline review comments on the PR based on findings.
        """
        logger.info(
            f"Generating inline comments for {len(findings)} findings."
        )

        if not self.github_pr_service:
            logger.warning("No GitHubPRService configured. Cannot post comments.")
            return

        # Group findings by file and line to group them into single comments
        grouped_findings: Dict[str, Dict[int, List[SecurityFinding]]] = {}
        for finding in findings:
            if finding.is_ai_generated and (finding.confidence_score is None or finding.evidence is None):
                logger.warning(f"Skipping AI finding {finding.id} due to missing evidence or confidence metadata.")
                continue

            if finding.id in self.posted_finding_ids:
                logger.warning(f"Skipping finding {finding.id} as it's already posted.")
                continue

            if finding.file_path not in grouped_findings:
                grouped_findings[finding.file_path] = {}
            if finding.line not in grouped_findings[finding.file_path]:
                grouped_findings[finding.file_path][finding.line] = []

            grouped_findings[finding.file_path][finding.line].append(finding)

        # Post review comments
        for file_path, lines in grouped_findings.items():
            for line, group in lines.items():
                # Further group by side
                side_groups = {}
                for finding in group:
                    if finding.side not in side_groups:
                        side_groups[finding.side] = []
                    side_groups[finding.side].append(finding)

                for side, side_group in side_groups.items():
                    comment_body = self._build_comment_body(side_group)
                    commit_sha = side_group[0].commit_sha

                    comment_payload = {
                        "commit_id": commit_sha,
                        "path": file_path,
                        "line": line,
                        "side": side,
                        "body": comment_body
                    }

                    try:
                        await self.github_pr_service.post_pr_review_comment(self.owner, self.repo, self.pr_number, comment_payload)
                        # Only mark as posted if successful
                        for f in side_group:
                            self.posted_finding_ids.add(f.id)
                    except Exception as e:
                        logger.error(f"Failed to post PR review comment for {file_path}:{line}: {e}")
                        # Handling partial failures by logging and continuing

    def _build_comment_body(self, findings: List[SecurityFinding]) -> str:
        body = ""
        for finding in findings:
            body += f"**[{finding.severity}] {finding.id}**\n"
            body += f"{finding.message}\n"
            if finding.evidence:
                body += f"**Evidence:** {finding.evidence}\n"
            if finding.confidence_score:
                body += f"**Confidence Score:** {finding.confidence_score}\n"
            body += "\n---\n"
        return body

    async def post_review_report(self, findings: List[SecurityFinding], test_results: TestResult):
        """
        Posts the final review report summary.
        """
        logger.info("Posting review report.")

        if not self.github_pr_service:
            logger.warning("No GitHubPRService configured. Cannot post review report.")
            return

        total_findings = len(findings)
        high_severity = len([f for f in findings if f.severity.upper() == "HIGH"])

        body = "## PR Review Summary\n\n"
        body += f"**Tests Status:** {test_results.status}\n\n"
        body += f"**Total Findings:** {total_findings}\n"
        body += f"**High Severity Findings:** {high_severity}\n"

        review_payload = {
            "event": "COMMENT",
            "body": body
        }

        try:
            await self.github_pr_service.post_pr_review(self.owner, self.repo, self.pr_number, review_payload)
        except Exception as e:
            logger.error(f"Failed to post PR review summary report: {e}")

    async def handle_human_approval(self):
        """
        Manages the human approval workflow state.
        """
        logger.info("Awaiting human approval workflow logic.")
