with open("scripts/ai_pr_reviewer.py", "r") as f:
    content = f.read()

content = content.replace("import ast\nimport ast\n", "import ast\n")
content = content.replace("import ast\n#!/usr/bin/env python3\n", "#!/usr/bin/env python3\n")
content = content.replace("import ast\n\ndef extract_ast_metadata", "def extract_ast_metadata")

with open("scripts/ai_pr_reviewer.py", "w") as f:
    f.write(content)
