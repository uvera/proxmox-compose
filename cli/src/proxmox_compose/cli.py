import typer
from typer import Typer

from proxmox_compose.commands.apply import apply_command
from proxmox_compose.commands.doctor import doctor_command
from proxmox_compose.commands.init import init_command
from proxmox_compose.commands.inventory import inventory_app
from proxmox_compose.commands.logs import logs_command
from proxmox_compose.commands.plan import plan_command
from proxmox_compose.commands.provision_existing import provision_existing_command
from proxmox_compose.commands.scaffold import scaffold_app
from proxmox_compose.commands.vault import vault_app

app = Typer(
    name="proxmox-compose",
    no_args_is_help=True,
    help="Provision and configure Proxmox infrastructure with Terraform + Ansible.",
)

app.command("init")(init_command)
app.command("plan")(plan_command)
app.command("apply")(apply_command)
app.command("provision-existing")(provision_existing_command)
app.command("doctor")(doctor_command)
app.command("logs")(logs_command)

try:
    from proxmox_compose.commands.logs_tui import logs_tui_command

    app.command("logs-tui")(logs_tui_command)
except ModuleNotFoundError:

    def logs_tui_command() -> None:  # type: ignore[no-redef]
        typer.secho(
            "The logs TUI requires the optional 'textual' dependency.",
            fg=typer.colors.RED,
            err=True,
        )
        raise typer.Exit(code=1)

    app.command("logs-tui")(logs_tui_command)
app.add_typer(inventory_app, name="inventory")
app.add_typer(scaffold_app, name="scaffold")
app.add_typer(vault_app, name="vault")
