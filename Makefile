.PHONY: env project build clean archive help

# Project variables
VENV := .venv
PYTHON := $(VENV)/bin/python
PIP := $(VENV)/bin/pip

help:
	@echo "Usage:"
	@echo "  make env                - Setup local environment and install dependencies"
	@echo "  make project            - Interactively create a new project configuration"
	@echo "  make build NAME=<name>  - Run repomix for a specific project"
	@echo "  make clean NAME=<name>  - Clean outputs for a specific project"
	@echo "  make archive NAME=<name> - Archive a project and remove it from projects/"

env:
	@echo "Setting up environment..."
	@if [ ! -d "$(VENV)" ]; then python3 -m venv $(VENV); fi
	@$(PIP) install --upgrade pip
	@$(PIP) install pyyaml click
	@if [ "$$(uname)" = "Darwin" ]; then \
		if ! command -v repomix >/dev/null 2>&1; then \
			echo "Installing repomix via brew..."; \
			brew install repomix; \
		else \
			echo "repomix is already installed."; \
		fi \
	fi
	@mkdir -p projects archive repos
	@echo "Environment setup complete."

project:
	@$(PYTHON) manage_projects.py create

build:
	@if [ -z "$(NAME)" ]; then echo "Error: NAME is required. Example: make build NAME=my-project"; exit 1; fi
	@$(PYTHON) manage_projects.py build $(NAME)

clean:
	@if [ -z "$(NAME)" ]; then echo "Error: NAME is required. Example: make clean NAME=my-project"; exit 1; fi
	@$(PYTHON) manage_projects.py clean $(NAME)

archive:
	@if [ -z "$(NAME)" ]; then echo "Error: NAME is required. Example: make archive NAME=my-project"; exit 1; fi
	@$(PYTHON) manage_projects.py archive $(NAME)
