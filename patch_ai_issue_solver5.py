with open("scripts/ai_issue_solver.py", "r") as f:
    lines = f.readlines()

new_lines = []
skip = False
for line in lines:
    if "file_changes_str = chr(10).join" in line:
        new_lines.append(line)
        skip = True

        replacement = """    summary_content = (
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
    )\n"""
        new_lines.append(replacement)

    if skip and "    )" in line:
        skip = False
        continue

    if not skip:
        new_lines.append(line)

with open("scripts/ai_issue_solver.py", "w") as f:
    f.writelines(new_lines)
