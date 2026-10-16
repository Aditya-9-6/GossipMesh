from typing import List, Optional

class Organization:
    def __init__(self, name: str, members: List[str] = None, role: Optional[str] = None):
        self.name = name
        self.members = members or []
        self.role = role