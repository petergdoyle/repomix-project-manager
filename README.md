# Repomix Code Inspector

A wrapper around [repomix](https://github.com/yamadashy/repomix) to manage multiple projects easily.

## Features
- **Project Management**: Create and store configurations for different repositories.
- **Git Support**: Automatically clones or pulls remote repositories before running repomix.
- **Local Support**: Point to any local directory on your machine.
- **Configurable**: Each project has its own `repomix-config.yaml`.

## Getting Started

### 1. Setup Environment
```bash
make env
```
This will create a virtual environment, install Python dependencies, and install `repomix` via Homebrew (on macOS).

### 2. Create a Project
```bash
make project
```
Follow the prompts to enter a project name and source (URL or path).

### 3. Build a Project
```bash
make build NAME=my-project
```
This will fetch the source and run repomix. The output will be in `projects/my-project/outputs/`.

### 4. Clean a Project
```bash
make clean NAME=my-project
```

### 5. Archive a Project
```bash
make archive NAME=my-project
```
Zips the project config and outputs into the `archive/` folder and removes it from `projects/`.
