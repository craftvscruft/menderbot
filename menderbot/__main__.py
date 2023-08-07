import sys

import rich_click as click
from click import Abort
from rich.console import Console
from rich.progress import Progress
from rich.prompt import Confirm

from menderbot import __version__
from menderbot.build_treesitter import (
    ensure_tree_sitter_binary,
    tree_sitter_binary_exists,
)
from menderbot.check import run_check
from menderbot.config import create_default_config, has_config, has_llm_consent
from menderbot.git_client import git_commit, git_diff_head, git_show_top_level
from menderbot.ingest import ask_index, get_chat_engine, index_exists, ingest_repo
from menderbot.llm import (
    INSTRUCTIONS,
    get_response,
    has_key,
    key_env_var,
    unwrap_codeblock,
)
from menderbot.prompts import (
    change_list_prompt,
    code_review_prompt,
    commit_msg_prompt,
    type_prompt,
)
from menderbot.source_file import SourceFile

console = Console()


@click.group(context_settings=dict(help_option_names=["-h", "--help"]))
@click.version_option(__version__, prog_name="menderbot")
@click.pass_context
def cli(ctx):
    """
    An AI-powered command line tool for working with legacy code.

    You can try using --help at the top level and also for
    specific subcommands.

    Connects to OpenAI using OPENAI_API_KEY environment variable.
    """
    if not has_key():
        console.log(f"{key_env_var()} not found in env, will not be able to connect.")
    ctx.ensure_object(dict)


@cli.command()
@click.argument("q", required=False)
def ask(q):
    """Ask a question about a specific piece of code or concept."""
    if not index_exists():
        console.print("[red]Index not found[/red]: please run menderbot ingest")
        return
    check_llm_consent()
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
    check_llm_consent()
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


def try_function_type_hints(
    mypy_cmd, source_file, tree, function_node, function_text, needs_typing
):
    from menderbot.typing import add_type_hints, parse_type_hint_answer  # Lazy import

    check_command = (
        f"{mypy_cmd} --shadow-file {source_file.path} {source_file.path}.shadow"
    )
    max_tries = 2
    check_output = None
    # First set them all to wrong type, to produce an error message.
    hints = [(ident, "None") for ident in needs_typing]
    insertions_for_function = add_type_hints(tree, function_node, hints)
    if insertions_for_function:
        source_file.update_file(insertions_for_function, suffix=".shadow")
        console.print("> ", check_command)
        (success, pre_check_output) = run_check(check_command)
        if not success:
            check_output = pre_check_output
    for try_num in range(0, max_tries):
        if try_num > 0:
            console.print("Retrying")
        prompt = type_prompt(function_text, needs_typing, previous_error=check_output)
        answer = get_response_with_progress(INSTRUCTIONS, [], prompt)
        hints = parse_type_hint_answer(answer)

        insertions_for_function = add_type_hints(tree, function_node, hints)
        if insertions_for_function:
            console.print(f"[cyan]Bot[/cyan]: {hints}")
            source_file.update_file(insertions_for_function, suffix=".shadow")
            (success, check_output) = run_check(check_command)
            if success:
                console.print("[green]Type checker passed[/green], keeping")
                return insertions_for_function
            else:
                console.out(check_output)
                console.print("\n[red]Type checker failed[/red], discarding")
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

    check_llm_consent()
    console.print("Running type-checker baseline")
    mypy_cmd = f"mypy --ignore-missing-imports --no-error-summary --soft-error-limit 10 '{file}'"
    (success, check_output) = run_check(f"{mypy_cmd}")
    if not success:
        console.print(check_output)
        console.print("Baseline failed, aborting.")
        return
    source_file = SourceFile(file)
    insertions = []
    for tree, function_node, function_text, needs_typing in process_untyped_functions(
        source_file
    ):
        insertions += try_function_type_hints(
            mypy_cmd, source_file, tree, function_node, function_text, needs_typing
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

    check_llm_consent()
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
    check_llm_consent()
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
    check_llm_consent()
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
    """
    Summarize the differences between two versions of a codebase. Takes diff from STDIN.

    Try:
      git diff HEAD | menderbot diff
      git diff main..HEAD | menderbot diff
    """
    check_llm_consent()
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
    check_llm_consent()
    ingest_repo()


def check_llm_consent():
    if not has_llm_consent():
        console.print(
            "[red]Error[/red]: This repo does not have consent recorded in .menderbot-config.yaml"
        )
        if not has_config():
            create_default_config()
        raise Abort()


@click.option(
    "--build",
    is_flag=True,
    default=False,
    help="Attempt to build Tree-Sitter if not present",
)
@cli.command()
def check(build: bool):
    """Verify we have what we need to run."""
    git_dir = git_show_top_level()
    failed = False

    def check_condition(condition, ok_msg, failed_msg):
        nonlocal failed
        if condition:
            console.print(f"[green]OK[/green]      {ok_msg}")
        else:
            console.print(f"[red]Failed[/red]  {failed_msg}")
            failed = True

    check_condition(
        git_dir, f"Git repo {git_dir}", "Not in repo directory or git not installed"
    )
    check_condition(
        tree_sitter_binary_exists(),
        "Tree-Sitter binary found",
        "Tree-Sitter binary not found, run check with --build to attempt building",
    )
    check_condition(
        has_key(),
        f"OpenAI API key found in {key_env_var()}",
        f"OpenAI API key not found in {key_env_var()}",
    )

    check_condition(
        has_llm_consent(),
        "LLM consent configured for this repo",
        "LLM consent not recorded in .menderbot-config.yaml for this repo",
    )
    if build:
        ensure_tree_sitter_binary()
    if failed:
        sys.exit(1)


if __name__ == "__main__":
    # pylint: disable-next=no-value-for-parameter
    cli(obj={})
