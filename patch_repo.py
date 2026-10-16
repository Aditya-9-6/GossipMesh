import re

with open("gossipmesh/api/routers/repositories.py", "r") as f:
    content = f.read()

content = re.sub(
    r"# Validate that an installation.*?raise AuthorizationError\(message=\"Installation does not belong to the requested organization\"\).*?def _sync_task.*?logger\.error",
    """    # Validate that an installation belongs to the requested organization.
    installation = db.query(GithubAppInstallation).filter(
        GithubAppInstallation.installation_id == request.installation_id,
        GithubAppInstallation.organization_id == request.organization_id
    ).first()
    if not installation:
        raise AuthorizationError(message='Installation does not belong to the requested organization')

    task_id = str(uuid.uuid4())""",
    content, flags=re.DOTALL)

with open("gossipmesh/api/routers/repositories.py", "w") as f:
    f.write(content)