import json
import pytest
from gossipmesh.semantic_cache import SemanticCache


def test_load_metadata_invalid_json(tmp_path):
    cache = SemanticCache(cache_dir=str(tmp_path))
    cache.metadata_file.write_text("invalid json {", encoding="utf-8")
    metadata = cache._load_metadata()
    assert metadata == {}


def test_load_metadata_valid_json(tmp_path):
    cache = SemanticCache(cache_dir=str(tmp_path))
    cache.metadata_file.write_text('{"key": "val"}', encoding="utf-8")
    metadata = cache._load_metadata()
    assert metadata == {"key": "val"}


def test_cache_get_set(tmp_path):
    cache = SemanticCache(cache_dir=str(tmp_path))
    cache.set("foo", "bar")
    assert cache.get("foo") == "bar"
