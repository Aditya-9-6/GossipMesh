import sys

with open("tests/api/routers/test_organizations.py", "r") as f:
    content = f.read()

# I will simply use `setattr` to add attributes safely to any object inside `side_effect`.
content = content.replace(
    'if isinstance(obj, Organization):\n            obj.id = 1',
    'if isinstance(obj, Organization):\n            obj.id = 1\n        try:\n            if isinstance(obj, Repository):\n                obj.id = 1\n                obj.is_active = True\n                obj.is_archived = False\n                obj.installation_id = None\n        except AttributeError:\n            pass'
)

with open("tests/api/routers/test_organizations.py", "w") as f:
    f.write(content)
