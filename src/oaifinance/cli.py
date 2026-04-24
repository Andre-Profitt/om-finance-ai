"""oai-finance CLI."""

from __future__ import annotations

import click

from oaifinance import pipeline


@click.group()
def cli() -> None:
    """O&M Finance Revenue Integrity Control Tower."""


@cli.command()
@click.option("--n-claims", type=int, default=5000, help="Synthetic claim volume.")
@click.option("--live", is_flag=True, help="Attempt live CMS fetch (not implemented in v0).")
def build(n_claims: int, live: bool) -> None:
    """Run the end-to-end pipeline: ingest → silver → gold → score → eval."""
    pipeline.run(n_claims=n_claims, live=live)


@cli.command("practice-analysis")
@click.option(
    "--practice", default=None, help="Target practice ID; defaults to highest-expected-recovery."
)
def practice_analysis(practice: str | None) -> None:
    """Build the per-practice performance summary + acquisition model."""
    from oaifinance.practice import performance

    model = performance.analyze(target_practice=practice)
    performance.print_summary(model)


@cli.command()
def version() -> None:
    from oaifinance import __version__

    click.echo(__version__)


if __name__ == "__main__":
    cli()
