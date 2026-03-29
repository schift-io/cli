from __future__ import annotations

import json

import click

from schift_cli.client import SchiftAPIError, extract_items, get_client, resolve_bucket
from schift_cli.display import error, print_kv, print_table, success


@click.group("jobs")
def jobs() -> None:
    """Inspect, reprocess, and cancel ingest jobs."""


@jobs.command("list")
@click.option("--bucket", "-b", default=None, help="Bucket name or bucket ID")
@click.option("--status", default=None, help="Filter jobs by status")
@click.option("--limit", type=int, default=20, show_default=True, help="Maximum jobs to return")
def list_jobs(bucket: str | None, status: str | None, limit: int) -> None:
    """List recent ingest jobs."""
    try:
        with get_client() as client:
            bucket_id = resolve_bucket(client, bucket).get("id") if bucket else None
            data = client.get(
                "/jobs",
                params={k: v for k, v in {
                    "bucket_id": bucket_id,
                    "status": status,
                    "limit": limit,
                }.items() if v is not None},
            )
    except SchiftAPIError as exc:
        error(f"Failed to list jobs: {exc.detail}")
        raise SystemExit(1)
    except click.ClickException:
        raise

    jobs_list = extract_items(data, "jobs")
    rows = [
        (
            item.get("id", "-"),
            item.get("bucket_id", "-"),
            item.get("file_name", item.get("document_name", "-")),
            item.get("status", "-"),
        )
        for item in jobs_list
    ]
    print_table("Ingest Jobs", ["Job", "Bucket", "File", "Status"], rows)


@jobs.command("get")
@click.argument("job_id")
def get_job(job_id: str) -> None:
    """Inspect one job."""
    try:
        with get_client() as client:
            data = client.get(f"/jobs/{job_id}")
    except SchiftAPIError as exc:
        error(f"Failed to inspect job: {exc.detail}")
        raise SystemExit(1)
    except click.ClickException:
        raise

    if not isinstance(data, dict):
        raise click.ClickException("Unexpected job response from Schift API.")

    print_kv(
        f"Job: {job_id}",
        {key: json.dumps(value, ensure_ascii=True) if isinstance(value, (dict, list)) else value for key, value in data.items()},
    )


@jobs.command("reprocess")
@click.argument("job_id")
def reprocess_job(job_id: str) -> None:
    """Requeue a failed or stale job."""
    try:
        with get_client() as client:
            client.post(f"/jobs/{job_id}/reprocess")
    except SchiftAPIError as exc:
        error(f"Failed to reprocess job: {exc.detail}")
        raise SystemExit(1)
    except click.ClickException:
        raise

    success(f"Requested reprocess for job '{job_id}'.")


@jobs.command("cancel")
@click.argument("job_id")
def cancel_job(job_id: str) -> None:
    """Cancel an in-flight job."""
    try:
        with get_client() as client:
            client.post(f"/jobs/{job_id}/cancel")
    except SchiftAPIError as exc:
        error(f"Failed to cancel job: {exc.detail}")
        raise SystemExit(1)
    except click.ClickException:
        raise

    success(f"Requested cancel for job '{job_id}'.")
