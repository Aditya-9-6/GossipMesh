with open("gossipmesh/repository/github.py", "r") as f:
    content = f.read()

content = content.replace("        return jwt.encode(payload, self.private_key, algorithm=\"RS256\")", "        encoded = jwt.encode(payload, self.private_key, algorithm=\"RS256\")\n        return encoded if isinstance(encoded, str) else encoded.decode(\"utf-8\")")

with open("gossipmesh/repository/github.py", "w") as f:
    f.write(content)
