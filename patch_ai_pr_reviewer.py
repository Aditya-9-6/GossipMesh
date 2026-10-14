with open("scripts/ai_pr_reviewer.py", "r") as f:
    content = f.read()

content = content.replace("    import ast", "")
content = "import ast\n" + content

content = content.replace("        with urllib.request.urlopen(req, timeout=15) as resp:", "        with urllib.request.urlopen(req, timeout=15):")

with open("scripts/ai_pr_reviewer.py", "w") as f:
    f.write(content)
