with open("gossipmesh/repository/vector_store.py", "r") as f:
    content = f.read()

content = "from typing import Any\n" + content

with open("gossipmesh/repository/vector_store.py", "w") as f:
    f.write(content)
