"""Command line interface for linkml-generate."""


import click
import logging
import sys

from pathlib import Path

from ontogpt.cli import write_extraction
from ontogpt.io.template_loader import get_template_details

from linkml_generate.engines.datamaker_engine import DataMakerEngine

DEFAULT_MODEL = "gpt-4o"
DEFAULT_MODEL_SOURCE = "openai"

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
@model_option
@output_option_wb
@output_format_options
@click.argument("inputschema", required=True)
def generate(
    model,
    output,
    output_format,
    inputschema,
    **kwargs,
):
    """Generate data from a LinkML schema.
    """
    # Choose model based on input, or use the default
    if not model:
        model = DEFAULT_MODEL
    
    if inputschema and not Path(inputschema).exists():
        raise FileNotFoundError(f"Cannot find input schema {inputschema}")

    template_details = get_template_details(template=input)

    ke = DataMakerEngine(
        template_details=template_details,
        model=model,
        model_source=DEFAULT_MODEL_SOURCE,
        use_azure=False,
        **kwargs,
    )
    target_class_def = None

    results = ke.make_data(cls=target_class_def)

    write_extraction(results, output, output_format, ke, inputschema)
