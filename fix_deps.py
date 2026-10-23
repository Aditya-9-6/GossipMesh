import re

with open("pyproject.toml", "r") as f:
    content = f.read()

# find dependencies = [...]
if 'dependencies = [' in content:
    deps_section = content.split('dependencies = [')[1].split(']')[0]
    if '"stripe"' not in deps_section:
        content = content.replace('dependencies = [\n', 'dependencies = [\n    "stripe",\n    "prometheus_client",\n')
        with open("pyproject.toml", "w") as f:
            f.write(content)
        print("Updated dependencies")
    else:
        print("Already has stripe")
else:
    print("Could not find dependencies section")
