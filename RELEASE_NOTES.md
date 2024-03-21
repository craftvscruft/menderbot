## v0.0.5
Update llama_index and open_ai dependencies

## v0.0.4
## v0.0.3

## v0.0.2

Welcome to the first public release of Menderbot, the AI-powered command line tool for working with legacy code.

**Full Changelog**: https://github.com/craftvscruft/menderbot/commits/v0.0.2

## New Contributors
* @raymyers wrote what you see here so far, feel free to [reach out](https://www.linkedin.com/in/cadrlife/) to get involved!

## Status

Currently, menderbot is usable in development of itself - a very small codebase. For instance, it's used on this project for first drafts of commit messages, it added most of the type annotations, and chat usually gives relevant answers. On codebases of an interesting size (> 10K lines) there is still much work to do.

## Commands implemented (-ish):

* `menderbot ask`: Ask a question about the codebase
* `menderbot chat`: Interactively chat about the codebase
* `menderbot commit`: Git commit the current changeset with a pre-populated commit message
* `menderbot diff`: Summarize the differences between two versions of a codebase
* `menderbot doc`: Generate documentation for the existing code (Python only)
* `menderbot review`: Review a code block or changeset and provide feedback
* `menderbot type`: Insert type hints (Python only)
* `menderbot ingest`: Index the current state of the repo for `ask` and `chat` commands
* `menderbot check`: Verify we have what we need to run

