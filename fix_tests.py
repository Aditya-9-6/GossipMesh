import sys

with open("tests/api/routers/test_organizations.py", "r") as f:
    content = f.read()

# Let's fix test_organizations once and for all: mock_db_session fixture from conftest returns a real session!
# In the test file, test_create_organization and others ASSUME it's a MagicMock and set .query.return_value!
# This only works if `mock_db_session` IS a MagicMock. If conftest gives a real one, the test crashes with AttributeError.
# So I just need to override the fixture in the file!

fixture = """
@pytest.fixture
def mock_db_session():
    return MagicMock()
"""
if "def mock_db_session():" not in content:
    content = content.replace("import pytest", "import pytest\n" + fixture)

with open("tests/api/routers/test_organizations.py", "w") as f:
    f.write(content)
