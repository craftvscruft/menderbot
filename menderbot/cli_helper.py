"""
Everything cli.py does besides declare commands goes here.

Eventually this module shouldn't exist, everything should move other places.
https://www.yanglinzhao.com/posts/utils-antipattern/
"""
import os

from click import Abort
from rich.console import Console
from rich.progress import Progress

from menderbot.check import run_check
from menderbot.code import LANGUAGE_STRATEGIES
from menderbot.config import create_default_config, has_config, has_llm_consent
from menderbot.llm import INSTRUCTIONS, get_response
from menderbot.prompts import type_prompt
from menderbot.source_file import SourceFile

console = Console()


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


def check_llm_consent():
    if not has_llm_consent():
        console.print(
            "[red]Error[/red]: This repo does not have consent recorded in .menderbot-config.yaml"
        )
        if not has_config():
            create_default_config()
        raise Abort()


def render_functions_for_file(file: str) -> dict:
    source_file = SourceFile(file)
    path = source_file.path
    _, file_extension = os.path.splitext(path)
    language_strategy = LANGUAGE_STRATEGIES.get(file_extension)
    if not language_strategy:
        return {
            "items": [],
            "error": f'Unrecognized extension "{file_extension}", skipping.',
        }

    source = source_file.load_source_as_utf8()
    tree = language_strategy.parse_source_to_tree(source)
    functions = [
        {"name": language_strategy.get_function_node_name(node)}
        for node in language_strategy.get_function_nodes(tree)
    ]
    return {"items": functions}
