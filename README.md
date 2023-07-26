# Menderbot
![Version](https://img.shields.io/badge/version-0.0.1-blue.svg?cacheSeconds=2592000)
![Tests](https://github.com/craftvscruft/menderbot/actions/workflows/ci.yml/badge.svg?branch=main)
[![License: APACHE](https://img.shields.io/github/license/craftvscruft/menderbot)](https://github.com/craftvscruft/menderbot/blob/main/LICENSE)

> AI-powered command line tool for working with legacy code. Based on the principles of the [Mechanized Mending Manifesto](https://mender.ai/docs/intro).

## Commands implemented (-ish):

* `menderbot ask`: Ask a question about a specific piece of code or concept
* `menderbot chat`: Interactively chat in the context of the current directory
* `menderbot commit`: Generate an informative commit message based on a changeset
* `menderbot diff`: Summarize the differences between two versions of a codebase
* `menderbot doc`: Generate documentation for the existing code (Python only)
* `menderbot review`: Review a code block or changeset and provide feedback
* `menderbot type`: Insert type hints (Python only)


## System requirements

* [pipenv](https://pipenv.pypa.io/en/latest/) (for managing Python environments)
* C Compiler
* The environment variable `OPENAI_API_KEY` set to a valid OpenAI API Key.

## Developing

This project uses [git submodules](https://git-scm.com/book/en/v2/Git-Tools-Submodules) for the parser grammars, so you'll want to clone it this way.

```
git clone --recurse-submodules git@github.com:craftvscruft/menderbot.git
```

Then you can initialize the Python environment using pipenv.

```
pipenv shell
```
### Running

While in the pipenv shell, install editable version.
```
python -m pip install -e .
```

Then run with `menderbot`.

### Installing

Not yet supported, run within pipenv on a local checkout for now. Upvote this [issue](https://github.com/craftvscruft/menderbot/issues/1) if you're interested.

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