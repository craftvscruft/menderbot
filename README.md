# Menderbot
AI-powered command line tool for working with legacy code. Based on the principles of the [Mechanized Mending Manifesto](https://mender.ai/docs/intro).

## Commands implemented (-ish):

* `menderbot ask`: Ask a question about a specific piece of code or concept
* `menderbot chat`: Interactively chat in the context of the current directory
* `menderbot commit`: Generate an informative commit message based on a changeset
* `menderbot diff`: Summarize the differences between two versions of a codebase
* `menderbot doc`: Generate documentation for the existing code (Python only)
* `menderbot review`: Review a code block or changeset and provide feedback
* `menderbot type`: Insert type hints (Python only)


## Developing

```
pipenv shell

python -m menderbot.build_treesitter
```
### Running

While in the pipenv shell, install editable version.
```
python -m pip install -e .
```

Then run with `menderbot`.

### Pre-commit

Formatting, linting, tests, and type-checking can all be run through pre-commit, configured in `.pre-commit-config`.

```
pre-commit run --all-files
```

Install this as a git hook with `pre-commit install`.

Or you can run individual steps

```
isort menderbot tests
black menderbot tests
pylint --disable=C,R menderbot
pytest
mypy
```