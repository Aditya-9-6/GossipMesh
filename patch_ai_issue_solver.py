import re

with open("scripts/ai_issue_solver.py", "r") as f:
    content = f.read()

new_content = re.sub(
    r'    summary_content = f"""## 🤖 Automated Solution for Issue #\{args.issue_number\}\n\n\*\*Issue\*\*: #\{args.issue_number\} - \{args.issue_title\}\n\n### 📝 Solution Overview\n\n### 🛡️ Quality & Performance Invariants\n- \[x\] Idiomatic Python concurrency and memory safety.\n- \[x\] High throughput and streaming invariants preserved.\n- \[x\] Comprehensive unit tests included.\n\n---\n\*Closes #\{args.issue_number\}\*\n"""',
    r'    summary_content = f"## 🤖 Automated Solution for Issue #{args.issue_number}\n\n**Issue**: #{args.issue_number} - {args.issue_title}\n\n### 📝 Solution Overview\n\n### 🛡️ Quality & Performance Invariants\n- [x] Idiomatic Python concurrency and memory safety.\n- [x] High throughput and streaming invariants preserved.\n- [x] Comprehensive unit tests included.\n\n---\n*Closes #{args.issue_number}*\n"',
    content
)

with open("scripts/ai_issue_solver.py", "w") as f:
    f.write(new_content)
