import os
import shutil
import subprocess
import yaml
import click
from pathlib import Path

PROJECTS_DIR = Path("projects")
ARCHIVE_DIR = Path("archive")
REPOS_DIR = Path("repos")

def get_most_recent_ssh_key():
    """Find the most recently modified SSH private key in ~/.ssh."""
    ssh_dir = Path.home() / ".ssh"
    if not ssh_dir.exists():
        return None
    
    # Common private key patterns
    keys = list(ssh_dir.glob("id_*"))
    # Filter out public keys and sort by mtime
    private_keys = [k for k in keys if not k.suffix == ".pub"]
    if not private_keys:
        return None
    
    return sorted(private_keys, key=os.path.getmtime, reverse=True)[0]

def is_git_repo(source):
    """Check if the source is a git repository URL."""
    return source.startswith("http") or source.startswith("git@") or "ssh://" in source

def get_git_env(config):
    """Set up git environment with SSH key if needed."""
    env = os.environ.copy()
    ssh_key = config.get("ssh_key")
    if ssh_key:
        env["GIT_SSH_COMMAND"] = f"ssh -i {ssh_key} -o IdentitiesOnly=yes -o ConnectTimeout=5"
    return env

def handle_git_error(e, operation="git operation"):
    """Provide a user-friendly message for git errors, especially network issues."""
    error_msg = str(e.stderr if hasattr(e, 'stderr') else e)
    if "Could not resolve host" in error_msg or "Connection timed out" in error_msg or "network is unreachable" in error_msg.lower():
        click.echo(f"Error: Network connection to host is not available for {operation}.")
    else:
        click.echo(f"Error during {operation}: {error_msg}")

@click.group()
def cli():
    pass

def create_project(name, source, ssh_key_path=None):
    """Programmatic version of create."""
    project_path = PROJECTS_DIR / name
    project_path.mkdir(parents=True, exist_ok=True)
    (project_path / "outputs").mkdir(exist_ok=True)
    
    config = {
        "project_name": name,
        "source": source,
        "ssh_key": ssh_key_path,
        "repomix_options": {
            "output": {
                "filePath": f"projects/{name}/outputs/repomix-output.md",
                "style": "markdown"
            },
            "ignore": {
                "customPatterns": ["node_modules", ".git", ".venv"]
            }
        }
    }
    
    config_file = project_path / "repomix-config.yaml"
    with open(config_file, "w") as f:
        yaml.dump(config, f, default_flow_style=False)
    
    return {"message": f"Project '{name}' created", "path": str(project_path)}

def build_project(name):
    """Programmatic version of build."""
    project_path = PROJECTS_DIR / name
    config_file = project_path / "repomix-config.yaml"
    
    if not config_file.exists():
        return {"error": f"Project '{name}' not found or missing config."}

    with open(config_file, "r") as f:
        config = yaml.safe_load(f)
    
    source = config["source"]
    logs = []

    # Handle git repositories
    if is_git_repo(source):
        repo_path = REPOS_DIR / name
        env = get_git_env(config)
        try:
            if repo_path.exists():
                logs.append(f"Updating existing repo in {repo_path}...")
                subprocess.run(["git", "-C", str(repo_path), "pull"], check=True, env=env, capture_output=True, text=True)
            else:
                logs.append(f"Cloning repo to {repo_path}...")
                REPOS_DIR.mkdir(exist_ok=True)
                subprocess.run(["git", "clone", source, str(repo_path)], check=True, env=env, capture_output=True, text=True)
        except subprocess.CalledProcessError as e:
            error_msg = str(e.stderr if hasattr(e, 'stderr') else e)
            if "Could not resolve host" in error_msg or "Connection timed out" in error_msg:
                return {"error": f"Network connection to host is not available for cloning/pulling repository.", "logs": logs}
            return {"error": f"Error during cloning/pulling: {error_msg}", "logs": logs}
        run_path = repo_path
    else:
        run_path = Path(source)
        if not run_path.exists():
            return {"error": f"Local path {run_path} does not exist."}

    # Prepare repomix command
    repomix_config_tmp = project_path / "repomix.config.json"
    import json
    with open(repomix_config_tmp, "w") as f:
        json.dump(config.get("repomix_options", {}), f)

    logs.append(f"Running repomix on {run_path}...")
    try:
        cmd = ["repomix", str(run_path), "--config", str(repomix_config_tmp)]
        subprocess.run(cmd, check=True, capture_output=True, text=True)
        return {"success": True, "message": f"Build complete. Output in {project_path}/outputs/", "logs": logs}
    except subprocess.CalledProcessError as e:
        return {"error": f"Error running repomix: {e.stderr}", "logs": logs}
    finally:
        if repomix_config_tmp.exists():
            repomix_config_tmp.unlink()

def refresh_project(name):
    """Programmatic version of refresh."""
    project_path = PROJECTS_DIR / name
    config_file = project_path / "repomix-config.yaml"
    
    if not config_file.exists():
        return {"error": f"Project '{name}' not found."}

    with open(config_file, "r") as f:
        config = yaml.safe_load(f)
    
    source = config["source"]
    if is_git_repo(source):
        repo_path = REPOS_DIR / name
        if not repo_path.exists():
            return {"status": "cloning", "message": "Repo not found, triggering build..."}

        env = get_git_env(config)
        try:
            subprocess.run(["git", "-C", str(repo_path), "pull"], check=True, env=env, capture_output=True, text=True)
            return {"success": True, "message": f"Project '{name}' refreshed successfully."}
        except subprocess.CalledProcessError as e:
            error_msg = str(e.stderr if hasattr(e, 'stderr') else e)
            if "Could not resolve host" in error_msg or "Connection timed out" in error_msg:
                return {"error": f"Network connection to host is not available for refreshing."}
            return {"error": f"Error during refresh: {error_msg}"}
    else:
        return {"warning": f"Project '{name}' is a local project. Nothing to refresh."}

def get_project_list():
    """Programmatic version of list."""
    if not PROJECTS_DIR.exists():
        return []

    project_names = [d.name for d in PROJECTS_DIR.iterdir() if d.is_dir()]
    results = []

    for name in sorted(project_names):
        config_file = PROJECTS_DIR / name / "repomix-config.yaml"
        if not config_file.exists():
            continue

        with open(config_file, "r") as f:
            config = yaml.safe_load(f)
        
        source = config["source"]
        source_type = "Git" if is_git_repo(source) else "Local"
        status = "N/A"
        
        if source_type == "Git":
            repo_path = REPOS_DIR / name
            if not repo_path.exists():
                status = "Not Cloned"
            else:
                env = get_git_env(config)
                try:
                    subprocess.run(["git", "-C", str(repo_path), "fetch"], check=True, env=env, capture_output=True, text=True, timeout=5)
                    local = subprocess.check_output(["git", "-C", str(repo_path), "rev-parse", "HEAD"], text=True).strip()
                    try:
                        remote = subprocess.check_output(["git", "-C", str(repo_path), "rev-parse", "@{u}"], text=True, stderr=subprocess.DEVNULL).strip()
                        status = "Fresh" if local == remote else "Need Refresh"
                    except subprocess.CalledProcessError:
                        status = "No Upstream"
                except:
                    status = "Network Error"
        else:
            status = "Local" if Path(source).exists() else "Missing"

        results.append({
            "name": name,
            "type": source_type,
            "status": status,
            "source": source
        })
    return results

def clean_project(name):
    """Programmatic version of clean."""
    outputs_dir = PROJECTS_DIR / name / "outputs"
    if outputs_dir.exists():
        shutil.rmtree(outputs_dir)
        outputs_dir.mkdir()
        return {"success": True, "message": f"Cleaned outputs for {name}"}
    return {"error": f"No outputs found for {name}"}

def archive_project(name):
    """Programmatic version of archive."""
    project_path = PROJECTS_DIR / name
    if not project_path.exists():
        return {"error": f"Project '{name}' not found."}
    
    ARCHIVE_DIR.mkdir(exist_ok=True)
    archive_name = ARCHIVE_DIR / f"{name}_archive"
    shutil.make_archive(str(archive_name), 'zip', str(project_path))
    shutil.rmtree(project_path)
    return {"success": True, "message": f"Project '{name}' archived to {archive_name}.zip"}

@cli.command()
def create():
    """Interactively create a new project."""
    name = click.prompt("Enter project name")
    source = click.prompt("Enter source (local path or git URL)")
    
    ssh_key_path = None
    if source.startswith("git@") or "ssh://" in source:
        recent_key = get_most_recent_ssh_key()
        if recent_key:
            if click.confirm(f"Found recent SSH key: {recent_key}. Use this?", default=True):
                ssh_key_path = str(recent_key)
        
        if not ssh_key_path:
            ssh_key_path = click.prompt("Please provide the path to the SSH key to use")
            ssh_key_path = os.path.expanduser(ssh_key_path)

    res = create_project(name, source, ssh_key_path)
    click.echo(res["message"])
    
    if click.confirm("Would you like to run the initial build now?", default=True):
        build.callback(name)

@cli.command()
@click.argument("name")
def build(name):
    """Run repomix for a specific project."""
    res = build_project(name)
    if "error" in res:
        click.echo(f"Error: {res['error']}")
    else:
        for log in res.get("logs", []):
            click.echo(log)
        click.echo(res["message"])

@cli.command()
@click.argument("name")
def refresh(name):
    """Pull from remote git repository if applicable."""
    res = refresh_project(name)
    if "error" in res:
        click.echo(f"Error: {res['error']}")
    elif "warning" in res:
        click.echo(f"Warning: {res['warning']}")
    elif res.get("status") == "cloning":
        click.echo(res["message"])
        build.callback(name)
    else:
        click.echo(res["message"])

@cli.command(name="list")
def list_projects_cli():
    """List all projects and their status."""
    results = get_project_list()
    if not results:
        click.echo("No projects found.")
        return

    click.echo(f"{'PROJECT':<25} {'TYPE':<10} {'STATUS':<15} {'SOURCE'}")
    click.echo("-" * 80)
    for p in results:
        click.echo(f"{p['name']:<25} {p['type']:<10} {p['status']:<15} {p['source']}")

@cli.command()
@click.argument("name")
def clean(name):
    """Clean outputs for a specific project."""
    res = clean_project(name)
    if "error" in res:
        click.echo(res["error"])
    else:
        click.echo(res["message"])

@cli.command()
@click.argument("name")
def archive(name):
    """Archive a project and remove it."""
    res = archive_project(name)
    if "error" in res:
        click.echo(res["error"])
    else:
        click.echo(res["message"])

if __name__ == "__main__":
    cli()
