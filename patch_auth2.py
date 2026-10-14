with open("gossipmesh/api/routers/auth.py", "r") as f:
    content = f.read()

content = content.replace("from jwt import PyJWKClient  # type: ignore", "import jwt")

with open("gossipmesh/api/routers/auth.py", "w") as f:
    f.write(content)
