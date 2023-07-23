import logging
import os
import string
import rich_click as click
from rich.progress import Progress
from rich.console import Console
from rich.prompt import Prompt, Confirm

from menderbot.llm import get_response, INSTRUCTIONS
from menderbot.doc import document_file
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
    # print(f"Debug mode is {'on' if debug else 'off'}")
    if not "OPENAI_API_KEY" in os.environ:
        console.log("OPENAI_API_KEY not found in env, will not be able to connect.")
    ctx.ensure_object(dict)
    ctx.obj['DRY'] = dry

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



def generate_doc(code, file_extension):
    if not file_extension == '.py':
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
        doc = get_response(INSTRUCTIONS, [], question)
        progress.update(task, completed=True)
        if '"""' in doc:
            doc = doc[0 : doc.rfind('"""') + 3]
            doc = doc[doc.find('"""'):]
            indent = function_indent(code)
            doc = reindent(doc, indent)
        return doc


@cli.command()
@click.pass_context
@click.argument("file")
def doc(ctx, file):
    """Generate documentation for the existing code."""
    source_file = SourceFile(file)
    insertions = document_file(source_file, generate_doc)
    if not insertions:
        console.print(f"No updates found for '{file}'.")
        return
    if not Confirm.ask(f"Write '{file}'?"):
        console.print(f"Skipping.")
    source_file.update_file(insertions, suffix='')
    console.print(f"Done.")
        

@cli.command()
def review():
    """Review a code block or changeset and provide feedback"""
    print("TODO")



def change_list_prompt(diff):
    return f"""
- Summarize the diff into markdown hyphen-bulleted list of changes.
- Use present tense verbs like "Add/Update", not "Added/Updated".
- Do not mention trivial changes like imports that support other changes.

# BEGIN DIFF
{diff}
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
    diff = git_diff_head(staged=True)
    new_question = change_list_prompt(diff)
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
    diff = git_diff_head()
    new_question = change_list_prompt(diff)
    with Progress(transient=True) as progress:
        task = progress.add_task("[green]Processing...", total=None)
        response_1 = get_response(INSTRUCTIONS, [], new_question)
        progress.update(task, completed=True)
    console.print(f"[cyan]Bot[/cyan]:\n{response_1}")


if __name__ == "__main__":
    # pylint: disable-next=no-value-for-parameter
    cli(obj={})
