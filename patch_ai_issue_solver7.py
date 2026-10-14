with open("scripts/ai_issue_solver.py", "r") as f:
    content = f.read()

content = content.replace('    keywords = [w for w in (args.issue_title + " " + args.issue_body).split() if len(w) > 3]', '')

with open("scripts/ai_issue_solver.py", "w") as f:
    f.write(content)
