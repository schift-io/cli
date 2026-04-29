from __future__ import annotations

import click

from schift_cli import __version__
from schift_cli.commands.auth import auth
from schift_cli.commands.bench import bench
from schift_cli.commands.catalog import catalog
from schift_cli.commands.db import db
from schift_cli.commands.embed import embed
from schift_cli.commands.jobs import jobs
from schift_cli.commands.migrate import migrate
from schift_cli.commands.query import query
from schift_cli.commands.search import search
from schift_cli.commands.skill import skill
from schift_cli.commands.upload import upload
from schift_cli.commands.usage import usage


@click.group()
@click.version_option(version=__version__, prog_name="schift")
def cli() -> None:
    """Schift CLI -- AI Agent Framework.

    Manage agents, embedding models, buckets, and migrations
    from the command line.
    """


cli.add_command(auth)
cli.add_command(catalog)
cli.add_command(embed)
cli.add_command(bench)
cli.add_command(migrate)
cli.add_command(db)
cli.add_command(query)
cli.add_command(search)
cli.add_command(upload)
cli.add_command(jobs)
cli.add_command(skill)
cli.add_command(usage)


if __name__ == "__main__":
    cli()
