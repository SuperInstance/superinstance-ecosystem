"""Tests for the .bottle protocol."""

import pytest
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from bottle_protocol import (
    Bottle,
    observe,
    hypothesize,
    experiment,
    result,
    command,
    config_change,
    API_VERSION,
    VALID_KINDS,
)


class TestBottleCreation:
    def test_create_observation(self):
        b = observe("forgemaster", "spectral similarity is trivial", {"sim": 0.97, "repos": 3})
        assert b.kind == "observation"
        assert "trivial" in b.payload["what"]
        assert b.payload["sim"] == 0.97
        assert b.confidence == 0.5

    def test_create_hypothesis(self):
        b = hypothesize("forgemaster", "position-aware beats hash", confidence=0.8)
        assert b.kind == "hypothesis"
        assert b.confidence == 0.8
        assert b.payload["hypothesis"] == "position-aware beats hash"

    def test_create_experiment(self):
        b = experiment("test", "run benchmark", "speedup > 5x", method="A/B test")
        assert b.kind == "experiment"
        assert b.payload["expected_result"] == "speedup > 5x"
        assert b.payload["method"] == "A/B test"

    def test_create_result(self):
        b = result("test", "exp-123", "speedup = 6x", confidence=0.9)
        assert b.kind == "result"
        assert "exp-123" in b.references
        assert b.confidence == 0.9

    def test_create_command(self):
        b = command("forgemaster", "validate.arm.build", "oracle2", {"repo": "fastloop-guard"})
        assert b.kind == "command"
        assert b.payload["action"] == "validate.arm.build"
        assert b.payload["target"] == "oracle2"
        assert b.confidence == 1.0

    def test_create_config_change(self):
        b = config_change("metal-lathe", "temperature", 1.0, 0.5, "too aggressive")
        assert b.kind == "config"
        assert b.payload["setting"] == "temperature"
        assert b.payload["old"] == 1.0
        assert b.payload["new"] == 0.5


class TestBottleSerialization:
    def test_yaml_roundtrip(self):
        b = config_change("metal-lathe", "temperature", 1.0, 0.5, "too aggressive")
        yaml_str = b.to_yaml()
        loaded = Bottle.from_yaml(yaml_str)
        assert loaded.kind == "config"
        assert loaded.payload["setting"] == "temperature"
        assert loaded.confidence == 0.5
        assert loaded.bottle_id == b.bottle_id

    def test_yaml_contains_api_version(self):
        b = observe("test", "something", {})
        yaml_str = b.to_yaml()
        assert "apiVersion" in yaml_str
        assert API_VERSION in yaml_str

    def test_dict_roundtrip(self):
        b = observe("test", "something", {"key": "val"})
        d = b.to_dict()
        assert d["kind"] == "observation"
        assert d["payload"]["key"] == "val"


class TestBottleIO:
    def test_save_and_load(self, tmp_path):
        b = hypothesize("forgemaster", "position-aware beats hash", confidence=0.8)
        path = b.save(str(tmp_path))
        assert os.path.exists(path)
        loaded = Bottle.from_file(path)
        assert loaded.kind == "hypothesis"
        assert loaded.confidence == 0.8

    def test_load_directory(self, tmp_path):
        for i in range(5):
            observe("test", f"obs {i}", {}).save(str(tmp_path))
        bottles = Bottle.load_directory(str(tmp_path))
        assert len(bottles) == 5
        kinds = {b.kind for b in bottles}
        assert kinds == {"observation"}

    def test_load_empty_directory(self, tmp_path):
        bottles = Bottle.load_directory(str(tmp_path / "nonexistent"))
        assert bottles == []

    def test_save_creates_directory(self, tmp_path):
        nested = tmp_path / "deep" / "nested" / "dir"
        b = observe("test", "deep save", {})
        path = b.save(str(nested))
        assert os.path.exists(path)


class TestBottleReferences:
    def test_references_link(self):
        exp = experiment("test", "run benchmark", "speedup > 5x")
        res = result("test", exp.bottle_id, "speedup = 6x", confidence=0.9)
        assert exp.bottle_id in res.references

    def test_chain_of_references(self):
        obs = observe("test", "anomaly detected", {"value": 42})
        hyp = hypothesize("test", "caused by X", evidence=[obs.bottle_id])
        exp = experiment("test", "test X", "X is the cause")
        res = result("test", exp.bottle_id, "confirmed")
        # result() auto-references the experiment_id; verify it's there
        assert exp.bottle_id in res.references


class TestBottleValidation:
    def test_invalid_kind_raises(self):
        with pytest.raises(ValueError, match="Invalid kind"):
            Bottle(kind="invalid", source="test", payload={})

    def test_auto_timestamp(self):
        b = observe("test", "something", {})
        assert b.timestamp  # not empty
        assert "T" in b.timestamp  # ISO format

    def test_auto_bottle_id(self):
        b1 = observe("test", "something", {})
        b2 = observe("test", "something else", {})
        assert b1.bottle_id != b2.bottle_id
        assert len(b1.bottle_id) == 16  # blake2b digest_size=8 → 16 hex chars

    def test_explicit_bottle_id_preserved(self):
        b = Bottle(kind="observation", source="test", payload={}, bottle_id="custom-id-123")
        assert b.bottle_id == "custom-id-123"
