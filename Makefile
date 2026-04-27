.PHONY: env project build clean archive refresh list web docker-build docker-run docker-stop docker-logs docker-restart help

# Project variables
VENV := .venv
PYTHON := $(VENV)/bin/python
PIP := $(VENV)/bin/pip

help:
	@echo "Usage:"
	@echo "  make env                - Setup local environment and install dependencies"
	@echo "  make project            - Interactively create a new project configuration"
	@echo "  make list               - List all projects and their status"
	@echo "  make build NAME=<name>  - Run repomix for a specific project"
	@echo "  make refresh NAME=<name> - Pull latest changes from remote (git projects only)"
	@echo "  make clean NAME=<name>  - Clean outputs for a specific project"
	@echo "  make archive NAME=<name> - Archive a project and remove it from projects/"
	@echo "  make web                - Start the web interface locally"
	@echo "  make docker-build       - Build the Docker image"
	@echo "  make docker-run         - Run the web interface in a Docker container"
	@echo "  make docker-stop        - Stop the Docker container"
	@echo "  make docker-logs        - Tail the Docker container logs"
	@echo "  make docker-restart     - Stop, rebuild, and restart the container"

env:
	@echo "Setting up environment..."
	@if [ ! -d "$(VENV)" ]; then python3 -m venv $(VENV); fi
	@$(PIP) install --upgrade pip
	@$(PIP) install pyyaml click fastapi uvicorn pydantic python-multipart
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

list:
	@$(PYTHON) manage_projects.py list

build:
	@if [ -z "$(NAME)" ]; then echo "Error: NAME is required. Example: make build NAME=my-project"; exit 1; fi
	@$(PYTHON) manage_projects.py build $(NAME)

refresh:
	@if [ -z "$(NAME)" ]; then echo "Error: NAME is required. Example: make refresh NAME=my-project"; exit 1; fi
	@$(PYTHON) manage_projects.py refresh $(NAME)

clean:
	@if [ -z "$(NAME)" ]; then echo "Error: NAME is required. Example: make clean NAME=my-project"; exit 1; fi
	@$(PYTHON) manage_projects.py clean $(NAME)

archive:
	@if [ -z "$(NAME)" ]; then echo "Error: NAME is required. Example: make archive NAME=my-project"; exit 1; fi
	@$(PYTHON) manage_projects.py archive $(NAME)

web:
	@echo "Starting web server on http://localhost:8000..."
	@$(PYTHON) server.py

DOCKER_IMAGE := repomix-manager
DOCKER_CONTAINER := repomix-manager-instance

docker-build:
	@echo "Building Docker image $(DOCKER_IMAGE)..."
	@docker build -t $(DOCKER_IMAGE) .

docker-run:
	@echo "Running $(DOCKER_IMAGE) in container..."
	@docker run -d \
		--name $(DOCKER_CONTAINER) \
		-p 8000:8000 \
		-v $$(pwd)/projects:/app/projects \
		-v $$(pwd)/repos:/app/repos \
		-v $$(pwd)/archive:/app/archive \
		-v $$(pwd)/server.py:/app/server.py \
		-v $$(pwd)/manage_projects.py:/app/manage_projects.py \
		-v $$(pwd)/web:/app/web \
		-v $$HOME/.ssh:/root/.ssh:ro \
		$(DOCKER_IMAGE)
	@echo "Web interface is now running at http://localhost:8000"

docker-stop:
	@echo "Stopping and removing container $(DOCKER_CONTAINER)..."
	@docker stop $(DOCKER_CONTAINER) || true
	@docker rm $(DOCKER_CONTAINER) || true

docker-logs:
	@docker logs -f $(DOCKER_CONTAINER)

docker-restart: docker-stop docker-build docker-run
