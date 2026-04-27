# Release Summary: v1.1.0 (Web UI & SSH Enhancements)

**Date**: April 27, 2026

## Overview
This release marks a significant milestone for **Repomix Project Manager**, evolving it from a command-line interface tool into a full-featured, containerized web application. The core objective of this release was to provide a premium, accessible interface for managing multiple Repomix configurations and outputs while ensuring reproducible deployments across environments.

## ✨ Key Features & Enhancements

### 1. Premium Web Dashboard
- **Glassmorphism UI**: A responsive, dark-mode web interface built with vanilla HTML/CSS and Javascript, focusing on premium aesthetics.
- **Project Grid**: Real-time visualization of all projects, indicating source type (Local/Git) and current status (Fresh, Needs Refresh, Not Cloned).
- **1-Click Actions**: Interactive buttons to Build, Refresh, Clean, View, Download, and Archive projects directly from the browser.
- **Cross-Browser Downloads**: Implemented explicit routing and HTTP headers (`Content-Disposition`) to ensure bulletproof file downloads across Safari and Google Chrome, circumventing browser UUID heuristics.

### 2. FastAPI Backend Integration
- **RESTful API**: Refactored the core Python logic (`manage_projects.py`) to separate the CLI interface from the business logic, enabling programmatic access.
- **Endpoints**: Introduced `server.py` to serve the web UI and provide endpoints for all project management tasks (`/api/projects`).

### 3. Docker Containerization
- **Multi-Runtime Image**: Created a custom `Dockerfile` based on `python:3.11-slim` that integrates both Python dependencies and Node.js (`repomix`).
- **Virtual Environment Isolation**: Implemented isolated Python environments (`/opt/venv`) inside the container to align with modern `pip` deployment standards and prevent system interference.
- **Host Syncing**: Configured volume mounts to seamlessly synchronize `projects/`, `repos/`, and `archive/` directories, as well as live code mounts (`server.py`, `web/`) for rapid development.

### 4. CLI Workflow Additions
- **Interactive Prompts**: `make project` now features improved user interactions, including an optional prompt to immediately build the repomix configuration after creation.
- **Expanded Makefile**: Added targets `make web`, `make docker-build`, `make docker-run`, `make docker-logs`, and a unified `make docker-restart` for streamlined operations.

### 5. Advanced SSH Key Management
- **Project-Isolated Keys**: SSH authentication is now isolated per-project. During creation or via the UI, keys are copied directly into the project folder (`.ssh_key`). This guarantees Git operations inside the Docker container always succeed without relying on host file mappings.
- **Unified Upload & Paste**: The Web UI features intuitive dialogs allowing you to optionally upload a private key file `.pem/.key` or manually paste the raw text into a secure textarea.
- **Docker ControlMaster Bypass**: Solved a systemic issue where Docker on Mac would crash when attempting to bind to Unix sockets (`Operation not supported`). The system now forces `ControlMaster=no` locally to ensure zero-configuration Git cloning.

## 🛠️ Technical Debt Addressed
- **Namespace Shadowing**: Fixed a critical bug where the CLI `list` command was shadowing Python's built-in `list` function, causing errors during SSH key discovery.
- **Git Network Handling**: Improved error catching for `subprocess` calls to elegantly handle network timeouts or DNS resolution failures during repository cloning.

## 🚀 Upgrade Instructions
If upgrading from a previous version, ensure you rebuild your Docker container to capture the new backend routes and UI assets:
```bash
make docker-restart
```
