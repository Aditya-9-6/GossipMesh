with open("scripts/ai_pr_reviewer.py", "r") as f:
    content = f.read()

content = content.replace("import ast\n#!/usr/bin/env python3\n", "#!/usr/bin/env python3\nimport ast\n")

with open("scripts/ai_pr_reviewer.py", "w") as f:
    f.write(content)
