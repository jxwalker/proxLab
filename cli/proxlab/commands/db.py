import typer
from rich.console import Console
from rich.table import Table
from rich import box
from proxlab.client import api_get, api_post, api_delete

app = typer.Typer(help="Manage Postgres databases")
console = Console()


@app.command("list")
def list_dbs():
    dbs = api_get("/api/databases")
    if not dbs:
        console.print("[dim]No databases.[/dim]")
        return
    table = Table(box=box.ROUNDED, header_style="bold cyan")
    table.add_column("Name")
    table.add_column("Owner")
    table.add_column("Size (MB)", justify="right")
    for d in dbs:
        table.add_row(d["name"], d["owner"], str(d["size_mb"]))
    console.print(table)


@app.command("create")
def create_db(name: str = typer.Argument(...)):
    """Create a Postgres database + user. Prints the connection string."""
    with console.status(f"Creating database {name}..."):
        result = api_post("/api/databases", json={"name": name})
    console.print(f"[green]✓[/green] Database [bold]{result['name']}[/bold] created")
    console.print(f"  Owner:   {result['owner']}")
    console.print(f"  [bold]DSN:[/bold]    [cyan]{result['connection_string']}[/cyan]")


@app.command("info")
def db_info(name: str = typer.Argument(...)):
    """Show connection info for an existing database."""
    result = api_get(f"/api/databases/{name}")
    console.print(f"[bold]{result['name']}[/bold]  owner={result['owner']}  size={result['size_mb']} MB")
    console.print(f"  [cyan]{result['connection_string']}[/cyan]")


@app.command("drop")
def drop_db(name: str, yes: bool = typer.Option(False, "--yes", "-y")):
    """Drop a database and its owner role."""
    if not yes:
        typer.confirm(f"Drop database '{name}'?", abort=True)
    api_delete(f"/api/databases/{name}")
    console.print(f"[red]✗[/red] Database '{name}' dropped")
