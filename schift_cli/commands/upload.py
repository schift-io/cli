from __future__ import annotations

import json
import mimetypes
from pathlib import Path

import click

from schift_cli.client import SchiftAPIError, get_client, resolve_bucket
from schift_cli.display import error, print_table, success


@click.command("upload")
@click.argument("paths", nargs=-1, type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.option("--bucket", "-b", required=True, help="Bucket name or bucket ID")
@click.option("--ocr-strategy", default=None, help="Optional OCR strategy override")
@click.option("--chunk-size", type=int, default=None, help="Optional chunk size override")
@click.option("--chunk-overlap", type=int, default=None, help="Optional chunk overlap override")
def upload(
    paths: tuple[Path, ...],
    bucket: str,
    ocr_strategy: str | None,
    chunk_size: int | None,
    chunk_overlap: int | None,
) -> None:
    """Upload one or more files into a bucket."""
    if not paths:
        raise click.ClickException("Pass at least one file path to upload.")

    payload: dict[str, str] = {}
    meta: dict[str, int | str] = {}
    if ocr_strategy is not None:
        meta["ocr_strategy"] = ocr_strategy
    if chunk_size is not None:
        meta["chunk_size"] = chunk_size
    if chunk_overlap is not None:
        meta["chunk_overlap"] = chunk_overlap
    if meta:
        payload["payload"] = json.dumps(meta)

    files = []
    for path in paths:
        mime = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        files.append(("files", (path.name, path.read_bytes(), mime)))

    try:
        with get_client() as client:
            resolved_bucket = resolve_bucket(client, bucket, create=True)
            bucket_id = resolved_bucket.get("id")
            if not bucket_id:
                raise click.ClickException("Bucket response did not include an id.")
            data = client.post_multipart(
                f"/buckets/{bucket_id}/upload",
                data=payload or None,
                files=files,
            )
    except SchiftAPIError as exc:
        error(f"Upload failed: {exc.detail}")
        raise SystemExit(1)
    except click.ClickException:
        raise

    uploaded = []
    if isinstance(data, dict) and isinstance(data.get("uploaded"), list):
        uploaded = data["uploaded"]
    elif isinstance(data, list):
        uploaded = data
    elif isinstance(data, dict):
        uploaded = [data]

    rows = [
        (
            item.get("file_name", item.get("filename", "-")),
            item.get("job_id", item.get("id", "-")),
            item.get("status", item.get("state", "queued")),
        )
        for item in uploaded
        if isinstance(item, dict)
    ]

    if rows:
        print_table(
            f"Bucket Upload ({resolved_bucket.get('name', bucket)})",
            ["File", "Job", "Status"],
            rows,
        )

    success(f"Uploaded {len(paths)} file(s) to bucket '{resolved_bucket.get('name', bucket)}'.")
