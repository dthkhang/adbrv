"""
APK resigning tools using uber-apk-signer
"""

import os
import subprocess
import sys
from rich.console import Console

console = Console()

def resign_apk(resign_args):
    """
    Resign APK file using integrated uber-apk-signer
    """
    jar_path = os.path.join(os.path.dirname(__file__), 'tools', 'uber-apk-signer-1.3.0.jar')
    if not os.path.isfile(jar_path):
        console.print(f"[bold red]uber-apk-signer jar not found at {jar_path}[/bold red]")
        sys.exit(1)
        
    cmd = ['java', '-jar', jar_path] + resign_args
    try:
        with console.status("[bold green]Resigning APK using uber-apk-signer...[/bold green]", spinner="dots"):
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode != 0:
                console.print(f"[bold red]Error running uber-apk-signer:\\n{result.stderr}[/bold red]")
                sys.exit(result.returncode)
            
        console.print("[bold green]✔ APK Resigning Complete![/bold green]")
        # Output result so user can read stdout if needed
        console.print(result.stdout)
            
    except Exception as e:
        console.print(f"[bold red]Error running uber-apk-signer: {e}[/bold red]")
        sys.exit(1)
