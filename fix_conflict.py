with open("gossipmesh/api/routers/runs.py", "r") as f:
    content = f.read()

content = content.replace("<<<<<<< Updated upstream\n# Dependency to get the database session\n=======\n>>>>>>> Stashed changes\n", "")

with open("gossipmesh/api/routers/runs.py", "w") as f:
    f.write(content)

with open("tests/test_runs.py", "r") as f:
    content = f.read()
print(content)
