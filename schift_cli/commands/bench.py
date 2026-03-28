from __future__ import annotations

from pathlib import Path

import click

from schift_cli.client import get_client, SchiftAPIError
from schift_cli.display import console, error, info, print_kv, spinner, success


@click.command("bench")
@click.option("--source", "-s", required=True, help="Source model ID (e.g. openai/text-embedding-3-large)")
@click.option("--target", "-t", required=True, help="Target model ID (e.g. google/gemini-embedding-004)")
@click.option("--data", "-d", type=click.Path(exists=True, path_type=Path), required=True,
              help="JSONL file with benchmark queries")
@click.option("--top-k", "-k", type=int, default=10, show_default=True,
              help="Number of results to compare per query")
def bench(source: str, target: str, data: Path, top_k: int) -> None:
    """Benchmark embedding quality between two models.

    Measures how well a Schift projection preserves retrieval quality
    when switching from SOURCE to TARGET model.
    """
    info(f"Benchmarking projection: {source} -> {target}")
    info(f"Data: {data}  |  top-k: {top_k}")

    try:
        with get_client() as client:
            with spinner("Running benchmark...") as progress:
                progress.add_task("Running benchmark...", total=None)
                result = client.post(
                    "/bench",
                    json={
                        "source_model": source,
                        "target_model": target,
                        "data_path": str(data),
                        "top_k": top_k,
                    },
                )
    except SchiftAPIError as e:
        error(f"Benchmark failed: {e.detail}")
        raise SystemExit(1)
    except click.ClickException:
        raise

    report = result.get("report", result)
    print_kv("Benchmark Report", {
        "Source Model": source,
        "Target Model": target,
        "Queries": report.get("num_queries", "-"),
        "Recall@k": report.get("recall_at_k", "-"),
        "MRR": report.get("mrr", "-"),
        "Cosine Similarity (avg)": report.get("avg_cosine_similarity", "-"),
        "Latency (p50)": report.get("latency_p50_ms", "-"),
        "Latency (p99)": report.get("latency_p99_ms", "-"),
    })

    quality = report.get("recall_at_k")
    if quality is not None:
        if float(quality) >= 0.95:
            success("Projection quality is excellent.")
        elif float(quality) >= 0.85:
            console.print("[yellow]Projection quality is acceptable but may degrade edge cases.[/]")
        else:
            console.print("[red]Projection quality is low. Consider increasing sample size in `migrate fit`.[/]")
