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
    ssh_key = config.get("ssh_key")
    
    env = os.environ.copy()
    if ssh_key:
        env["GIT_SSH_COMMAND"] = f"ssh -i {ssh_key} -o IdentitiesOnly=yes"

    # Handle git repositories
    if source.startswith("http") or source.startswith("git@") or "ssh://" in source:
        repo_path = REPOS_DIR / name
        if repo_path.exists():
            click.echo(f"Updating existing repo in {repo_path}...")
            subprocess.run(["git", "-C", str(repo_path), "pull"], check=True, env=env)
        else:
            click.echo(f"Cloning repo to {repo_path}...")
            REPOS_DIR.mkdir(exist_ok=True)
            subprocess.run(["git", "clone", source, str(repo_path)], check=True, env=env)
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
