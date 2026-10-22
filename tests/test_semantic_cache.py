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
    data = {"key1": {"key_text": "text1", "embedding": [0.1, 0.2]}}
    cache.metadata_file.write_text(json.dumps(data), encoding="utf-8")
    metadata = cache._load_metadata()
    assert metadata == data

def test_load_metadata_missing_file(tmp_path):
    cache = SemanticCache(cache_dir=str(tmp_path))
    assert not cache.metadata_file.exists()
    metadata = cache._load_metadata()
    assert metadata == {}
