with open("gossipmesh/api/routers/auth.py", "r") as f:
    content = f.read()

content = content.replace("nonce, code_verifier = state_data.split(\":\")", "nonce, code_verifier = state_data.decode(\"utf-8\").split(\":\") if isinstance(state_data, bytes) else state_data.split(\":\")")
content = content.replace("credential.sub = sub", "credential.sub = str(sub)")
content = content.replace("from jwt import PyJWKClient", "from jwt import PyJWKClient  # type: ignore")

with open("gossipmesh/api/routers/auth.py", "w") as f:
    f.write(content)
