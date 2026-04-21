import subprocess, sys

class ProxyError(Exception):
    pass

def set_proxy(local_port, device_port, serial=None):
    from rich.console import Console
    console = Console()
    adb_base = ["adb"]
    if serial:
        adb_base += ["-s", serial]
    try:
        with console.status(f"  [dim]Reversing port...[/dim]", spinner="dots"):
            subprocess.run(adb_base + ["reverse", f"tcp:{local_port}", f"tcp:{device_port}"], check=True, capture_output=True)
        console.print(f"  [bold green]✔[/bold green] Reverse    [cyan]tcp:{local_port}[/cyan] → [cyan]tcp:{device_port}[/cyan]")

        with console.status(f"  [dim]Setting proxy...[/dim]", spinner="dots"):
            cmd = f"settings put global http_proxy localhost:{local_port}"
            su_result = subprocess.run(adb_base + ["shell", "su", "-c", cmd], capture_output=True)
            if su_result.returncode != 0:
                subprocess.run(adb_base + ["shell", "settings", "put", "global", "http_proxy", f"localhost:{local_port}"], check=True)
        console.print(f"  [bold green]✔[/bold green] Proxy      [cyan]localhost:{local_port}[/cyan]")

    except subprocess.CalledProcessError as e:
        raise ProxyError(f"Error setting proxy or reverse: {e}")


def unset_proxy_and_reverse(serial=None):
    from rich.console import Console
    console = Console()
    adb_base = ["adb"]
    if serial:
        adb_base += ["-s", serial]
    try:
        with console.status("  [dim]Removing proxy...[/dim]", spinner="dots"):
            cmd = "settings put global http_proxy :0"
            su_result = subprocess.run(adb_base + ["shell", "su", "-c", cmd], capture_output=True)
            if su_result.returncode != 0:
                subprocess.run(adb_base + ["shell", "settings", "put", "global", "http_proxy", ":0"], check=True)
        console.print("  [bold green]✔[/bold green] Proxy      [cyan]cleared[/cyan]")

        with console.status("  [dim]Removing reverse ports...[/dim]", spinner="dots"):
            subprocess.run(adb_base + ["reverse", "--remove-all"], check=True, capture_output=True)
        console.print("  [bold green]✔[/bold green] Reverse    [cyan]all ports removed[/cyan]")

    except subprocess.CalledProcessError as e:
        raise ProxyError(f"Error unsetting proxy or reverse: {e}")