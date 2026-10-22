import pytest
from gossipmesh.runtime.patch_validator import PatchValidator, PatchValidationError


def test_patch_validator_valid_files(tmp_path):
    validator = PatchValidator(workspace=tmp_path)
    patch_set = {
        "gossipmesh/new_module.py": "def hello():\n    return 'world'\n",
        "docs/spec.json": '{"name": "GossipMesh", "version": "1.0"}',
    }

    is_valid, errors = validator.validate_patch_set(patch_set)
    assert is_valid is True
    assert len(errors) == 0


def test_patch_validator_rejects_absolute_path(tmp_path):
    validator = PatchValidator(workspace=tmp_path)
    with pytest.raises(PatchValidationError) as exc:
        validator.validate_path("/etc/passwd")
    assert "Forbidden absolute path" in str(exc.value)


def test_patch_validator_rejects_path_traversal(tmp_path):
    validator = PatchValidator(workspace=tmp_path)
    with pytest.raises(PatchValidationError) as exc:
        validator.validate_path("../outside.py")
    assert "Path traversal" in str(exc.value)


def test_patch_validator_rejects_forbidden_files(tmp_path):
    validator = PatchValidator(workspace=tmp_path)
    forbidden_examples = [
        ".env",
        ".git/config",
        "secret.key",
        "cert.pem",
        ".gemini_keys",
        "id_rsa",
    ]
    for path in forbidden_examples:
        with pytest.raises(PatchValidationError) as exc:
            validator.validate_path(path)
        assert "Forbidden file pattern" in str(exc.value)


def test_patch_validator_rejects_invalid_python_syntax(tmp_path):
    validator = PatchValidator(workspace=tmp_path)
    with pytest.raises(PatchValidationError) as exc:
        validator.validate_content("gossipmesh/broken.py", "def foo(:\n    pass")
    assert "Python syntax error" in str(exc.value)


def test_patch_validator_rejects_invalid_json(tmp_path):
    validator = PatchValidator(workspace=tmp_path)
    with pytest.raises(PatchValidationError) as exc:
        validator.validate_content("config/broken.json", '{"key": "value",}')
    assert "Invalid JSON syntax" in str(exc.value)


def test_patch_validator_rejects_exceeded_file_count(tmp_path):
    validator = PatchValidator(workspace=tmp_path, max_files=2)
    files = {
        "f1.py": "x = 1",
        "f2.py": "y = 2",
        "f3.py": "z = 3",
    }
    with pytest.raises(PatchValidationError) as exc:
        validator.validate_patch_set(files)
    assert "Total files limit exceeded" in str(exc.value)
