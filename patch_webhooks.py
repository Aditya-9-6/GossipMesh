import re
with open("gossipmesh/api/webhooks.py", "r") as f:
    content = f.read()

content = re.sub(
r"<<<<<<< HEAD\nfrom gossipmesh.models.repository import GithubAppInstallation\n=======\nfrom gossipmesh.models.jobs import BackgroundJob\n\nfrom gossipmesh.worker.tasks import process_pr_review, process_issue_solver, process_ci_fixer\n>>>>>>> origin/main",
"""from gossipmesh.models.repository import GithubAppInstallation
from gossipmesh.models.jobs import BackgroundJob

from gossipmesh.worker.tasks import process_pr_review, process_issue_solver, process_ci_fixer""",
content)

content = re.sub(
r"<<<<<<< HEAD\ndef dispatch_webhook\(event: str, payload: dict, background_tasks: BackgroundTasks, db: Session\):\n    action = payload.get\(\"action\"\)\n    if event == \"installation\":.*?=======\ndef dispatch_webhook\(event: str, payload: dict, db: Session\):.*?>>>>>>> origin/main",
"""def dispatch_webhook(event: str, payload: dict, db: Session):
    action = payload.get("action")
    if event == "installation":
        installation = payload.get("installation", {})
        account = installation.get("account", {})
        inst_id = installation.get("id")

        if action == "created":
            record = GithubAppInstallation(
                installation_id=inst_id,
                account_name=account.get("login", ""),
                target_type=account.get("type", "Unknown"),
                target_id=account.get("id", 0),
                repository_selection=installation.get("repository_selection", "all"),
                permissions=installation.get("permissions", {})
            )
            db.add(record)
            db.flush()

            audit = AuditEvent(
                action="installation.created",
                details={"installation_id": inst_id, "account": account.get("login")}
            )
            db.add(audit)

        elif action == "deleted":
            db.query(GithubAppInstallation).filter(GithubAppInstallation.installation_id == inst_id).delete()
            db.flush()

            audit = AuditEvent(
                action="installation.deleted",
                details={"installation_id": inst_id}
            )
            db.add(audit)

        elif action == "suspend":
            sender_login = payload.get("sender", {}).get("login")
            db.query(GithubAppInstallation).filter(GithubAppInstallation.installation_id == inst_id).update({
                "suspended_at": func.now(),
                "suspended_by": sender_login
            })
            db.flush()

            audit = AuditEvent(
                action="installation.suspended",
                details={"installation_id": inst_id, "suspended_by": sender_login}
            )
            db.add(audit)

        elif action == "unsuspend":
            db.query(GithubAppInstallation).filter(GithubAppInstallation.installation_id == inst_id).update({
                "suspended_at": None,
                "suspended_by": None
            })
            db.flush()

            audit = AuditEvent(
                action="installation.unsuspended",
                details={"installation_id": inst_id}
            )
            db.add(audit)

    elif event == "pull_request":
        if action in ["opened", "synchronize", "reopened"]:
            pr_data = payload.get("pull_request", {})
            task_id = str(uuid.uuid4())
            job_record = BackgroundJob(
                task_id=task_id,
                task_name="process_pr_review"
            )
            db.add(job_record)
            db.commit()
            process_pr_review.apply_async(args=[pr_data], task_id=task_id)

    # Milestone 7: Issue Solver
    elif event == "issues":
        if action == "opened":
            issue_data = payload.get("issue", {})
            task_id = str(uuid.uuid4())
            job_record = BackgroundJob(
                task_id=task_id,
                task_name="process_issue_solver"
            )
            db.add(job_record)
            db.commit()
            process_issue_solver.apply_async(args=[issue_data], task_id=task_id)

    # Milestone 7: CI Fixer (Triggered by workflow_run completion)
    elif event == "workflow_run":
        run_data = payload.get("workflow_run", {})
        if action == "completed" and run_data.get("conclusion") == "failure":
            task_id = str(uuid.uuid4())
            job_record = BackgroundJob(
                task_id=task_id,
                task_name="process_ci_fixer"
            )
            db.add(job_record)
            db.commit()
            process_ci_fixer.apply_async(args=[run_data], task_id=task_id)

    elif event == "issue_comment":
        if action == "created":
            # Handle human approval workflow or explicit commands
            comment_body = payload.get("comment", {}).get("body", "")
            if "/approve" in comment_body:
                logger.info("Human approval received via comment.")
                # Trigger approval state transition logic here""",
content, flags=re.DOTALL)

content = re.sub(
r"<<<<<<< HEAD\n        dispatch_webhook\(event, payload, background_tasks, db\)\n=======\n        dispatch_webhook\(event, payload, db\)\n>>>>>>> origin/main",
"        dispatch_webhook(event, payload, db)",
content)

content = re.sub(
r"<<<<<<< HEAD\n        dispatch_webhook\(event_record.event, event_record.payload, background_tasks, db\)\n=======\n        dispatch_webhook\(event_record.event, event_record.payload, db\)\n>>>>>>> origin/main",
"        dispatch_webhook(event_record.event, event_record.payload, db)",
content)

with open("gossipmesh/api/webhooks.py", "w") as f:
    f.write(content)
