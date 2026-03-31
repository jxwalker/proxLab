import typer
from pathlib import Path

app = typer.Typer(help="Configure API URL and token")

CONFIG_DIR = Path.home() / ".config" / "proxlab"
CONFIG_FILE = CONFIG_DIR / "config.toml"


@app.command("set")
def set_config(
    url: str = typer.Option(..., help="Base URL for proxlab API (e.g. http://proxlab.local/api)"),
    token: str = typer.Option(..., help="API token")
):
    """
    Save API URL + token to ~/.config/proxlab/config.toml.
    """
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    CONFIG_FILE.write_text(
        f'api_url = "{url}"\n'
        f'api_token = "{token}"\n'
    )
    typer.echo(f"Saved configuration to {CONFIG_FILE}")
