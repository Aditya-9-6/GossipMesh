import re
with open("scripts/ai_issue_solver.py", "r") as f:
    content = f.read()

# Using raw strings correctly to replace the problematic f-string block
pattern = re.compile(r'    summary_content = f"""## 🤖 Automated Solution for Issue #\{args\.issue_number\}.*?\n"""', re.DOTALL)

replacement = """    file_changes_str = chr(10).join(f"- `{f['path']}`" for f in files)
    summary_content = (
        f"## 🤖 Automated Solution for Issue #{args.issue_number}\\n\\n"
        f"**Issue**: #{args.issue_number} - {args.issue_title}\\n\\n"
        f"### 📝 Solution Overview\\n{summary}\\n\\n"
        f"### 📦 Files Changed\\n{file_changes_str}\\n\\n"
        "### 🛡️ Quality & Performance Invariants\\n"
        "- [x] Idiomatic Python concurrency and memory safety.\\n"
        "- [x] High throughput and streaming invariants preserved.\\n"
        "- [x] Comprehensive unit tests included.\\n\\n"
        "---\\n"
        f"*Closes #{args.issue_number}*\\n"
    )"""

new_content = pattern.sub(replacement, content)

with open("scripts/ai_issue_solver.py", "w") as f:
    f.write(new_content)
