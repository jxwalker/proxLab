import typer
from proxlab.commands import vm, storage, db, config as cfg_cmd

app = typer.Typer(
    name="proxlab",
    help="proxlab — VM orchestration CLI for beast/TrueNAS/Postgres",
    no_args_is_help=True,
)

app.add_typer(vm.app, name="vm")
app.add_typer(storage.app, name="storage")
app.add_typer(db.app, name="db")
app.add_typer(cfg_cmd.app, name="config")

if __name__ == "__main__":
    app()
