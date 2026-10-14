with open("gossipmesh/api/routers/auth.py", "r") as f:
    content = f.read()

content = content.replace("jwks_client = PyJWKClient(jwks_uri)", "jwks_client = jwt.PyJWKClient(jwks_uri)")

with open("gossipmesh/api/routers/auth.py", "w") as f:
    f.write(content)
