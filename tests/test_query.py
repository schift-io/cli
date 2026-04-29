from click.testing import CliRunner

from schift_cli.commands import query as query_module


class FakeClient:
    def __init__(self):
        self.posts = []

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return None

    def post(self, path, json=None):
        self.posts.append((path, json))
        return {"results": []}


def test_query_uses_bucket_search_endpoint(monkeypatch):
    client = FakeClient()
    monkeypatch.setattr(query_module, "get_client", lambda: client)
    monkeypatch.setattr(
        query_module,
        "resolve_bucket",
        lambda _client, bucket: {"id": f"{bucket}-id"},
    )

    result = CliRunner().invoke(query_module.query, ["hello", "--bucket", "docs"])

    assert result.exit_code == 0
    assert client.posts == [
        ("/buckets/docs-id/search", {"query": "hello", "top_k": 10}),
    ]


def test_query_keeps_collection_alias(monkeypatch):
    client = FakeClient()
    monkeypatch.setattr(query_module, "get_client", lambda: client)

    result = CliRunner().invoke(
        query_module.query,
        ["hello", "--collection", "legacy-docs"],
    )

    assert result.exit_code == 0
    assert client.posts == [
        ("/buckets/legacy-docs/search", {"query": "hello", "top_k": 10}),
    ]
