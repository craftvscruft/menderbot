# define the name of the virtual environment directory
VENV := venv

# default target, when make executed without arguments
all: venv

$(VENV)/bin/activate: pyproject.toml
	python3 -m venv $(VENV)
	./$(VENV)/bin/pip install "." ".[dev]"

# venv is a shortcut target
venv: $(VENV)/bin/activate

install: venv
	./$(VENV)/bin/python3 -m pip install -e .

clean:
	rm -rf $(VENV)
	find . -type f -name '*.pyc' -delete

test: venv
	./$(VENV)/bin/python3 -m pytest tests

coverage: venv
	./$(VENV)/bin/python3 -m pytest tests --cov --cov-fail-under=50 --cov-report html
	-open "htmlcov/index.html"

type: venv
	./$(VENV)/bin/python3 -m mypy menderbot

lint: venv
	./$(VENV)/bin/python3 -m pylint --disable=C,R menderbot

format: venv
	./$(VENV)/bin/python3 -m isort menderbot tests
	./$(VENV)/bin/python3 -m black menderbot tests

check: test type format lint

docker:
	docker build . -t menderbot:latest
	@echo Image built.
	@echo
	@echo Now you can go into your target repo and run "menderbot check" with:
	@echo "  docker run -e OPENAI_API_KEY -it -v "\$$PWD:/target" menderbot:latest check"
	@echo
	@echo "Maybe you'd like to alias it?"
	@echo "  alias menderbot-docker='docker run -e OPENAI_API_KEY -it -v "\$$PWD:/target" menderbot:latest'"

.PHONY: all venv check install clean test type lint format coverage docker clean-docker