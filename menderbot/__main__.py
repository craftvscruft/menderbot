import rich_click as click
from rich.progress import Progress
from rich.console import Console
from rich.prompt import Prompt

from menderbot.llm import get_response, INSTRUCTIONS

console = Console()


@click.group(context_settings=dict(help_option_names=["-h", "--help"]))
@click.option(
    "--debug",
    default=False,
    help="Show the debug log messages.",
)
@click.option(
    "--dry",
    default=False,
    help="Dry run, do not call API, only output prompts.",
)
@click.version_option("1.23", prog_name="mytool")
def cli(debug, dry):
    """
    An AI-powered command line tool for working with legacy code.

    You can try using --help at the top level and also for
    specific subcommands.

    Please provide OPENAI_API_KEY as an environment variable.
    """
    # print(f"Debug mode is {'on' if debug else 'off'}")
    pass


@cli.command()
@click.argument("q", nargs=-1)
def ask(q):
    """Ask a question about a specific piece of code or concept."""
    new_question = " ".join(q)
    if not new_question:
        new_question = Prompt.ask("[green]Ask")
    with Progress(transient=True) as progress:
        task = progress.add_task("[green]Processing...", total=None)
        response = get_response(INSTRUCTIONS, [], new_question)
        progress.update(task, completed=True)
    console.print(f"[cyan]Bot[/cyan]: {response}")


@cli.command()
def chat():
    """Interactively chat in the context of the current directory."""
    previous_questions_and_answers = []
    while True:
        new_question = Prompt.ask("[green]Ask")
        if new_question:
            # Moderation?
            with Progress(transient=True) as progress:
                task = progress.add_task("[green]Processing...", total=None)
                response = get_response(
                    INSTRUCTIONS, previous_questions_and_answers, new_question
                )
                progress.update(task, completed=True)
            # add the new question and answer to the list of previous questions and answers
            previous_questions_and_answers.append((new_question, response))
            console.print(f"[cyan]Bot[/cyan]: {response}")


@cli.command()
def doc():
    """Generate documentation for the existing code."""
    print("TODO")


@cli.command()
def review():
    """Review a code block or changeset and provide feedback"""
    print("TODO")


@cli.command()
def commit():
    """Generate an informative commit message based on a changeset."""
    print("TODO")


@cli.command()
def diff():
    """Summarize the differences between two versions of a codebase."""
    print("TODO")


if __name__ == "__main__":
    cli()
