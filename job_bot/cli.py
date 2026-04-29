"""CLI: job-bot run <pipeline.yaml> [--job-url URL] [--profile profiles/me.yaml]"""
from __future__ import annotations

import sys
from pathlib import Path

import click
import yaml

from .context import ApplicationContext
from .pipeline import Pipeline, SKILL_REGISTRY


@click.group()
def main():
    """Job Bot — modular job application pipeline."""


@main.command()
@click.argument("pipeline_file", default="pipelines/default.yaml", required=False)
@click.option("--job-url", "-u", default="", help="Override job posting URL")
@click.option("--company", "-c", default="", help="Override company name")
@click.option("--title", "-t", default="", help="Override job title")
@click.option("--profile", "-p", default="", help="Override profile YAML path")
@click.option("--headless", is_flag=True, default=False, help="Skip interactive review")
def run(
    pipeline_file: str,
    job_url: str,
    company: str,
    title: str,
    profile: str,
    headless: bool,
) -> None:
    """Run the pipeline defined in PIPELINE_FILE."""
    path = Path(pipeline_file)
    if not path.exists():
        click.echo(f"Pipeline file not found: {path}", err=True)
        sys.exit(1)

    with path.open() as f:
        config = yaml.safe_load(f)

    # CLI flags override pipeline config
    if profile:
        for step in config.get("steps", []):
            if isinstance(step, dict) and step.get("skill") == "profile_loader":
                step["profile_path"] = profile
    if headless:
        for step in config.get("steps", []):
            if isinstance(step, dict) and step.get("skill") == "human_review":
                step["headless"] = True

    pipeline = Pipeline.from_config(config)

    ctx = ApplicationContext(
        job_url=job_url,
        company_name=company,
        job_title=title,
    )

    pipeline.run(ctx)


@main.command()
def skills() -> None:
    """List all available skill modules."""
    click.echo("Available skills:")
    for name in SKILL_REGISTRY:
        click.echo(f"  {name}")


@main.command()
@click.argument("pipeline_file", default="pipelines/default.yaml", required=False)
def describe(pipeline_file: str) -> None:
    """Show the steps in a pipeline file without running it."""
    path = Path(pipeline_file)
    if not path.exists():
        click.echo(f"Pipeline file not found: {path}", err=True)
        sys.exit(1)
    with path.open() as f:
        config = yaml.safe_load(f)
    pipeline = Pipeline.from_config(config)
    click.echo(pipeline.describe())


if __name__ == "__main__":
    main()
