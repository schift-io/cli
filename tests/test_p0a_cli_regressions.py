from __future__ import annotations

import pytest
from click.testing import CliRunner

from schift_cli import client as client_module
from schift_cli import config as config_module
from schift_cli.commands import embed as embed_module
from schift_cli.commands.migrate import _mask_connection_string
from schift_cli.main import cli


@pytest.fixture
def isolated_config(monkeypatch, tmp_path):
    cfg_dir = tmp_path / ".schift"
    cfg_file = cfg_dir / "config.json"
    monkeypatch.setattr(config_module, "CONFIG_DIR", cfg_dir)
    monkeypatch.setattr(config_module, "CONFIG_FILE", cfg_file)
    return cfg_file


def _write_config_key(cfg_file, api_key: str) -> None:
    cfg_file.parent.mkdir(parents=True, exist_ok=True)
    cfg_file.write_text(f'{{"api_key": "{api_key}"}}\n')


def test_root_api_key_flag_beats_env_and_config(monkeypatch, isolated_config):
    _write_config_key(isolated_config, "cfg_key")
    monkeypatch.setenv("SCHIFT_API_KEY", "env_key")
    seen: dict[str, str | None] = {}

    class FakeClient:
        def __init__(self, api_key: str | None = None):
            seen["api_key"] = api_key

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return None

        def get(self, *args, **kwargs):
            return {"summary": {}}

    monkeypatch.setattr(client_module, "SchiftClient", FakeClient)

    result = CliRunner().invoke(cli, ["--api-key", "flag_key", "usage"])

    assert result.exit_code == 0, result.output
    assert seen["api_key"] == "flag_key"


def test_empty_explicit_api_key_rejects_without_fallback(monkeypatch, isolated_config):
    _write_config_key(isolated_config, "cfg_key")
    monkeypatch.setenv("SCHIFT_API_KEY", "env_key")

    with pytest.raises(Exception, match="API key cannot be empty"):
        client_module.SchiftClient(api_key="")

    result = CliRunner().invoke(cli, ["--api-key", "", "usage"])
    assert result.exit_code == 1
    assert "API key cannot be empty" in result.output


def test_embed_inline_text_before_model_reaches_command_path(monkeypatch):
    captured: dict[str, object] = {}

    class FakeClient:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return None

        def post(self, path, json=None):
            captured["path"] = path
            captured["json"] = json
            return {"embedding": [0.1, 0.2, 0.3]}

    monkeypatch.setattr(embed_module, "get_client", lambda: FakeClient())

    result = CliRunner().invoke(
        embed_module.embed,
        ["hello", "--model", "openai/text-embedding-3-large"],
    )

    assert result.exit_code == 0, result.output
    assert captured == {
        "path": "/embed",
        "json": {"text": "hello", "model": "openai/text-embedding-3-large"},
    }


@pytest.mark.parametrize(
    ("conn", "expected"),
    [
        (
            "pgvector://user:secret@db.example.com:5432/mydb?table=docs#frag",
            "pgvector://user:***@db.example.com:5432/mydb?table=docs#frag",
        ),
        ("pgvector://user@host/db", "pgvector://user@host/db"),
        ("chroma://localhost:8000", "chroma://localhost:8000"),
    ],
)
def test_mask_connection_string_preserves_non_password_userinfo(conn, expected):
    assert _mask_connection_string(conn) == expected
