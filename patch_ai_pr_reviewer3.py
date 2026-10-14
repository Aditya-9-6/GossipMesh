with open("scripts/ai_pr_reviewer.py", "r") as f:
    content = f.read()

content = "import ast\n" + content

with open("scripts/ai_pr_reviewer.py", "w") as f:
    f.write(content)
