from __future__ import annotations

import json
from pathlib import Path

import click

from schift_cli.client import get_client, SchiftAPIError
from schift_cli.display import console, error, info, success


@click.group("embed", invoke_without_command=True)
@click.argument("text", required=False, default=None)
@click.option("--model", "-m", default=None,
              help="Embedding model ID (e.g. openai/text-embedding-3-large)")
@click.pass_context
def embed(ctx: click.Context, text: str | None, model: str | None) -> None:
    """Generate embeddings for text.

    \b
    Usage:
        schift embed "hello world" --model openai/text-embedding-3-large
        schift embed batch --file texts.jsonl --model google/gemini-embedding-004
    """
    if ctx.invoked_subcommand is not None:
        return

    if not text:
        raise click.UsageError("Provide TEXT to embed, or use `schift embed batch`.")
    if not model:
        raise click.UsageError("--model is required.")

    try:
        with get_client() as client:
            data = client.post("/embed", json={"text": text, "model": model})
    except SchiftAPIError as e:
        error(f"Embedding failed: {e.detail}")
        raise SystemExit(1)
    except click.ClickException:
        raise

    embedding = data.get("embedding", [])
    dims = len(embedding)
    preview = embedding[:5]
    preview_str = ", ".join(f"{v:.6f}" for v in preview)

    success(f"Generated {dims}-dimensional embedding")
    console.print(f"  [{preview_str}, ...]")


@embed.command("batch")
@click.option("--file", "-f", "file_path", required=True,
              type=click.Path(exists=True, path_type=Path),
              help="JSONL file with one text per line (field: \"text\")")
@click.option("--model", "-m", required=True,
              help="Embedding model ID (e.g. google/gemini-embedding-004)")
@click.option("--output", "-o", type=click.Path(path_type=Path), default=None,
              help="Output JSONL file for results (default: stdout summary)")
def embed_batch(file_path: Path, model: str, output: Path | None) -> None:
    """Embed multiple texts from a JSONL file.

    Each line in the input file must be a JSON object with a "text" field.
    """
    texts: list[str] = []
    with open(file_path) as f:
        for i, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
                texts.append(obj["text"])
            except (json.JSONDecodeError, KeyError):
                error(f"Line {i}: expected JSON with a \"text\" field")
                raise SystemExit(1)

    if not texts:
        error("No texts found in input file.")
        raise SystemExit(1)

    info(f"Embedding {len(texts)} texts with model {model}")

    try:
        with get_client() as client:
            data = client.post(
                "/embed/batch",
                json={"texts": texts, "model": model},
            )
    except SchiftAPIError as e:
        error(f"Batch embedding failed: {e.detail}")
        raise SystemExit(1)
    except click.ClickException:
        raise

    embeddings = data.get("embeddings", [])

    if output:
        with open(output, "w") as f:
            for text_val, emb in zip(texts, embeddings):
                f.write(json.dumps({"text": text_val, "embedding": emb}) + "\n")
        success(f"Wrote {len(embeddings)} embeddings to {output}")
    else:
        dims = len(embeddings[0]) if embeddings else 0
        success(f"Generated {len(embeddings)} embeddings ({dims} dimensions each)")
