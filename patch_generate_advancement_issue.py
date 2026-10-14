with open("scripts/generate_advancement_issue.py", "r") as f:
    content = f.read()

content = content.replace("    issues_info = []\n    try:", "    try:")

with open("scripts/generate_advancement_issue.py", "w") as f:
    f.write(content)
