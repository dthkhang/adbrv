import sys
import subprocess
from rich.console import Console

console = Console()

class CoreError(Exception):
    pass

def update_script():
    console.print("[bold cyan][*] Checking for updates from GitHub...[/bold cyan]")
    try:
        args = [
            sys.executable, "-m", "pip", "install", "--upgrade", 
            "--break-system-packages", "git+https://github.com/dthkhang/adbrv.git"
        ]
        
        with console.status("[bold yellow]Auto-updating via pip (this may take a few seconds)...[/bold yellow]", spinner="dots"):
            result = subprocess.run(
                args,
                capture_output=True,
                text=True
            )

        if result.returncode == 0:
            console.print("[bold green][:heavy_check_mark:] Update successful! The tool is now up-to-date.[/bold green]")
            console.print("[bold magenta][!] Please re-run the script to use the new version.[/bold magenta]")
        else:
            console.print(f"[bold red][:x:] Update failed. Exit code: {result.returncode}[/bold red]")
            if result.stderr:
                console.print(f"[red]{result.stderr}[/red]")
            console.print("[bold yellow]You can try manually:[/bold yellow] pip install --upgrade --break-system-packages git+https://github.com/dthkhang/adbrv.git")

    except Exception as e:
        raise CoreError(f"Unexpected error during update: {e}")