from enum import Enum


class OrganizationRole(str, Enum):
    owner = "owner"
    admin = "admin"
    developer = "developer"
    member = "member"
