from __future__ import annotations
import time
import subprocess
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table
from rich import box

from proxlab.client import api_get, api_post, api_delete

app = typer.Typer(help="Manage servers (VMs)")
console = Console()

STATUS_STYLE = {
    "running": "[green]running[/green]",
    "stopped": "[dim]stopped[/dim]",
    "pending": "[yellow]pending[/yellow]",
    "error": "[red]error[/red]",
}


@app.command("list")
def list_vms():
    """List all proxlab-managed servers."""
    servers = api_get("/api/servers")
    if not servers:
        console.print("[dim]No servers found.[/dim]")
        return
    table = Table(box=box.ROUNDED, show_header=True, header_style="bold cyan")
    table.add_column("ID", style="dim", width=6)
    table.add_column("Name", min_width=16)
    table.add_column("Status", min_width=10)
    table.add_column("IP", min_width=14)
    table.add_column("Flavor", min_width=8)
    table.add_column("Cores", justify="right", width=6)
    table.add_column("RAM (MB)", justify="right", width=9)
    for s in servers:
        table.add_row(
            str(s["id"]),
            s["name"],
            STATUS_STYLE.get(s["status"], s["status"]),
            s.get("ip") or "[dim]—[/dim]",
            s.get("flavor", "—"),
            str(s.get("cores", "—")),
            str(s.get("memory_mb", "—")),
        )
    console.print(table)


@app.command("create")
def create_vm(
    name: str = typer.Argument(..., help="Server hostname"),
    flavor: str = typer.Option("small", help="Flavor: micro/small/medium/large/xlarge/custom"),
    template: str = typer.Option("base", help="Template: base/dev"),
    cores: Optional[int] = typer.Option(None, help="CPU cores (for flavor=custom)"),
    ram: Optional[int] = typer.Option(None, "--ram", help="RAM in GB (for flavor=custom)"),
    disk: Optional[int] = typer.Option(None, help="Disk in GB (for flavor=custom)"),
    storage: Optional[str] = typer.Option(None, help="Allocate NAS storage with this name"),
    storage_quota: int = typer.Option(50, help="NAS quota in GB"),
    db: Optional[str] = typer.Option(None, help="Provision a Postgres database"),
    ssh_key: Optional[str] = typer.Option(None, help="SSH public key to inject"),
):
    """Provision a new server on beast."""
    payload: dict = {
        "name": name,
        "flavor": flavor,
        "template": template,
    }
    if cores:
        payload["cores"] = cores
    if ram:
        payload["memory_mb"] = ram * 1024
    if disk:
        payload["disk_gb"] = disk
    if storage:
        payload["storage_name"] = storage
        payload["storage_quota_gb"] = storage_quota
    if db:
        payload["database_name"] = db
    if ssh_key:
        payload["ssh_keys"] = [ssh_key]

    with console.status(f"[cyan]Provisioning {name}...[/cyan]"):
        task = api_post("/api/servers", json=payload)

    task_id = task["id"]
    console.print(f"[dim]Task ID:[/dim] {task_id}")

    # Poll until done
    with console.status("[cyan]Waiting for VM to start...[/cyan]"):
        while True:
            t = api_get(f"/api/tasks/{task_id}")
            if t["status"] == "ok":
                console.print(f"[green]✓[/green] Server [bold]{name}[/bold] is ready!")
                if t.get("vmid"):
                    console.print(f"  VMID: {t['vmid']}")
                break
            elif t["status"] == "error":
                console.print(f"[red]✗ Failed:[/red] {t.get('error', 'unknown error')}")
                raise typer.Exit(1)
            time.sleep(3)


@app.command("start")
def start_vm(vmid: int = typer.Argument(...)):
    """Start a stopped server."""
    with console.status(f"Starting {vmid}..."):
        api_post(f"/api/servers/{vmid}/action", json={"action": "os-start"})
    console.print(f"[green]✓[/green] Start requested for VMID {vmid}")


@app.command("stop")
def stop_vm(vmid: int = typer.Argument(...)):
    """Gracefully stop a running server."""
    with console.status(f"Stopping {vmid}..."):
        api_post(f"/api/servers/{vmid}/action", json={"action": "os-stop"})
    console.print(f"[yellow]⏹[/yellow] Stop requested for VMID {vmid}")


@app.command("destroy")
def destroy_vm(
    vmid: int = typer.Argument(...),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation"),
):
    """Permanently destroy a server."""
    if not yes:
        typer.confirm(f"Destroy VMID {vmid}? This cannot be undone.", abort=True)
    with console.status(f"[red]Destroying {vmid}...[/red]"):
        api_delete(f"/api/servers/{vmid}")
    console.print(f"[red]✗[/red] VMID {vmid} destroyed")


@app.command("ssh")
def ssh_vm(vmid: int = typer.Argument(...), user: str = typer.Option("ubuntu", help="SSH username")):
    """Open an SSH session to a running server (looks up IP from guest agent)."""
    server = api_get(f"/api/servers/{vmid}")
    ip = server.get("ip")
    if not ip:
        console.print(f"[red]No IP found for VMID {vmid}. Is it running?[/red]")
        raise typer.Exit(1)
    console.print(f"[dim]Connecting to {user}@{ip}...[/dim]")
    subprocess.run(["ssh", f"{user}@{ip}"])
