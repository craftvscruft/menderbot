import os
import re

import rich_click as click
from rich.console import Console
from rich.progress import Progress
from rich.prompt import Confirm, Prompt

from menderbot.check import run_check
from menderbot.code import function_indent, reindent
from menderbot.doc import document_file
from menderbot.git_client import git_commit, git_diff_head
from menderbot.llm import INSTRUCTIONS, get_response, unwrap_codeblock
from menderbot.prompts import (
    change_list_prompt,
    code_review_prompt,
    commit_msg_prompt,
    type_prompt,
)
from menderbot.source_file import SourceFile
from menderbot.typing import add_type_hints, process_untyped_functions

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
@click.version_option("0.0.1", prog_name="menderbot")
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
    new_question = q
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


def parse_type_hint_answer(text):
    def line_to_tuple(line):
        [ident, new_type] = line.split(":")
        new_type = re.sub(r"\bList\b", "list", new_type)
        return (ident.strip(), new_type.strip())

    lines = text.strip().splitlines()
    hints = [line_to_tuple(line) for line in lines if ":" in line]
    return [hint for hint in hints if hint[0] != "self" and hint[1].lower() != "any"]


def try_function_type_hints(source_file, function_node, function_text, needs_typing):
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
            # console.print("Hint", check_output)
    for try_num in range(0, max_tries):
        if try_num > 0:
            console.print("Retrying")
        prompt = type_prompt(function_text, needs_typing, previous_error=check_output)
        # console.print(f"[cyan]Prompt[/cyan]:\n{prompt}\n")
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
    """Generate documentation for the existing code."""
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
    """Review a code block or changeset and provide feedback"""
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


if __name__ == "__main__":
    # pylint: disable-next=no-value-for-parameter
    cli(obj={})
