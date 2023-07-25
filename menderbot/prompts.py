def type_prompt(function_text: str, needs_typing: list, previous_error: str) -> str:
    # print("previous_error", previous_error)
    needs_typing_text = ",".join(needs_typing)
    # Do not assume the existence any unreferenced classes outside the standard library unless you see.
    return f"""
Please infer these missing Python type hints. 
If you cannot determine the type with confidence, use 'any'. 
The lowercase built-in types available include: int, str, list, set, dict, tuple. 
You will be shown a previous error message from the type-checker with useful clues.

Input:
```
def foo(a, b: int, unk):
return a + b
```
Previous error: 
```
error: Argument 3 to "foo" has incompatible type "LightBulb"; expected "NoReturn"  [arg-type]
```
Infer: a, unk, return
Output:
a: int
unk: LightBulb
return: int

Input:
```
{function_text}
```
Previous error:
```
{previous_error}
```
Infer: {needs_typing_text}
Output:
"""


def change_list_prompt(diff_text: str) -> str:
    return f"""
- Summarize the diff into markdown hyphen-bulleted list of changes.
- Use present tense verbs like "Add/Update", not "Added/Updated".
- Do not mention trivial changes like imports that support other changes.

# BEGIN DIFF
{diff_text}
# END DIFF
"""


def code_review_prompt(diff_text: str) -> str:
    return f"""
Act as an expert Software Engineer. Give a code review for this diff.

# BEGIN DIFF
{diff_text}
# END DIFF
"""


def commit_msg_prompt(change_list_text: str) -> str:
    return f"""
From this list of changes, write a brief commit message.
- Sart with a one line summary, guessing the specific intent behind the changes including the names of any updated features. 
- Include a condensed version of the input change list formatted as a markdown list with hyphen "-" bullets. 
- Only output the new commit message, not any further conversation.
- Omit from the list trivial changes like imports
- Do not refer to anything that changes behavior as a "refactor"

Example Output:
```
Refactor foo module

* Add types to foo.bar
* Extract baz logic from foo.main to foo.baz
* Formatting
```

# BEGIN CHANGES
{change_list_text}
# END CHANGES

Output:
"""
