from __future__ import annotations

import click

from schift_cli.client import get_client, SchiftAPIError
from schift_cli.display import error, info, print_kv, print_table, success


@click.group("db")
def db() -> None:
    """Manage vector buckets."""


@db.command("create")
@click.argument("name")
@click.option("--dim", "-d", type=int, required=True, help="Vector dimensions (e.g. 3072)")
@click.option("--metric", type=click.Choice(["cosine", "euclidean", "dot"]),
              default="cosine", show_default=True, help="Distance metric")
def create(name: str, dim: int, metric: str) -> None:
    """Create a new vector bucket."""
    try:
        with get_client() as client:
            data = client.post(
                "/collections",
                json={"name": name, "dimensions": dim, "metric": metric},
            )
    except SchiftAPIError as e:
        error(f"Failed to create bucket: {e.detail}")
        raise SystemExit(1)
    except click.ClickException:
        raise

    bucket = data.get("bucket", data.get("collection", data))
    success(f"Bucket '{name}' created (id: {bucket.get('id', '-')})")


@db.command("list")
def list_collections() -> None:
    """List all vector buckets."""
    try:
        with get_client() as client:
            data = client.get("/collections")
    except SchiftAPIError as e:
        error(f"Failed to list buckets: {e.detail}")
        raise SystemExit(1)
    except click.ClickException:
        raise

    collections = data.get("buckets", data.get("collections", []))
    if not collections:
        info("No buckets found. Create one with `schift db create`.")
        return

    rows = [
        (
            c.get("name", ""),
            str(c.get("dimensions", "")),
            c.get("metric", ""),
            str(c.get("vector_count", "")),
            c.get("created_at", ""),
        )
        for c in collections
    ]
    print_table(
        "Vector Buckets",
        ["Name", "Dimensions", "Metric", "Vectors", "Created"],
        rows,
    )


@db.command("stats")
@click.argument("name")
def stats(name: str) -> None:
    """Show statistics for a bucket."""
    try:
        with get_client() as client:
            data = client.get(f"/collections/{name}/stats")
    except SchiftAPIError as e:
        if e.status_code == 404:
            error(f"Bucket not found: {name}")
        else:
            error(f"Failed to get stats: {e.detail}")
        raise SystemExit(1)
    except click.ClickException:
        raise

    s = data.get("stats", data)
    print_kv(f"Bucket: {name}", {
        "Vectors": s.get("vector_count", "-"),
        "Dimensions": s.get("dimensions", "-"),
        "Metric": s.get("metric", "-"),
        "Index Type": s.get("index_type", "-"),
        "Storage Size": s.get("storage_size", "-"),
        "Created": s.get("created_at", "-"),
        "Last Updated": s.get("updated_at", "-"),
    })
