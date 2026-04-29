"""Tests for `schift migrate` CLI subcommands."""

import pytest
from click.testing import CliRunner

from schift_cli.commands import migrate as migrate_module
from schift_cli.commands.migrate import _parse_source_url, _parse_target


class FakeClient:
    def __init__(self, post_response=None, get_response=None):
        self._post_response = post_response or {}
        self._get_response = get_response or {}
        self.posts = []
        self.gets = []

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return None

    def post(self, path, json=None):
        self.posts.append((path, json))
        return self._post_response

    def get(self, path):
        self.gets.append(path)
        return self._get_response


# ── URL parser tests ──────────────────────────────────────────────────


def test_parse_pgvector_basic():
    src = _parse_source_url("pgvector://user:pass@db.example.com:5432/mydb?table=docs")
    assert src["kind"] == "pgvector"
    assert "postgresql://user:pass@db.example.com:5432/mydb" in src["config"]["dsn"]
    assert src["config"]["table"] == "docs"


def test_parse_pgvector_with_columns():
    src = _parse_source_url(
        "pgvector://localhost/mydb?table=docs&id_col=uuid&embedding_col=vec&text_col=body"
    )
    assert src["config"]["id_col"] == "uuid"
    assert src["config"]["embedding_col"] == "vec"
    assert src["config"]["text_col"] == "body"


def test_parse_pgvector_missing_table():
    import click

    with pytest.raises(click.BadParameter):
        _parse_source_url("pgvector://localhost/mydb")


def test_parse_chroma():
    src = _parse_source_url("chroma://localhost:8000?collection=docs")
    assert src["kind"] == "chroma"
    assert src["config"]["host"] == "localhost"
    assert src["config"]["port"] == 8000
    assert src["config"]["collection_name"] == "docs"


def test_parse_pinecone_requires_key():
    import click

    with pytest.raises(click.BadParameter):
        _parse_source_url("pinecone://my-index.svc.us-east-1-aws.pinecone.io")


def test_parse_pinecone_with_namespace():
    src = _parse_source_url(
        "pinecone://my-index.svc.us-east-1-aws.pinecone.io?api_key=pk_xxx&namespace=prod"
    )
    assert src["kind"] == "pinecone"
    assert src["config"]["api_key"] == "pk_xxx"
    assert src["config"]["namespace"] == "prod"


def test_parse_weaviate():
    src = _parse_source_url("weaviate://my-cluster.weaviate.network?class=Doc&api_key=wk_xxx")
    assert src["kind"] == "weaviate"
    assert src["config"]["url"] == "https://my-cluster.weaviate.network"
    assert src["config"]["class_name"] == "Doc"
    assert src["config"]["api_key"] == "wk_xxx"


def test_parse_unknown_scheme():
    import click

    with pytest.raises(click.BadParameter):
        _parse_source_url("ftp://example.com/data")


def test_parse_target_schift():
    assert _parse_target("schift://col_abc123") == "col_abc123"


def test_parse_target_rejects_other():
    import click

    with pytest.raises(click.BadParameter):
        _parse_target("postgres://col_abc")


# ── CLI subcommand tests ───────────────────────────────────────────────


def test_quote_command(monkeypatch):
    fake = FakeClient(post_response={
        "n_total_vectors": 250000,
        "src_dim": 1536,
        "free_tier": False,
        "rate_per_million_cents": 10,
        "quote_cents": 25,
        "quote_usd": 0.25,
    })
    monkeypatch.setattr(migrate_module, "get_client", lambda: fake)

    result = CliRunner().invoke(
        migrate_module.migrate,
        ["quote", "--from", "pgvector://localhost/db?table=docs"],
    )
    assert result.exit_code == 0, result.output
    assert fake.posts[0][0] == "/migrate/quote"
    assert fake.posts[0][1]["source"]["kind"] == "pgvector"
    assert fake.posts[0][1]["retain_on_cloud"] is True


def test_quote_command_export_out(monkeypatch):
    fake = FakeClient(post_response={
        "n_total_vectors": 1_000_000, "src_dim": 768, "free_tier": False,
        "rate_per_million_cents": 50, "quote_cents": 50, "quote_usd": 0.50,
    })
    monkeypatch.setattr(migrate_module, "get_client", lambda: fake)

    result = CliRunner().invoke(
        migrate_module.migrate,
        ["quote", "--from", "chroma://localhost:8000?collection=docs", "--export-out"],
    )
    assert result.exit_code == 0, result.output
    assert fake.posts[0][1]["retain_on_cloud"] is False


def test_start_command(monkeypatch):
    fake = FakeClient(post_response={
        "job_id": "job_abc", "state": "queued", "free_tier": True,
        "quote_cents": 0, "requires_payment": False,
    })
    monkeypatch.setattr(migrate_module, "get_client", lambda: fake)

    result = CliRunner().invoke(
        migrate_module.migrate,
        [
            "start",
            "--from", "pgvector://localhost/db?table=docs",
            "--to", "schift://col_xyz",
            "--method", "ridge",
        ],
    )
    assert result.exit_code == 0, result.output
    payload = fake.posts[0][1]
    assert payload["source"]["kind"] == "pgvector"
    assert payload["target_collection_id"] == "col_xyz"
    assert payload["method"] == "ridge"
    assert payload["retain_on_cloud"] is True


def test_status_command(monkeypatch):
    fake = FakeClient(get_response={
        "state": "ready", "progress": 1.0, "n_projected": 5183,
        "n_total": 5183, "cka": 0.852, "sample_retention": 0.995,
        "error": None,
    })
    monkeypatch.setattr(migrate_module, "get_client", lambda: fake)

    result = CliRunner().invoke(migrate_module.migrate, ["status", "job_abc"])
    assert result.exit_code == 0, result.output
    assert fake.gets == ["/migrate/job_abc"]
