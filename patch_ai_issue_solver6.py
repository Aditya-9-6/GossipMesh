with open("scripts/ai_issue_solver.py", "r") as f:
    content = f.read()

# Replace the specific syntax issue
content = content.replace("f\"*Closes #{args.issue_number}*\\n\"", "f\"*Closes #{args.issue_number}*\\n\"")

with open("scripts/ai_issue_solver.py", "w") as f:
    f.write(content)
