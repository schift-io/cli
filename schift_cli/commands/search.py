from __future__ import annotations

import json

import click

from schift_cli.client import SchiftAPIError, get_client, resolve_bucket
from schift_cli.display import console, error, print_table


@click.command("search")
@click.argument("text")
@click.option("--bucket", "-b", default=None, help="Bucket name or bucket ID")
@click.option("--collection", "-c", default=None, help="Deprecated alias for --bucket")
@click.option("--top-k", "-k", type=int, default=10, show_default=True, help="Number of results to return")
@click.option("--model", "-m", default=None, help="Embedding model to use for the query")
@click.option("--mode", type=click.Choice(["hybrid", "semantic", "keyword"]), default="hybrid", show_default=True, help="Retrieval mode")
@click.option("--rerank/--no-rerank", default=False, show_default=True, help="Enable reranking")
@click.option("--threshold", type=float, default=None, help="Minimum similarity score filter")
@click.option("--filter", "filter_json", default=None, help="JSON filter envelope")
def search(
    text: str,
    bucket: str | None,
    collection: str | None,
    top_k: int,
    model: str | None,
    mode: str,
    rerank: bool,
    threshold: float | None,
    filter_json: str | None,
) -> None:
    """Run bucket search with the canonical search surface."""
    if bool(bucket) == bool(collection):
        raise click.ClickException("Pass exactly one of --bucket or --collection.")

    filter_payload = None
    if filter_json is not None:
        try:
            filter_payload = json.loads(filter_json)
        except json.JSONDecodeError as exc:
            raise click.ClickException(f"Invalid --filter JSON: {exc}") from exc

    payload: dict[str, object] = {
        "query": text,
        "top_k": top_k,
        "mode": mode,
        "rerank": rerank,
    }
    if model:
        payload["model"] = model
    if filter_payload is not None:
        payload["filter"] = filter_payload

    try:
        with get_client() as client:
            if bucket:
                resolved_bucket = resolve_bucket(client, bucket)
                title = f"Bucket Search ({resolved_bucket.get('name', bucket)})"
                data = client.post(f"/buckets/{resolved_bucket['id']}/search", json=payload)
            else:
                title = f"Bucket Search ({collection})"
                data = client.post(f"/buckets/{collection}/search", json=payload)
    except SchiftAPIError as exc:
        error(f"Search failed: {exc.detail}")
        raise SystemExit(1)
    except click.ClickException:
        raise

    results = data.get("results", []) if isinstance(data, dict) else data
    if not isinstance(results, list):
        results = []
    if threshold is not None:
        results = [item for item in results if isinstance(item, dict) and float(item.get("score", 0)) >= threshold]

    if not results:
        console.print("No results found.")
        return

    rows = [
        (
            str(index + 1),
            item.get("id", item.get("chunk_id", "-")),
            f"{float(item.get('score', 0)):.4f}",
            _truncate(_result_text(item), 80),
        )
        for index, item in enumerate(results)
        if isinstance(item, dict)
    ]

    print_table(
        title,
        ["#", "ID", "Score", "Text"],
        rows,
        caption=f"Query: \"{text}\" | top-k: {top_k}",
    )


def _result_text(item: dict) -> str:
    metadata = item.get("metadata")
    if isinstance(metadata, dict):
        for key in ("text", "chunk_text", "content", "source"):
            value = metadata.get(key)
            if isinstance(value, str) and value:
                return value
    for key in ("text", "chunk_text", "content", "locator"):
        value = item.get(key)
        if isinstance(value, str) and value:
            return value
    return "-"


def _truncate(value: str, max_len: int) -> str:
    if len(value) <= max_len:
        return value
    return value[: max_len - 3] + "..."
