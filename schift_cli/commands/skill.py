"""schift skill install — install Claude Code skills for Schift best practices."""

from __future__ import annotations

import shutil
from importlib import resources
from pathlib import Path

import click


SKILL_NAME = "schift-best-practices"
CLAUDE_SKILLS_DIR = Path.home() / ".claude" / "skills"


@click.group()
def skill() -> None:
    """Manage Claude Code skills for Schift."""


@skill.command()
@click.option(
    "--dest",
    type=click.Path(),
    default=None,
    help="Override destination directory (default: ~/.claude/skills/)",
)
def install(dest: str | None) -> None:
    """Install schift-best-practices skill for Claude Code."""

    target = Path(dest) if dest else CLAUDE_SKILLS_DIR / SKILL_NAME

    # Locate bundled skill files
    source = _find_skill_source()
    if source is None:
        click.secho(
            "Error: bundled skill files not found. "
            "Try reinstalling schift-cli.",
            fg="red",
        )
        raise SystemExit(1)

    if target.exists():
        click.confirm(
            f"{target} already exists. Overwrite?",
            abort=True,
        )
        shutil.rmtree(target)

    shutil.copytree(source, target)

    # Create CLAUDE.md symlink if missing
    claude_md = target / "CLAUDE.md"
    agents_md = target / "AGENTS.md"
    if agents_md.exists() and not claude_md.exists():
        claude_md.symlink_to("AGENTS.md")

    click.secho(f"Installed {SKILL_NAME} to {target}", fg="green")
    click.echo(
        "Claude Code will now reference Schift best practices "
        "when you work on embedding, search, or RAG code."
    )


@skill.command()
def uninstall() -> None:
    """Remove schift-best-practices skill from Claude Code."""

    target = CLAUDE_SKILLS_DIR / SKILL_NAME
    if not target.exists():
        click.echo(f"{SKILL_NAME} is not installed.")
        return

    click.confirm(f"Remove {target}?", abort=True)
    shutil.rmtree(target)
    click.secho(f"Removed {SKILL_NAME}", fg="yellow")


@skill.command(name="list")
def list_skills() -> None:
    """List installed Schift skills."""

    target = CLAUDE_SKILLS_DIR / SKILL_NAME
    if target.exists():
        refs = list((target / "references").glob("*.md")) if (target / "references").exists() else []
        click.echo(f"{SKILL_NAME}  ({len(refs)} references)  {target}")
    else:
        click.echo("No Schift skills installed. Run: schift skill install")


def _find_skill_source() -> Path | None:
    """Locate the bundled skill directory shipped with the package."""

    # 1. Check package data (installed via pip)
    try:
        pkg = resources.files("schift_cli") / "data" / SKILL_NAME
        # resources.files returns a Traversable; resolve to Path
        pkg_path = Path(str(pkg))
        if pkg_path.is_dir() and (pkg_path / "SKILL.md").exists():
            return pkg_path
    except (TypeError, FileNotFoundError):
        pass

    # 2. Fallback: check relative to repo root (dev mode / editable install)
    repo_root = Path(__file__).resolve().parents[4]  # sdk/cli/schift_cli/commands → repo root
    dev_path = repo_root / "skills" / SKILL_NAME
    if dev_path.is_dir() and (dev_path / "SKILL.md").exists():
        return dev_path

    return None
