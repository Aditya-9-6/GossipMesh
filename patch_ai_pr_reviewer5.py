with open("scripts/ai_pr_reviewer.py", "r") as f:
    content = f.read()

content = content.replace("import ast\n\"\"\"\n", "\"\"\"\n")

content = content.replace("import os", "import ast\nimport os")

with open("scripts/ai_pr_reviewer.py", "w") as f:
    f.write(content)
