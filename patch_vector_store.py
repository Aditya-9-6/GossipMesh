with open("gossipmesh/repository/vector_store.py", "r") as f:
    content = f.read()

content = content.replace("embedding: list[float] = Column(Vector(1536))", "embedding: Any = Column(Vector(1536))")
content = content.replace("id: str = Column(String, primary_key=True)", "id: Any = Column(String, primary_key=True)")
content = content.replace("repo_id: int = Column(Integer, index=True)", "repo_id: Any = Column(Integer, index=True)")
content = content.replace("filepath: str = Column(String, index=True)", "filepath: Any = Column(String, index=True)")
content = content.replace("content: str = Column(String)", "content: Any = Column(String)")
content = content.replace("metadata_json: dict = Column(JSON)", "metadata_json: Any = Column(JSON)")
content = content.replace("import JSON", "import JSON\nfrom typing import Any")

with open("gossipmesh/repository/vector_store.py", "w") as f:
    f.write(content)
