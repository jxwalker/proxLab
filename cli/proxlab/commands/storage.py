import typer
from rich.console import Console
from rich.table import Table
from rich import box
from proxlab.client import api_get, api_post, api_delete

app = typer.Typer(help="Manage NAS storage datasets")
console = Console()


@app.command("list")
def list_storage():
    datasets = api_get("/api/storage")
    if not datasets:
        console.print("[dim]No proxlab storage datasets.[/dim]")
        return
    table = Table(box=box.ROUNDED, header_style="bold cyan")
    table.add_column("Name")
    table.add_column("NFS Path")
    table.add_column("Quota GB", justify="right")
    table.add_column("Used GB", justify="right")
    table.add_column("Free GB", justify="right")
    for d in datasets:
        table.add_row(
            d["name"], d["nfs_path"],
            str(d["quota_gb"]), str(d["used_gb"]), str(d["available_gb"]),
        )
    console.print(table)


@app.command("create")
def create_storage(
    name: str = typer.Argument(...),
    quota: int = typer.Option(50, help="Quota in GB"),
):
    with console.status(f"Creating dataset {name}..."):
        ds = api_post("/api/storage", json={"name": name, "quota_gb": quota})
    console.print(f"[green]✓[/green] Created [bold]{ds['name']}[/bold]")
    console.print(f"  NFS mount: {ds['nfs_server']}:{ds['nfs_path']}")


@app.command("delete")
def delete_storage(name: str, yes: bool = typer.Option(False, "--yes", "-y")):
    if not yes:
        typer.confirm(f"Delete dataset '{name}'?", abort=True)
    api_delete(f"/api/storage/{name}")
    console.print(f"[red]✗[/red] Dataset '{name}' deleted")
