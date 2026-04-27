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
    
    click.echo(f"Project '{name}' created at {project_path}")

@cli.command()
@click.argument("name")
def build(name):
    """Run repomix for a specific project."""
    project_path = PROJECTS_DIR / name
    config_file = project_path / "repomix-config.yaml"
    
    if not config_file.exists():
        click.echo(f"Error: Project '{name}' not found or missing config.")
        return

    with open(config_file, "r") as f:
        config = yaml.safe_load(f)
    
    source = config["source"]
    
    # Handle git repositories
    if is_git_repo(source):
        repo_path = REPOS_DIR / name
        env = get_git_env(config)
        try:
            if repo_path.exists():
                click.echo(f"Updating existing repo in {repo_path}...")
                subprocess.run(["git", "-C", str(repo_path), "pull"], check=True, env=env, capture_output=True, text=True)
            else:
                click.echo(f"Cloning repo to {repo_path}...")
                REPOS_DIR.mkdir(exist_ok=True)
                subprocess.run(["git", "clone", source, str(repo_path)], check=True, env=env, capture_output=True, text=True)
        except subprocess.CalledProcessError as e:
            handle_git_error(e, "cloning/pulling repository")
            return
        run_path = repo_path
    else:
        run_path = Path(source)
        if not run_path.exists():
            click.echo(f"Error: Local path {run_path} does not exist.")
            return

    # Prepare repomix command
    repomix_config_tmp = project_path / "repomix.config.json"
    import json
    with open(repomix_config_tmp, "w") as f:
        json.dump(config.get("repomix_options", {}), f)

    click.echo(f"Running repomix on {run_path}...")
    try:
        subprocess.run([
            "repomix", 
            str(run_path), 
            "--config", str(repomix_config_tmp)
        ], check=True)
        click.echo(f"Build complete. Output in {project_path}/outputs/")
    except subprocess.CalledProcessError as e:
        click.echo(f"Error running repomix: {e}")
    finally:
        if repomix_config_tmp.exists():
            repomix_config_tmp.unlink()

@cli.command()
@click.argument("name")
def refresh(name):
    """Pull from remote git repository if applicable."""
    project_path = PROJECTS_DIR / name
    config_file = project_path / "repomix-config.yaml"
    
    if not config_file.exists():
        click.echo(f"Error: Project '{name}' not found.")
        return

    with open(config_file, "r") as f:
        config = yaml.safe_load(f)
    
    source = config["source"]
    if is_git_repo(source):
        repo_path = REPOS_DIR / name
        if not repo_path.exists():
            click.echo(f"Project '{name}' repo not found. Running build to clone...")
            build.callback(name)
            return

        env = get_git_env(config)
        try:
            click.echo(f"Refreshing {name} from {source}...")
            subprocess.run(["git", "-C", str(repo_path), "pull"], check=True, env=env, capture_output=True, text=True)
            click.echo(f"Project '{name}' refreshed successfully.")
        except subprocess.CalledProcessError as e:
            handle_git_error(e, f"refreshing {name}")
    else:
        click.echo(f"Warning: Project '{name}' is a local project (path: {source}). Nothing to refresh.")

@cli.command()
def list():
    """List all projects and their status."""
    if not PROJECTS_DIR.exists():
        click.echo("No projects found.")
        return

    projects = [d.name for d in PROJECTS_DIR.iterdir() if d.is_dir()]
    if not projects:
        click.echo("No projects found.")
        return

    click.echo(f"{'PROJECT':<25} {'TYPE':<10} {'STATUS':<15} {'SOURCE'}")
    click.echo("-" * 80)

    for name in sorted(projects):
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
                    # Fetch in background to check for updates
                    subprocess.run(["git", "-C", str(repo_path), "fetch"], check=True, env=env, capture_output=True, text=True, timeout=10)
                    
                    # Compare local HEAD with upstream
                    local = subprocess.check_output(["git", "-C", str(repo_path), "rev-parse", "HEAD"], text=True).strip()
                    try:
                        remote = subprocess.check_output(["git", "-C", str(repo_path), "rev-parse", "@{u}"], text=True, stderr=subprocess.DEVNULL).strip()
                        if local == remote:
                            status = "Fresh"
                        else:
                            status = "Need Refresh"
                    except subprocess.CalledProcessError:
                        status = "No Upstream"
                except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as e:
                    status = "Network Error"
        else:
            status = "Local" if Path(source).exists() else "Missing"

        click.echo(f"{name:<25} {source_type:<10} {status:<15} {source}")

@cli.command()
@click.argument("name")
def clean(name):
    """Clean outputs for a specific project."""
    outputs_dir = PROJECTS_DIR / name / "outputs"
    if outputs_dir.exists():
        shutil.rmtree(outputs_dir)
        outputs_dir.mkdir()
        click.echo(f"Cleaned outputs for {name}")
    else:
        click.echo(f"No outputs found for {name}")

@cli.command()
@click.argument("name")
def archive(name):
    """Archive a project and remove it."""
    project_path = PROJECTS_DIR / name
    if not project_path.exists():
        click.echo(f"Error: Project '{name}' not found.")
        return
    
    ARCHIVE_DIR.mkdir(exist_ok=True)
    archive_name = ARCHIVE_DIR / f"{name}_archive"
    shutil.make_archive(str(archive_name), 'zip', str(project_path))
    
    shutil.rmtree(project_path)
    click.echo(f"Project '{name}' archived to {archive_name}.zip and removed from projects/")

if __name__ == "__main__":
    cli()
