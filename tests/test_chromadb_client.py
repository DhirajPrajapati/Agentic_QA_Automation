"""
test_chromadb_client — Tests for tools/chromadb_client._create_client().
Part of: QA Orchestrator
Phase: 6
Mock-safe: yes
"""
from unittest.mock import MagicMock, patch

import chromadb

from tools.chromadb_client import _create_client


def test_create_client_uses_http_client_when_host_is_set(monkeypatch):
    monkeypatch.setenv("CHROMADB_HOST", "chroma-server")
    monkeypatch.setenv("CHROMADB_PORT", "8000")

    captured: dict = {}

    def fake_http(host: str, port: int) -> MagicMock:
        captured["host"] = host
        captured["port"] = port
        return MagicMock()

    with patch.object(chromadb, "HttpClient", side_effect=fake_http):
        _create_client()

    assert captured["host"] == "chroma-server"
    assert captured["port"] == 8000


def test_create_client_uses_default_port_8000(monkeypatch):
    monkeypatch.setenv("CHROMADB_HOST", "chroma-server")
    monkeypatch.delenv("CHROMADB_PORT", raising=False)

    captured: dict = {}

    def fake_http(host: str, port: int) -> MagicMock:
        captured["port"] = port
        return MagicMock()

    with patch.object(chromadb, "HttpClient", side_effect=fake_http):
        _create_client()

    assert captured["port"] == 8000


def test_create_client_uses_custom_port(monkeypatch):
    monkeypatch.setenv("CHROMADB_HOST", "chroma-server")
    monkeypatch.setenv("CHROMADB_PORT", "9000")

    captured: dict = {}

    def fake_http(host: str, port: int) -> MagicMock:
        captured["port"] = port
        return MagicMock()

    with patch.object(chromadb, "HttpClient", side_effect=fake_http):
        _create_client()

    assert captured["port"] == 9000


def test_create_client_uses_persistent_client_without_host(monkeypatch):
    monkeypatch.delenv("CHROMADB_HOST", raising=False)

    captured: dict = {}

    def fake_persistent(path: str, settings: object) -> MagicMock:
        captured["path"] = path
        return MagicMock()

    with patch.object(chromadb, "PersistentClient", side_effect=fake_persistent):
        _create_client()

    assert "chromadb" in captured["path"]


def test_create_client_persistent_respects_chromadb_path_var(monkeypatch):
    import tools.chromadb_client as cc

    monkeypatch.delenv("CHROMADB_HOST", raising=False)
    monkeypatch.setattr(cc, "CHROMADB_PATH", "/custom/path/chromadb")

    captured: dict = {}

    def fake_persistent(path: str, settings: object) -> MagicMock:
        captured["path"] = path
        return MagicMock()

    with patch.object(chromadb, "PersistentClient", side_effect=fake_persistent):
        cc._create_client()

    assert captured["path"] == "/custom/path/chromadb"
