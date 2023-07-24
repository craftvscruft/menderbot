import os
import rich_click as click
from rich.progress import Progress
from rich.console import Console
from rich.prompt import Prompt, Confirm

from menderbot.llm import get_response, INSTRUCTIONS
from menderbot.doc import document_file
from menderbot.typing import process_untyped_functions
from menderbot.git_client import git_diff_head, git_commit
from menderbot.code import reindent, function_indent
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
    if not "OPENAI_API_KEY" in os.environ:
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


def type_prompt(function_text, needs_typing, previous_error=""):
    needs_typing_text = ",".join(needs_typing)
    return f"""
Please infer these missing Python type hints. 
If you cannot determine the type with confidence, use 'any'. 
Do not assume the existence any unreferenced classes outside the standard library.

Input:
def foo(a, b: int):
  return a + b

Infer: a, return
Output:
a: int
return: int

Input:
{function_text}

Previous error:
{previous_error or "None"}

Infer: {needs_typing_text}
Output:
"""


def parse_type_hint_answer(text):
    def line_to_tuple(line):
        [ident, new_type] = line.split(":")
        return (ident.strip(), new_type.strip())

    lines = text.strip().splitlines()
    hints = [line_to_tuple(line) for line in lines if ":" in line]
    return [hint for hint in hints if hint[1].lower() != "any"]


def handle_untyped_function(function_text, needs_typing):
    prompt = type_prompt(function_text, needs_typing)
    answer = get_response_with_progress(INSTRUCTIONS, [], prompt)
    console.print(f"[cyan]Bot[/cyan]:\n{answer}\n")
    return parse_type_hint_answer(answer)


@cli.command("type")
@click.argument("file")
def type_command(file):
    """Suggest type hints (Python only)"""
    source_file = SourceFile(file)
    insertions = process_untyped_functions(source_file, handle_untyped_function)
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


def change_list_prompt(diff_text):
    return f"""
- Summarize the diff into markdown hyphen-bulleted list of changes.
- Use present tense verbs like "Add/Update", not "Added/Updated".
- Do not mention trivial changes like imports that support other changes.

# BEGIN DIFF
{diff_text}
# END DIFF
"""


def code_review_prompt(diff_text):
    return f"""
Act as an expert Software Engineer. Give a code review for this diff.

# BEGIN DIFF
{diff_text}
# END DIFF
"""


def commit_msg_prompt(change_list_text):
    return f"""
From this list of changes, write a brief commit message.
- Sart with a one line summary, guessing the specific intent behind the changes including the names of any updated features. 
- Include a condensed version of the input change list formatted as a markdown list with hyphen "-" bullets. 
- Only output the new commit message, not any further conversation.
- Omit from the list trivial changes like imports
- Do not refer to anything that changes behavior as a "refactor"

# BEGIN CHANGES
{change_list_text}
# END CHANGES
"""


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
        response_2 = get_response(INSTRUCTIONS, [], question_2)
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
