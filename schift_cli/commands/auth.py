from __future__ import annotations

import click

from schift_cli.config import clear_api_key, get_api_key, set_api_key, CONFIG_FILE
from schift_cli.display import success, info, error


@click.group("auth")
def auth() -> None:
    """Manage authentication with the Schift platform."""


@auth.command()
def login() -> None:
    """Set your Schift API key."""
    existing = get_api_key()
    if existing:
        overwrite = click.confirm(
            "An API key is already configured. Overwrite?", default=False
        )
        if not overwrite:
            info("Keeping existing API key.")
            return

    api_key = click.prompt("Enter your Schift API key", hide_input=True)
    api_key = api_key.strip()

    if not api_key:
        raise click.ClickException("API key cannot be empty.")

    set_api_key(api_key)
    success(f"API key saved to {CONFIG_FILE}")


@auth.command()
def logout() -> None:
    """Remove the stored API key."""
    if not get_api_key():
        info("No API key is currently stored.")
        return

    clear_api_key()
    success("API key removed.")


@auth.command()
def status() -> None:
    """Show current authentication status."""
    import os
    from schift_cli.config import ENV_API_KEY

    env_key = os.environ.get(ENV_API_KEY)
    file_key = None
    try:
        from schift_cli.config import load_config
        file_key = load_config().get("api_key")
    except Exception:
        pass

    if env_key:
        masked = env_key[:8] + "..." + env_key[-4:] if len(env_key) > 12 else "***"
        success(f"Authenticated via {ENV_API_KEY} env var (key: {masked})")
    elif file_key:
        masked = file_key[:8] + "..." + file_key[-4:] if len(file_key) > 12 else "***"
        success(f"Authenticated via config file (key: {masked})")
    else:
        error("Not authenticated. Run `schift auth login` to get started.")
