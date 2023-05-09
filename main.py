import openai
import rich_click as click
from rich.progress import Progress
from rich.console import Console
import os
from rich.prompt import Prompt
openai.api_key = os.getenv("OPENAI_API_KEY")

console = Console()

INSTRUCTIONS = """You are helpful electronic assistant with knowledge of Software Engineering."""

TEMPERATURE = 0.5
MAX_TOKENS = 500
FREQUENCY_PENALTY = 0
PRESENCE_PENALTY = 0.6
# limits how many questions we include in the prompt
MAX_CONTEXT_QUESTIONS = 10

def get_response(instructions, previous_questions_and_answers, new_question):
    """Get a response from ChatCompletion

    Args:
        instructions: The instructions for the chat bot - this determines how it will behave
        previous_questions_and_answers: Chat history
        new_question: The new question to ask the bot

    Returns:
        The response text
    """
    # build the messages
    messages = [
        { "role": "system", "content": instructions },
    ]
    # add the previous questions and answers
    for question, answer in previous_questions_and_answers[-MAX_CONTEXT_QUESTIONS:]:
        messages.append({ "role": "user", "content": question })
        messages.append({ "role": "assistant", "content": answer })
    # add the new question
    messages.append({ "role": "user", "content": new_question })

    completion = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=messages,
        temperature=TEMPERATURE,
        max_tokens=MAX_TOKENS,
        top_p=1,
        frequency_penalty=FREQUENCY_PENALTY,
        presence_penalty=PRESENCE_PENALTY,
    )
    return completion.choices[0].message.content



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
@click.argument('q', nargs=-1)
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
                response = get_response(INSTRUCTIONS, previous_questions_and_answers, new_question)
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