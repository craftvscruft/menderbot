import sys

import rich_click as click
from rich.progress import Progress
from rich.prompt import Confirm

from menderbot import __version__
from menderbot.check import run_check
from menderbot.cli_helper import (
    check_llm_consent,
    console,
    generate_doc,
    render_functions_for_file,
    try_function_type_hints,
)
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
from menderbot.prompts import change_list_prompt, code_review_prompt, commit_msg_prompt
from menderbot.source_file import SourceFile


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


@cli.command()
def check():
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
        has_key(),
        f"OpenAI API key found in {key_env_var()}",
        f"OpenAI API key not found in {key_env_var()}",
    )
    if not has_config():
        create_default_config("No .menderbot-config.yaml file found, creating...")
    check_condition(
        has_llm_consent(),
        "LLM consent configured for this repo",
        "LLM consent not recorded in .menderbot-config.yaml for this repo, please edit it",
    )
    if failed:
        sys.exit(1)


@cli.group()
def plumbing():
    """
    Internal goodies used by other features, such as syntax manipulation
    """


@plumbing.command()
@click.argument("file")
def functions(file):
    """
    Show some info about functions in a file as json.

    Uses definitions only for languages that separate declarations.
    Do not rely on this format, it will change before 1.0.0
    """
    data = render_functions_for_file(file)
    console.print_json(data=data)
    if data.get("error"):
        sys.exit(1)
