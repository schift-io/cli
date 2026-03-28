from __future__ import annotations

import click

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
    """Hide password in connection strings for display."""
    if "@" in conn:
        # pgvector://user:pass@host -> pgvector://user:***@host
        before_at = conn.split("@")[0]
        after_at = conn.split("@", 1)[1]
        if ":" in before_at:
            scheme_user = before_at.rsplit(":", 1)[0]
            return f"{scheme_user}:***@{after_at}"
    return conn
