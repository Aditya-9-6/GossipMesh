import sys

def add_health_readiness():
    filepath = "tests/test_health_readiness.py"
    content = """import pytest

def test_health():
    pass
"""
    with open(filepath, "w") as f:
        f.write(content)
add_health_readiness()
