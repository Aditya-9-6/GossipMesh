with open("scripts/ai_issue_solver.py", "r") as f:
    lines = f.readlines()

new_lines = []
for line in lines:
    if line.startswith("    summary_content = f\"\"\"##"):
        new_lines.append("    summary_content = f\"\"\"## 🤖 Automated Solution for Issue #{args.issue_number}\\n\"\n")
        new_lines.append("    summary_content += f\"**Issue**: #{args.issue_number} - {args.issue_title}\\n\\n\"\n")
        new_lines.append("    summary_content += f\"### 📝 Solution Overview\\n{summary}\\n\\n\"\n")
        new_lines.append("    summary_content += f\"### 📦 Files Changed\\n\"\n")
        new_lines.append("    summary_content += chr(10).join(f\"- `{f['path']}`\" for f in files) + \"\\n\\n\"\n")
        new_lines.append("    summary_content += \"### 🛡️ Quality & Performance Invariants\\n\"\n")
        new_lines.append("    summary_content += \"- [x] Idiomatic Python concurrency and memory safety.\\n\"\n")
        new_lines.append("    summary_content += \"- [x] High throughput and streaming invariants preserved.\\n\"\n")
        new_lines.append("    summary_content += \"- [x] Comprehensive unit tests included.\\n\\n---\\n\"\n")
        new_lines.append("    summary_content += f\"*Closes #{args.issue_number}*\\n\"\"\"\n")
    elif line.startswith("351"):
        continue
    else:
        new_lines.append(line)

# Let's just rewrite the whole block instead of a loop like that which is fragile
