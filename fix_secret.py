import sys, os

file_path = "gossipmesh/security/secret_scanner.py"
if os.path.exists(file_path):
    with open(file_path, "r") as f:
        content = f.read()
    if "from typing import " in content and "Any" not in content.split("from typing import ")[1].split("\n")[0]:
        content = content.replace("from typing import ", "from typing import Any, ")
    elif "import typing" not in content:
        content = "from typing import Any\n" + content
    with open(file_path, "w") as f:
        f.write(content)
