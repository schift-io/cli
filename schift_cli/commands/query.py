from __future__ import annotations

import click

from schift_cli.client import get_client, resolve_bucket, SchiftAPIError
from schift_cli.display import console, error, print_table


@click.command("query")
@click.argument("text")
@click.option("--bucket", "-b", default=None, help="Bucket name or bucket ID to search")
@click.option("--collection", "-c", default=None, help="Deprecated alias for --bucket")
@click.option("--top-k", "-k", type=int, default=10, show_default=True,
              help="Number of results to return")
@click.option("--model", "-m", default=None, help="Embedding model to use for the query (uses bucket default if omitted)")
@click.option("--threshold", type=float, default=None, help="Minimum similarity score filter")
def query(text: str, bucket: str | None, collection: str | None, top_k: int, model: str | None, threshold: float | None) -> None:
    """Compatibility alias for bucket search.

    TEXT is the search query string.
    """
    resolved_bucket = bucket or collection
    if not resolved_bucket:
        raise click.ClickException("Pass --bucket. --collection remains as a deprecated alias.")

    payload: dict = {
        "query": text,
        "top_k": top_k,
    }
    if model:
        payload["model"] = model
    if threshold is not None:
        payload["threshold"] = threshold

    try:
        with get_client() as client:
            if bucket:
                bucket_id = resolve_bucket(client, bucket)["id"]
            else:
                bucket_id = collection
            data = client.post(f"/buckets/{bucket_id}/search", json=payload)
    except SchiftAPIError as e:
        error(f"Query failed: {e.detail}")
        raise SystemExit(1)
    except click.ClickException:
        raise

    results = data.get("results", [])
    if not results:
        console.print("No results found.")
        return

    rows = [
        (
            str(i + 1),
            r.get("id", "-"),
            f"{r.get('score', 0):.4f}",
            _truncate(r.get("text", r.get("metadata", {}).get("text", "-")), 80),
        )
        for i, r in enumerate(results)
    ]

    print_table(
        f"Search Results ({resolved_bucket})",
        ["#", "ID", "Score", "Text"],
        rows,
        caption=f"Query: \"{text}\" | top-k: {top_k}",
    )


def _truncate(s: str, max_len: int) -> str:
    if len(s) <= max_len:
        return s
    return s[: max_len - 3] + "..."
