import os

import rich_click as click
from rich.console import Console
from rich.progress import Progress
from rich.prompt import Confirm

from menderbot import VERSION
from menderbot.check import run_check
from menderbot.git_client import git_commit, git_diff_head
from menderbot.ingest import ask_index, get_chat_engine, index_exists, ingest_repo
from menderbot.llm import INSTRUCTIONS, get_response, unwrap_codeblock
from menderbot.prompts import (
    change_list_prompt,
    code_review_prompt,
    commit_msg_prompt,
    type_prompt,
)
from menderbot.source_file import SourceFile

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
@click.version_option(VERSION, prog_name="menderbot")
@click.pass_context
def cli(ctx, debug, dry):
    """
    An AI-powered command line tool for working with legacy code.

    You can try using --help at the top level and also for
    specific subcommands.

    Connects to OpenAI using OPENAI_API_KEY environment variable.
    """
    del debug
    # print(f"Debug mode is {'on' if debug else 'off'}")
    if "OPENAI_API_KEY" not in os.environ:
        console.log("OPENAI_API_KEY not found in env, will not be able to connect.")
    ctx.ensure_object(dict)
    ctx.obj["DRY"] = dry


@cli.command()
@click.argument("q", required=False)
def ask(q):
    """Ask a question about a specific piece of code or concept."""
    if not index_exists():
        console.print("[red]Index not found[/red]: please run menderbot ingest")
        return
    new_question = q
    if not new_question:
        new_question = console.input("[green]Ask[/green]: ")
    with Progress(transient=True) as progress:
        task = progress.add_task("[green]Processing...", total=None)
        response = ask_index(new_question)
        progress.update(task, completed=True)
    console.print(f"[cyan]Bot[/cyan]: {response}")


@cli.command()
def chat():
    """Interactively chat in the context of the current directory."""
    if not index_exists():
        console.print("[red]Index not found[/red]: please run menderbot ingest")
    else:
        console.print("Loading index...")
    chat_engine = get_chat_engine()
    while True:
        new_question = console.input("[green]Ask[/green]: ")
        # new_question += "\nUse your tool to query for context."
        if new_question:
            streaming_response = chat_engine.stream_chat(new_question)
            console.print("[cyan]Bot[/cyan]: ", end="")
            for token in streaming_response.response_gen:
                console.out(token, end="")
            console.out("\n")


def try_function_type_hints(source_file, function_node, function_text, needs_typing):
    from menderbot.typing import add_type_hints, parse_type_hint_answer  # Lazy import

    mypy_args = "--no-error-summary --soft-error-limit 10"
    check_command = (
        f"mypy {mypy_args} --shadow-file {source_file.path} {source_file.path}.shadow"
    )
    max_tries = 2
    check_output = None
    # First set them all to wrong type, to produce an error message.
    hints = [(ident, "None") for ident in needs_typing]
    insertions_for_function = add_type_hints(function_node, hints)
    if insertions_for_function:
        source_file.update_file(insertions_for_function, suffix=".shadow")
        (success, pre_check_output) = run_check(check_command)
        if not success:
            check_output = pre_check_output
    for try_num in range(0, max_tries):
        if try_num > 0:
            console.print("Retrying")
        prompt = type_prompt(function_text, needs_typing, previous_error=check_output)
        answer = get_response_with_progress(INSTRUCTIONS, [], prompt)
        hints = parse_type_hint_answer(answer)

        insertions_for_function = add_type_hints(function_node, hints)
        if insertions_for_function:
            console.print(f"[cyan]Bot[/cyan]: {hints}")
            source_file.update_file(insertions_for_function, suffix=".shadow")
            (success, check_output) = run_check(check_command)
            if success:
                console.print("[green]Type checker passed[/green], keeping")
                return insertions_for_function
            else:
                console.print("[red]Type checker failed[/red], discarding")
        else:
            console.print("[cyan]Bot[/cyan]: No changes")
            # No retry if it didn't try to hint anything.
            return []
    return []


@cli.command("type")
@click.argument("file")
def type_command(file):
    """Insert type hints (Python only)"""
    from menderbot.typing import process_untyped_functions  # Lazy import

    console.print("Running type-checker baseline")
    (success, check_output) = run_check("mypy")
    if not success:
        console.print(check_output)
        console.print("Baseline failed, aborting.")
        return
    source_file = SourceFile(file)
    insertions = []
    for function_node, function_text, needs_typing in process_untyped_functions(
        source_file
    ):
        insertions += try_function_type_hints(
            source_file, function_node, function_text, needs_typing
        )
    if not insertions:
        console.print(f"No changes for '{file}.")
        return
    if not Confirm.ask(f"Write '{file}'?"):
        console.print("Skipping.")
        return
    source_file.update_file(insertions, suffix="")
    console.print("Done.")


def get_response_with_progress(instructions, history, question):
    with Progress(transient=True) as progress:
        task = progress.add_task("[green]Processing...", total=None)
        answer = get_response(instructions, history, question)
        progress.update(task, completed=True)
        return answer


def generate_doc(code, file_extension):
    if not file_extension == ".py":
        # Until more types are supported.
        return None
    question = f"""
Write a short Python docstring for this code.
Do not include Arg lists.
Respond with docstring only, no code.
CODE:
{code}
"""
    from menderbot.code import function_indent, reindent  # Lazy import

    with Progress(transient=True) as progress:
        task = progress.add_task("[green]Processing...", total=None)
        doc_text = get_response(INSTRUCTIONS, [], question)
        progress.update(task, completed=True)
        if '"""' in doc_text:
            doc_text = doc_text[0 : doc_text.rfind('"""') + 3]
            doc_text = doc_text[doc_text.find('"""') :]
            indent = function_indent(code)
            doc_text = reindent(doc_text, indent)
        return doc_text


@cli.command()
@click.argument("file")
def doc(file):
    """Generate function-level documentation for the existing code (Python only)."""
    from menderbot.doc import document_file  # Lazy import

    source_file = SourceFile(file)
    insertions = document_file(source_file, generate_doc)
    if not insertions:
        console.print(f"No updates found for '{file}'.")
        return
    if not Confirm.ask(f"Write '{file}'?"):
        console.print("Skipping.")
        return
    source_file.update_file(insertions, suffix="")
    console.print("Done.")


@cli.command()
def review():
    """Review a code block or changeset and provide feedback."""
    console.print("Reading diff from STDIN...")
    diff_text = click.get_text_stream("stdin").read()
    new_question = code_review_prompt(diff_text)
    with Progress(transient=True) as progress:
        task = progress.add_task("[green]Processing...", total=None)
        response_1 = get_response(INSTRUCTIONS, [], new_question)
        progress.update(task, completed=True)
    console.print(f"[cyan]Bot[/cyan]:\n{response_1}")


@cli.command()
def commit():
    """Generate an informative commit message based on a changeset."""
    diff_text = git_diff_head(staged=True)
    new_question = change_list_prompt(diff_text)
    with Progress(transient=True) as progress:
        task = progress.add_task("[green]Processing...", total=None)
        response_1 = get_response(INSTRUCTIONS, [], new_question)
        progress.update(task, completed=True)
    console.print(f"[cyan]Bot (initial pass)[/cyan]:\n{response_1}")

    question_2 = commit_msg_prompt(response_1)
    with Progress(transient=True) as progress:
        task = progress.add_task("[green]Processing...", total=None)
        response_2 = unwrap_codeblock(get_response(INSTRUCTIONS, [], question_2))
        progress.update(task, completed=True)
    console.print(f"[cyan]Bot[/cyan]:\n{response_2}")
    git_commit(response_2)


@cli.command()
def diff():
    """Summarize the differences between two versions of a codebase."""
    console.print("Reading diff from STDIN...")
    diff_text = click.get_text_stream("stdin").read()
    new_question = change_list_prompt(diff_text)
    with Progress(transient=True) as progress:
        task = progress.add_task("[green]Processing...", total=None)
        response_1 = get_response(INSTRUCTIONS, [], new_question)
        progress.update(task, completed=True)
    console.print(f"[cyan]Bot[/cyan]:\n{response_1}")


@cli.command()
def ingest():
    """Index files in current repo to be used with 'ask' and 'chat'."""
    ingest_repo()


if __name__ == "__main__":
    # pylint: disable-next=no-value-for-parameter
    cli(obj={})
