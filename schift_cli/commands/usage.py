from __future__ import annotations

import click

from schift_cli.client import get_client, SchiftAPIError
from schift_cli.display import error, print_kv, print_table


@click.command("usage")
@click.option("--period", "-p", default="30d", show_default=True,
              help="Time period (e.g. 7d, 30d, 90d)")
def usage(period: str) -> None:
    """Show API usage and billing summary."""
    try:
        with get_client() as client:
            data = client.get("/usage", params={"period": period})
    except SchiftAPIError as e:
        error(f"Failed to fetch usage: {e.detail}")
        raise SystemExit(1)
    except click.ClickException:
        raise

    summary = data.get("summary", data)

    print_kv(f"Usage Summary (last {period})", {
        "Total Requests": summary.get("total_requests", "-"),
        "Embeddings Generated": summary.get("embeddings_generated", "-"),
        "Projections Computed": summary.get("projections_computed", "-"),
        "Queries Executed": summary.get("queries_executed", "-"),
        "Storage Used": summary.get("storage_used", "-"),
        "Cost": summary.get("cost", "-"),
    })

    # Show per-model breakdown if available
    breakdown = data.get("by_model", [])
    if breakdown:
        rows = [
            (
                b.get("model", ""),
                str(b.get("requests", "")),
                str(b.get("tokens", "")),
                b.get("cost", ""),
            )
            for b in breakdown
        ]
        print_table(
            "Usage by Model",
            ["Model", "Requests", "Tokens", "Cost"],
            rows,
        )
