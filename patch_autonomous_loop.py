with open("scripts/autonomous_loop.py", "r") as f:
    content = f.read()

content = content.replace("            merge_out = run_cmd([\"gh\", \"pr\", \"merge\", str(pr_num), \"--squash\", \"--admin\"], cwd=workspace)", "            run_cmd([\"gh\", \"pr\", \"merge\", str(pr_num), \"--squash\", \"--admin\"], cwd=workspace)")

with open("scripts/autonomous_loop.py", "w") as f:
    f.write(content)
