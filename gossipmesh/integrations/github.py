import logging
import re
from typing import Dict, List, Optional, Set, Tuple, Any
from gossipmesh.models.pr_review import SecurityFinding, TestResult
from gossipmesh.integrations.github_pr import GitHubPRService

logger = logging.getLogger(__name__)


class GitHubIntegration:
    def __init__(self, owner: str, repo: str, pr_number: int, github_pr_service: GitHubPRService):
        self.owner = owner
        self.repo = repo
        self.pr_number = pr_number
        self.github_pr_service = github_pr_service

    def _parse_unified_diff(self, diff: str) -> Dict[str, Dict[str, Set[int]]]:
        valid_lines: Dict[str, Dict[str, Set[int]]] = {"RIGHT": {}, "LEFT": {}}
        current_file = None
        current_right_line = 0
        current_left_line = 0

        for line in diff.split("\n"):
            if line.startswith("--- a/") or line.startswith("+++ b/") or line.startswith("+++ /dev/null"):
                current_file = line[6:]
                valid_lines["RIGHT"][current_file] = set()
                valid_lines["LEFT"][current_file] = set()
            elif line.startswith("@@"):
                match = re.search(r"-(\d+)(?:,\d+)? \+(\d+)(?:,\d+)? @@", line)
                if match:
                    current_left_line = int(match.group(1))
                    current_right_line = int(match.group(2))
            elif line.startswith("+") and not line.startswith("+++"):
                if current_file:
                    valid_lines["RIGHT"][current_file].add(current_right_line)
                current_right_line += 1
            elif line.startswith("-") and not line.startswith("---"):
                if current_file:
                    valid_lines["LEFT"][current_file].add(current_left_line)
                current_left_line += 1
            elif line.startswith(" ") or not line:
                current_right_line += 1
                current_left_line += 1

        return valid_lines

    async def generate_inline_comments(self, findings: List[SecurityFinding]):
        logger.info(f"Generating inline comments for {len(findings)} findings.")

        diff = await self.github_pr_service.get_pr_diff(self.owner, self.repo, self.pr_number)
        valid_lines = self._parse_unified_diff(diff)

        seen_fingerprints = set()

        # Fetch existing comments to support cross-run retry safety
        try:
            get_comments_fn = getattr(self.github_pr_service, "get_pr_review_comments", None)
            if get_comments_fn:
                existing_comments = await get_comments_fn(self.owner, self.repo, self.pr_number)
                for comment in existing_comments:
                    body = comment.get("body", "")
                    for fp in re.findall(r"<!-- fingerprint: (.*?) -->", body):
                        seen_fingerprints.add(fp)

            existing_reviews = await self.github_pr_service.get_pr_reviews(self.owner, self.repo, self.pr_number)
            for review in existing_reviews:
                body = review.get("body", "")
                if body:
                    for fp in re.findall(r"<!-- fingerprint: (.*?) -->", body):
                        seen_fingerprints.add(fp)
        except Exception as e:
            logger.warning(f"Failed to fetch existing PR comments for deduplication: {e}")

        grouped_findings: Dict[Tuple[str, int, Optional[int], str], List[SecurityFinding]] = {}
        fallback_findings = []

        for finding in findings:
            if finding.fingerprint and finding.fingerprint in seen_fingerprints:
                continue
            if finding.fingerprint:
                seen_fingerprints.add(finding.fingerprint)

            # Validation
            is_valid_line = False
            side_valid_lines = valid_lines.get(finding.side)
            if side_valid_lines and finding.file_path in side_valid_lines:
                if finding.line in side_valid_lines[finding.file_path]:
                    if finding.end_line:
                        if finding.end_line in side_valid_lines[finding.file_path]:
                            is_valid_line = True
                    else:
                        is_valid_line = True

            if not is_valid_line:
                fallback_findings.append(finding)
                continue

            group_key = (finding.file_path, finding.line, finding.end_line, finding.side)
            if group_key not in grouped_findings:
                grouped_findings[group_key] = []
            grouped_findings[group_key].append(finding)

        review_comments = []

        for group_key, findings_group in grouped_findings.items():
            file_path, line, end_line, side = group_key

            body = ""
            for f in findings_group:
                body += f"**{f.severity}**: {f.message}\n"
                if f.evidence:
                    body += f"**Evidence**: {f.evidence}\n"

                if getattr(f.remediation, "auto_patch", None):
                    body += f"**Remediation**: {f.remediation.description}\n\n```suggestion\n{f.remediation.auto_patch}\n```\n"
                elif f.remediation:
                    body += f"**Remediation**: {f.remediation}\n"

                if f.confidence_score is not None:
                    body += f"**Confidence**: {f.confidence_score}%\n"
                if f.source_scanner:
                    body += f"*(Scanner: {f.source_scanner})*\n"
                if f.fingerprint:
                    body += f"\n<!-- fingerprint: {f.fingerprint} -->\n"
                body += "\n---\n"

            comment_payload = {"body": body, "path": file_path, "side": side, "line": line}
            if end_line and end_line != line:
                comment_payload["start_line"] = line
                comment_payload["line"] = end_line

            review_comments.append((comment_payload, findings_group))

        if review_comments:
            payloads = [cp for cp, _ in review_comments]
            # Use commit_sha from the first finding
            commit_sha = review_comments[0][1][0].commit_sha

            try:
                review_payload = {
                    "commit_id": commit_sha,
                    "body": "### AI Code Review Findings",
                    "event": "COMMENT",
                    "comments": payloads,
                }
                response = await self.github_pr_service.post_pr_review(
                    self.owner, self.repo, self.pr_number, review_payload
                )

                # We can't map exact comment IDs back easily from a batched PR review post unless we parse the response.
                # Assuming success, we just skip setting github_comment_id or set it to the review ID.
                review_id = str(response.get("id"))
                for _, f_group in review_comments:
                    for f in f_group:
                        f.github_comment_id = review_id

            except Exception as e:
                logger.error(f"Failed to post PR review with inline comments: {e}")
                for _, f_group in review_comments:
                    fallback_findings.extend(f_group)

        if fallback_findings:
            fallback_body = "### Review Findings (Fallback)\n\nThe following findings could not be placed inline:\n\n"
            for f in fallback_findings:
                fallback_body += f"- **{f.file_path}:{f.line}** ({f.severity}): {f.message}\n"
                if f.evidence:
                    fallback_body += f"  - **Evidence**: {f.evidence}\n"

                if getattr(f.remediation, "auto_patch", None):
                    fallback_body += f"  - **Remediation**: {f.remediation.description}\n\n```suggestion\n{f.remediation.auto_patch}\n```\n"
                elif f.remediation:
                    fallback_body += f"  - **Remediation**: {f.remediation}\n"

                if f.confidence_score is not None:
                    fallback_body += f"  - **Confidence**: {f.confidence_score}%\n"
                if f.source_scanner:
                    fallback_body += f"  - *(Scanner: {f.source_scanner})*\n"
                if f.fingerprint:
                    fallback_body += f"\n<!-- fingerprint: {f.fingerprint} -->\n"

            try:
                await self.github_pr_service.post_pr_review(
                    self.owner, self.repo, self.pr_number, {"body": fallback_body, "event": "COMMENT"}
                )
            except Exception as e:
                logger.error(f"Failed to post fallback review summary: {e}")

    async def post_review_report(self, findings: List[SecurityFinding], test_results: TestResult):
        logger.info("Posting review report.")

    async def handle_human_approval(self):
        logger.info("Awaiting human approval workflow logic.")
