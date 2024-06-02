"""Command line interface for linkml-generate."""


import click
import logging
import sys

inputfile_option = click.option("-i", "--inputfile", help="Path to a LinkML schema in YAML.")
model_option = click.option(
    "-m",
    "--model",
    help="Model name to use, e.g. orca-mini-7b or gpt-4."
    " See all model names with ontogpt list-models.",
)
output_option_wb = click.option(
    "-o", "--output", type=click.File(mode="wb"), default=sys.stdout, help="Output data file."
)
output_format_options = click.option(
    "-O",
    "--output-format",
    type=click.Choice(["json", "yaml", "pickle", "md", "html", "owl", "turtle", "jsonl", "kgx"]),
    default="yaml",
    help="Output format.",
)

@click.group()
@click.option("-v", "--verbose", count=True)
@click.option("-q", "--quiet")
def main(verbose: int, quiet: bool):
    """CLI for linkml-generate.

    :param verbose: Verbosity while running.
    :param quiet: Boolean to be quiet or verbose.
    """
    logger = logging.getLogger()
    if verbose >= 2:
        logger.setLevel(level=logging.DEBUG)
    elif verbose == 1:
        logger.setLevel(level=logging.INFO)
    else:
        logger.setLevel(level=logging.WARNING)
    if quiet:
        logger.setLevel(level=logging.ERROR)
    logger.info(f"Logger {logger.name} set to level {logger.level}")


@main.command()
@inputfile_option
@model_option
@output_option_wb
@output_format_options
@click.argument("input", required=False)
def generate(
    inputfile,
    model,
    output,
    output_format,
    **kwargs,
):
    """Generate data from a LinkML schema.
    """
    print("Empty for now.")
    pass