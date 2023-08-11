# Menderbot
![Version](https://img.shields.io/badge/version-0.0.2-blue.svg?cacheSeconds=2592000)
![Tests](https://github.com/craftvscruft/menderbot/actions/workflows/ci.yml/badge.svg?branch=main)
[![License: APACHE](https://img.shields.io/github/license/craftvscruft/menderbot)](https://github.com/craftvscruft/menderbot/blob/main/LICENSE)

> The AI-powered command line tool for working with legacy code. [Designed](./DESIGN.md) based on the principles of the [Mechanized Mending Manifesto](https://mender.ai/docs/intro).

## Status

Menderbot is usable in development of itself - a very small codebase. For instance, it's used on this project for first drafts of commit messages, it added most of the type annotations, and chat usually gives relevant answers. On codebases of an interesting size (> 10K lines) there is still much work to do.

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

## System requirements

* git
* Python 3.9+
* The environment variable `OPENAI_API_KEY` set to a valid OpenAI API Key.

### Running
Clone the project...

Install an editable version.
```
python -m pip install -e .
```

Then run with `menderbot` in any repo.

### Installing from Pip

Not yet supported, install from a local checkout for now. Upvote this [issue](https://github.com/craftvscruft/menderbot/issues/1) if you're interested.

## Developing

Clone the project...

```
git clone git@github.com:craftvscruft/menderbot.git
```

Then you can initialize your Python environment using [venv](https://docs.python.org/3/library/venv.html).

```
python -m venv venv

source venv/bin/activate

pip install "." ".[dev]"
```

If you want to re-generate the Antlr parsers, see [PARSERS.md](./PARSERS.md), but you probably won't need to.

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

## Author

👤 **Ray Myers**

* YouTube: [Craft vs Cruft](https://www.youtube.com/channel/UC4nEbAo5xFsOZDk2v0RIGHA)
* Twitter: [@lambdapocalypse](https://twitter.com/lambdapocalypse)
* GitHub: [@raymyers](https://github.com/raymyers)
* LinkedIn: [@cadrlife](https://linkedin.com/in/cadrlife)

## 🤝 Contributing

Contributions, issues and feature requests are welcome!

Feel free to check [issues page](https://github.com/craftvscruft/menderbot/issues). You can also take a look at the [contributing guide](https://github.com/craftvscruft/menderbot/blob/main/CONTRIBUTING.md).

## Show your support

Give a ⭐️ if this project helped you!
<!-- 
[![support us](https://img.shields.io/badge/become-a%20patreon%20us-orange.svg?cacheSeconds=2592000)](https://www.patreon.com/craftvscruft) -->

## Acknowledgements

* [OpenAI](https://platform.openai.com/docs/models/overview) GPT and Ada models
* [LlamaIndex](https://gpt-index.readthedocs.io/en/latest/), an LLM data framework
* [Antlr](https://www.antlr.org/) parser generator

## 📝 License

Copyright © 2023 [Ray Myers](https://github.com/raymyers).

This project is [Apache 2](https://www.apache.org/licenses/LICENSE-2.0) licensed.