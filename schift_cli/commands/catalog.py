from __future__ import annotations

import click

from schift_cli.client import get_client, SchiftAPIError
from schift_cli.display import print_table, print_kv, error


@click.group("catalog")
def catalog() -> None:
    """Browse available embedding models."""


@catalog.command("list")
def list_models() -> None:
    """List all supported embedding models."""
    try:
        with get_client() as client:
            data = client.get("/catalog/models")
    except SchiftAPIError as e:
        error(f"Failed to fetch model catalog: {e.detail}")
        raise SystemExit(1)
    except click.ClickException:
        raise

    models = data.get("models", [])
    if not models:
        click.echo("No models found in the catalog.")
        return

    rows = [
        (
            m.get("id", ""),
            m.get("provider", ""),
            str(m.get("dimensions", "")),
            m.get("max_tokens", ""),
            m.get("status", ""),
        )
        for m in models
    ]
    print_table(
        "Embedding Model Catalog",
        ["Model ID", "Provider", "Dimensions", "Max Tokens", "Status"],
        rows,
    )


@catalog.command("get")
@click.argument("model_id")
def get_model(model_id: str) -> None:
    """Show details for a specific model.

    MODEL_ID is the fully qualified model name, e.g. openai/text-embedding-3-large
    """
    try:
        with get_client() as client:
            data = client.get(f"/catalog/models/{model_id}")
    except SchiftAPIError as e:
        if e.status_code == 404:
            error(f"Model not found: {model_id}")
        else:
            error(f"Failed to fetch model: {e.detail}")
        raise SystemExit(1)
    except click.ClickException:
        raise

    model = data.get("model", data)
    print_kv(f"Model: {model_id}", {
        "Provider": model.get("provider", "-"),
        "Dimensions": model.get("dimensions", "-"),
        "Max Tokens": model.get("max_tokens", "-"),
        "Status": model.get("status", "-"),
        "Description": model.get("description", "-"),
    })
