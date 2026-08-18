"""
test_collection_loader — Tests for tools/collection_loader.py.
Part of: QA Orchestrator
Phase: 1
Mock-safe: yes
"""
from tools.collection_loader import load_collection


def test_load_collection_returns_dict_when_found():
    collection = load_collection("investor", "login")
    assert collection is not None
    assert collection["info"]["name"] == "Investor Login"


def test_load_collection_returns_none_when_missing():
    assert load_collection("investor", "does_not_exist") is None
