from __future__ import annotations

import click
from urllib.parse import urlsplit, urlunsplit

from schift_cli.client import get_client, SchiftAPIError
from schift_cli.display import console, error, info, print_kv, spinner, success


@click.group("migrate")
def migrate() -> None:
    """Fit projection matrices and migrate vector databases."""


@migrate.command("fit")
@click.option("--source", "-s", required=True, help="Source embedding model ID")
@click.option("--target", "-t", required=True, help="Target embedding model ID")
@click.option("--sample", type=float, default=0.1, show_default=True,
              help="Fraction of data to sample for fitting (0.0-1.0)")
def fit(source: str, target: str, sample: float) -> None:
    """Fit a projection matrix between two embedding models.

    The projection is computed server-side. You never see the matrix --
    Schift stores it and returns a projection ID for use in `migrate run`.
    """
    if not 0.0 < sample <= 1.0:
        raise click.BadParameter("Sample must be between 0 and 1.", param_hint="--sample")

    info(f"Fitting projection: {source} -> {target} (sample={sample})")

    try:
        with get_client() as client:
            with spinner("Fitting projection matrix...") as progress:
                progress.add_task("Fitting projection matrix...", total=None)
                result = client.post(
                    "/migrate/fit",
                    json={
                        "source_model": source,
                        "target_model": target,
                        "sample_fraction": sample,
                    },
                )
    except SchiftAPIError as e:
        error(f"Fit failed: {e.detail}")
        raise SystemExit(1)
    except click.ClickException:
        raise

    projection = result.get("projection", result)
    proj_id = projection.get("id", "unknown")

    print_kv("Projection Created", {
        "Projection ID": proj_id,
        "Source Model": source,
        "Target Model": target,
        "Sample Fraction": sample,
        "Status": projection.get("status", "ready"),
        "Quality (R2)": projection.get("r2_score", "-"),
    })

    success(f"Use this projection ID to migrate: schift migrate run --projection {proj_id}")


@migrate.command("run")
@click.option("--projection", "-p", required=True, help="Projection ID from `migrate fit`")
@click.option("--db", required=True, help="Database connection string (e.g. pgvector://...)")
@click.option("--dry-run", is_flag=True, default=False, help="Preview the migration without applying changes")
@click.option("--batch-size", type=int, default=1000, show_default=True,
              help="Number of vectors to migrate per batch")
def run(projection: str, db: str, dry_run: bool, batch_size: int) -> None:
    """Apply a projection to migrate vectors in a database.

    Use --dry-run first to preview the migration plan.
    """
    mode = "DRY RUN" if dry_run else "LIVE"
    info(f"Migration [{mode}]: projection={projection}")
    info(f"Database: {_mask_connection_string(db)}")

    if not dry_run:
        click.confirm(
            "This will modify vectors in your database. Continue?",
            abort=True,
        )

    try:
        with get_client() as client:
            with spinner("Running migration...") as progress:
                progress.add_task("Running migration...", total=None)
                result = client.post(
                    "/migrate/run",
                    json={
                        "projection_id": projection,
                        "db_connection": db,
                        "dry_run": dry_run,
                        "batch_size": batch_size,
                    },
                )
    except SchiftAPIError as e:
        error(f"Migration failed: {e.detail}")
        raise SystemExit(1)
    except click.ClickException:
        raise

    migration = result.get("migration", result)

    print_kv(f"Migration Result ({mode})", {
        "Vectors Processed": migration.get("vectors_processed", "-"),
        "Vectors Skipped": migration.get("vectors_skipped", "-"),
        "Duration": migration.get("duration", "-"),
        "Status": migration.get("status", "-"),
    })

    if dry_run:
        info("No changes were applied. Remove --dry-run to execute.")
    else:
        success("Migration complete.")


def _mask_connection_string(conn: str) -> str:
    """Hide only the password in connection strings for display."""
    parsed = urlsplit(conn)
    if not parsed.password or not parsed.netloc:
        return conn

    username = parsed.username or ""
    hostname = parsed.hostname or ""
    auth = f"{username}:***@" if username else "***@"
    port = f":{parsed.port}" if parsed.port is not None else ""

    return urlunsplit((
        parsed.scheme,
        f"{auth}{hostname}{port}",
        parsed.path,
        parsed.query,
        parsed.fragment,
    ))


# ──────────────────────────────────────────────────────────────────────
# /v1/migrate (vectors-in via canonical hub) — quote / start / status
# ──────────────────────────────────────────────────────────────────────


def _parse_source_url(url: str) -> dict:
    """Parse `pgvector://user:pass@host:5432/dbname?table=docs&id=id&embedding=embedding`
    or `chroma://host:8000?collection=name`
    or `pinecone://host?namespace=&api_key=...`
    or `weaviate://host?class=Doc`.
    """
    from urllib.parse import urlparse, parse_qs

    p = urlparse(url)
    kind = p.scheme
    qs = {k: v[0] for k, v in parse_qs(p.query).items()}

    if kind == "pgvector":
        dsn = f"postgresql://{p.username + ':' + p.password + '@' if p.username else ''}{p.hostname}{':' + str(p.port) if p.port else ''}{p.path or ''}"
        if not qs.get("table"):
            raise click.BadParameter("pgvector URL must include ?table=name", param_hint="--from")
        cfg = {"dsn": dsn, "table": qs["table"]}
        for k in ("id_col", "embedding_col", "text_col", "metadata_col", "where"):
            if k in qs:
                cfg[k] = qs[k]
        return {"kind": "pgvector", "config": cfg}

    if kind == "chroma":
        cfg = {"host": p.hostname, "port": p.port or 8000}
        if "collection" not in qs:
            raise click.BadParameter("chroma URL must include ?collection=name", param_hint="--from")
        cfg["collection_name"] = qs["collection"]
        for k in ("ssl", "tenant", "database", "api_key"):
            if k in qs:
                cfg[k] = qs[k] if k != "ssl" else qs[k].lower() == "true"
        return {"kind": "chroma", "config": cfg}

    if kind == "pinecone":
        if "api_key" not in qs:
            raise click.BadParameter("pinecone URL must include ?api_key=...", param_hint="--from")
        cfg = {"host": p.hostname, "api_key": qs["api_key"]}
        for k in ("namespace", "text_field"):
            if k in qs:
                cfg[k] = qs[k]
        return {"kind": "pinecone", "config": cfg}

    if kind == "weaviate":
        if "class" not in qs:
            raise click.BadParameter("weaviate URL must include ?class=ClassName", param_hint="--from")
        cfg = {"url": f"https://{p.hostname}{':' + str(p.port) if p.port else ''}", "class_name": qs["class"]}
        for k in ("api_key", "text_field"):
            if k in qs:
                cfg[k] = qs[k]
        return {"kind": "weaviate", "config": cfg}

    raise click.BadParameter(
        f"Unknown source scheme '{kind}' (supported: pgvector|chroma|pinecone|weaviate)",
        param_hint="--from",
    )


def _parse_target(url: str) -> str:
    """`schift://col_id` -> "col_id" """
    if not url.startswith("schift://"):
        raise click.BadParameter("--to must be schift://<collection_id>", param_hint="--to")
    return url.removeprefix("schift://").strip("/")


@migrate.command("quote")
@click.option("--from", "from_url", required=True, help="Source URL (pgvector|chroma|pinecone|weaviate scheme)")
@click.option("--export-out/--retain-cloud", default=False, help="Export-out pricing ($0.50/1M) vs Schift Cloud retention ($0.10/1M)")
def quote_cmd(from_url: str, export_out: bool) -> None:
    """Get migration quote based on source size."""
    src = _parse_source_url(from_url)
    info(f"Source: {src['kind']} (config redacted)")
    try:
        with get_client() as client:
            with spinner("Counting vectors...") as progress:
                progress.add_task("Counting vectors...", total=None)
                resp = client.post(
                    "/migrate/quote",
                    json={"source": src, "retain_on_cloud": not export_out},
                )
    except SchiftAPIError as e:
        error(f"Quote failed: {e.detail}")
        raise SystemExit(1)
    print_kv("Quote", {
        "Vectors": f"{resp['n_total_vectors']:,}",
        "Source dim": resp["src_dim"],
        "Free tier": "yes" if resp["free_tier"] else "no",
        "Rate": f"${resp['rate_per_million_cents']/100:.2f} / 1M vectors",
        "Total": f"${resp['quote_usd']:.2f}",
    })


@migrate.command("start")
@click.option("--from", "from_url", required=True, help="Source URL")
@click.option("--to", "to_url", required=True, help="schift://<collection_id>")
@click.option("--method", type=click.Choice(["ridge", "procrustes"]), default="ridge")
@click.option("--export-out/--retain-cloud", default=False)
def start_cmd(from_url: str, to_url: str, method: str, export_out: bool) -> None:
    """Start an async migration job."""
    src = _parse_source_url(from_url)
    target_collection_id = _parse_target(to_url)
    try:
        with get_client() as client:
            resp = client.post(
                "/migrate/start",
                json={
                    "source": src,
                    "target_collection_id": target_collection_id,
                    "method": method,
                    "retain_on_cloud": not export_out,
                },
            )
    except SchiftAPIError as e:
        error(f"Start failed: {e.detail}")
        raise SystemExit(1)
    print_kv("Migration job started", {
        "Job ID": resp["job_id"],
        "State": resp["state"],
        "Free tier": "yes" if resp["free_tier"] else "no",
        "Quote": f"${resp['quote_cents']/100:.2f}",
        "Requires payment": "yes" if resp["requires_payment"] else "no",
    })
    if resp["requires_payment"]:
        info("Complete payment via Polar checkout to start the job.")
    else:
        info(f"Watch progress: schift migrate status {resp['job_id']}")


@migrate.command("status")
@click.argument("job_id")
def status_cmd(job_id: str) -> None:
    """Show migration job status."""
    try:
        with get_client() as client:
            resp = client.get(f"/migrate/{job_id}")
    except SchiftAPIError as e:
        error(f"Status failed: {e.detail}")
        raise SystemExit(1)
    print_kv(f"Migration {job_id}", {
        "State": resp["state"],
        "Progress": f"{resp['progress']*100:.1f}%",
        "Vectors": f"{resp['n_projected']:,} / {resp['n_total']:,}",
        "CKA": f"{resp['cka']:.4f}" if resp.get("cka") is not None else "-",
        "Sample retention": f"{resp['sample_retention']*100:.1f}%" if resp.get("sample_retention") is not None else "-",
        "Error": resp.get("error") or "-",
    })
