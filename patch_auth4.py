with open("gossipmesh/api/routers/auth.py", "r") as f:
    content = f.read()

content = content.replace("jwks_client = jwt.PyJWKClient(jwks_uri)", "jwks_client: Any = jwt.PyJWKClient(jwks_uri)  # type: ignore")

with open("gossipmesh/api/routers/auth.py", "w") as f:
    f.write(content)
