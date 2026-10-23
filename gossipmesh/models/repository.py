from enum import Enum


class IndexState(str, Enum):
    PENDING = "pending"
    INDEXED = "indexed"


class GithubAppInstallation:
    pass


class Repository:
    project_id: int = 1
    github_id: int = 1
