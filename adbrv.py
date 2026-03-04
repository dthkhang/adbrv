#!/usr/bin/env python3
__version__ = "2.0.0"
import sys
import typer
from typing import Optional, List
from typing_extensions import Annotated
from rich.console import Console
from rich import print as rprint

from adbrv_module.proxy import set_proxy, unset_proxy_and_reverse, ProxyError
from adbrv_module.devices import get_connected_devices, check_devices_info, AdbError
from adbrv_module.fridaTools import frida_kill, start_frida_server
from adbrv_module.checkSymbols import check_symbols
from adbrv_module.resignAPK import resign_apk
from adbrv_module.findSOfile import find_so_files
from adbrv_module.libSecurity import check_lib_security
from adbrv_module.core import update_script, CoreError

from typer.rich_utils import _get_rich_console
from rich.panel import Panel
import typer.rich_utils

typer.rich_utils.STYLE_OPTIONS_TABLE_PAD_EDGE = True
typer.rich_utils.STYLE_COMMANDS_TABLE_PAD_EDGE = True
typer.rich_utils.STYLE_OPTIONS_TABLE_PADDING = (0, 3)
typer.rich_utils.STYLE_COMMANDS_TABLE_PADDING = (0, 3)

original_rich_format_help = typer.rich_utils.rich_format_help
def custom_rich_format_help(
    *,
    obj,
    ctx,
    markup_mode,
):
    epilog = obj.epilog
    obj.epilog = None
    original_rich_format_help(obj=obj, ctx=ctx, markup_mode=markup_mode)
    obj.epilog = epilog
    if epilog:
        console = _get_rich_console()
        from rich.table import Table
        from rich.text import Text
        
        example_table = Table(show_header=False, box=None, padding=(0, 3), pad_edge=True)
        example_table.add_column(style="cyan", no_wrap=True)
        example_table.add_column()

        
        # Parse the raw epilog string to build rows
        # Format expected: odd lines are commands, even lines are descriptions
        lines = [line.strip() for line in epilog.strip().split('\n') if line.strip()]
        for i in range(0, len(lines), 2):
            if i + 1 < len(lines):
                cmd = lines[i].replace('[cyan]', '').replace('[/cyan]', '')
                desc = lines[i+1]
                example_table.add_row(f"{cmd}", desc)
                
        console.print(
            Panel(
                example_table,
                border_style="dim",
                title="Examples",
                title_align="left",
            )
        )

typer.rich_utils.rich_format_help = custom_rich_format_help

app = typer.Typer(
    name="adbrv",
    help="ADB reverse port forwarding, HTTP proxy configuration, APK analysis tools, and security assessment for Android devices.",
    epilog="""
adbrv status
Show proxy, reverse port, and frida-server status.

adbrv status -d 1234
Show status for specific device.

adbrv set 8080 8080
Set up reverse proxy & HTTP proxy.

adbrv unset
Remove proxy and all reverse ports.

adbrv frida-start
Start frida-server (prompts auto-selection).

adbrv resign --apk target.apk
Resign APK file using integrated uber-apk-signer.

adbrv checksym base_dir
Check symbols in decompiled APK folder.

adbrv findso
Search for .so files across all APKs in current folder.

adbrv libsec
Run MASTG security checks on .so files.
""",
    add_completion=False,
    rich_markup_mode="rich"
)
console = Console()

def version_callback(value: bool):
    if value:
        console.print(f"[bold green]adbrv version[/bold green] [cyan]{__version__}[/cyan]")
        raise typer.Exit()

@app.callback()
def main_callback(
    version: Annotated[
        Optional[bool],
        typer.Option(
            "--version",
            "-v",
            callback=version_callback,
            is_eager=True,
            help="Show the application's version and exit.",
        ),
    ] = None,
):
    pass

@app.command(name="set")
def cmd_set(
    local_port: Annotated[int, typer.Argument(help="Local port to route traffic to (integer)")],
    device_port: Annotated[int, typer.Argument(help="Device port to map (integer)")],
    device: Annotated[Optional[str], typer.Option("--device", "-d", help="Specific device serial")] = None,
):
    """Set up ADB reverse proxy and HTTP proxy."""
    try:
        if not (1 <= local_port <= 65535) or not (1 <= device_port <= 65535):
            console.print("[bold red][!] Invalid port. Port must be an integer between 1 and 65535.[/bold red]")
            raise typer.Exit(1)
            
        devices = get_connected_devices()
        if not devices:
            console.print("[bold red][!] No devices connected.[/bold red]")
            raise typer.Exit(1)
        if device:
            if device not in devices:
                console.print(f"[bold red][!] Device {device} not found.[/bold red]")
                raise typer.Exit(1)
            set_proxy(local_port, device_port, device)
        else:
            if len(devices) > 1:
                console.print("[bold red][!] Multiple devices connected. Please specify --device <serial>.[/bold red]")
                raise typer.Exit(1)
            set_proxy(local_port, device_port, devices[0])
    except (AdbError, ProxyError, CoreError) as e:
        console.print(f"[bold red][!] {e}[/bold red]")
        raise typer.Exit(1)

@app.command(name="unset")
def cmd_unset(
    device: Annotated[Optional[str], typer.Option("--device", "-d", help="Specific device serial")] = None,
):
    """Remove proxy and all reverse ports on the selected (or all) devices."""
    try:
        devices = get_connected_devices()
        if not devices:
            console.print("[bold red][!] No devices connected.[/bold red]")
            raise typer.Exit(1)
        if device:
            if device not in devices:
                console.print(f"[bold red][!] Device {device} not found.[/bold red]")
                raise typer.Exit(1)
            unset_proxy_and_reverse(device)
        else:
            for d in devices:
                unset_proxy_and_reverse(d)
    except (AdbError, ProxyError, CoreError) as e:
        console.print(f"[bold red][!] {e}[/bold red]")
        raise typer.Exit(1)

@app.command(name="status")
def cmd_status(
    device: Annotated[Optional[str], typer.Option("--device", "-d", help="Specific device serial")] = None,
):
    """Display proxy, reverse port, and frida-server status."""
    try:
        devices = get_connected_devices()
        if device:
            if device not in devices:
                console.print(f"[bold red][!] Device {device} not found.[/bold red]")
                raise typer.Exit(1)
            check_devices_info(device)
        else:
            check_devices_info()
    except (AdbError, ProxyError, CoreError) as e:
        console.print(f"[bold red][!] {e}[/bold red]")
        raise typer.Exit(1)

@app.command(name="frida-start")
def cmd_frida_start(
    device: Annotated[Optional[str], typer.Option("--device", "-d", help="Specific device serial")] = None,
):
    """Start frida-server on the device with root privileges."""
    try:
        start_frida_server(device)
    except (AdbError, ProxyError, CoreError) as e:
        console.print(f"[bold red][!] {e}[/bold red]")
        raise typer.Exit(1)

@app.command(name="frida-kill")
def cmd_frida_kill(
    device: Annotated[Optional[str], typer.Option("--device", "-d", help="Specific device serial")] = None,
):
    """Kill all running frida-server processes on the device."""
    try:
        frida_kill(device)
    except (AdbError, ProxyError, CoreError) as e:
        console.print(f"[bold red][!] {e}[/bold red]")
        raise typer.Exit(1)

@app.command(name="update")
def cmd_update():
    """Automatically update the script to the latest version from GitHub."""
    try:
        update_script()
    except (AdbError, ProxyError, CoreError) as e:
        console.print(f"[bold red][!] {e}[/bold red]")
        raise typer.Exit(1)

@app.command(
    name="resign",
    context_settings={"allow_extra_args": True, "ignore_unknown_options": True}
)
def cmd_resign(
    ctx: typer.Context,
    apk: Annotated[str, typer.Option("--apk", help="The APK file to resign")],
):
    """Resign APK file using the integrated uber-apk-signer tool."""
    try:
        # ctx.args provides any additional arguments passed by the user
        resign_args = ['-a', apk] + ctx.args
        resign_apk(resign_args)
    except Exception as e:
        console.print(f"[bold red][!] {e}[/bold red]")
        raise typer.Exit(1)

@app.command(name="checksym")
def cmd_checksym(
    output_folder: Annotated[str, typer.Argument(help="Apktool output folder (e.g. base)")],
):
    """Scan native libraries (.so) in the APK decompiled folder, select ABI, and check symbols."""
    try:
        check_symbols(output_folder)
    except Exception as e:
        console.print(f"[bold red][!] {e}[/bold red]")
        raise typer.Exit(1)

@app.command(name="findso")
def cmd_findso():
    """Find .so files in APK files in current directory."""
    try:
        find_so_files()
    except Exception as e:
        console.print(f"[bold red][!] {e}[/bold red]")
        raise typer.Exit(1)

@app.command(name="libsec")
def cmd_libsec():
    """Check security features of .so files (PIE, Stack Canary, Debug symbols)."""
    try:
        check_lib_security()
    except Exception as e:
        console.print(f"[bold red][!] {e}[/bold red]")
        raise typer.Exit(1)

def main():
    app()

if __name__ == "__main__":
    main()