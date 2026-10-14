with open("gossipmesh/core/security.py", "r") as f:
    content = f.read()

content = content.replace("    return encoded_jwt", "    return encoded_jwt if isinstance(encoded_jwt, str) else encoded_jwt.decode('utf-8')")

with open("gossipmesh/core/security.py", "w") as f:
    f.write(content)
