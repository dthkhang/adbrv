"""
Frida server management tools for Android devices
"""

import subprocess
import time
from .devices import get_connected_devices, adb_shell, AdbError
from .utils import print_success, print_error, print_info, print_warning

def start_frida_server(serial=None):
    """Start frida-server on Android device"""
    from .devices import select_device
    serial = select_device(serial)
    
    adb_base = ["adb"]
    if serial:
        adb_base += ["-s", serial]
    from rich.console import Console
    console = Console()
    
    fs = "/data/local/tmp/*rida-server*"
    
    try:
        # Check if frida-server exists
        result = subprocess.run(adb_base + ["shell", "ls", fs], capture_output=True, text=True)
        
        if result.returncode != 0:
            console.print("  [bold red][!] Frida/Florida Server Not Found!![/bold red]")
            console.print("  [yellow][!] Please check the server filename in /data/local/tmp.[/yellow]")
            return False
            
        # Get server filename
        frida_files = result.stdout.strip().splitlines()
        if not frida_files:
            console.print("  [bold red][!] No Frida/Florida server files found![/bold red]")
            console.print("  [yellow][!] Please check the server filename in /data/local/tmp.[/yellow]")
            return False
            
        if len(frida_files) == 1:
            fsName = frida_files[0]
            console.print(f"  [cyan][i] Found: {fsName}[/cyan]")
        else:
            import questionary
            fsName = questionary.select(
                "Select which server to start:",
                choices=frida_files,
                instruction="(Use arrow keys)"
            ).ask()
            
            if not fsName:  # User cancelled
                return False
                
            console.print(f"  [cyan][i] Selected: {fsName}[/cyan]")

        # Check if already running
        ps_result = subprocess.run(adb_base + ["shell", "ps | grep rida-server"], 
                                 capture_output=True, text=True)

        if "rida-server" in ps_result.stdout:
            console.print("  [bold yellow][!] Frida/Florida Server Is Already Running[/bold yellow]")
            return True

        # Start frida-server
        with console.status("  [cyan]Starting server...[/cyan]", spinner="bouncingBar"):
            # Set executable permission
            # Try su first (for root-owned files), fallback to shell, then proceed anyway
            import shlex
            safe_name = shlex.quote(fsName)
            su_chmod = subprocess.run(adb_base + ["shell", "su", "-c", f"chmod +x {safe_name}"], capture_output=True)
            if su_chmod.returncode != 0:
                plain_chmod = subprocess.run(adb_base + ["shell", "chmod", "+x", fsName], capture_output=True)
                if plain_chmod.returncode != 0:
                    print_warning(f"chmod failed for {fsName}, file may already have execute permission — proceeding anyway.")

            # Start with root privileges (run in background)
            try:
                subprocess.run(adb_base + ["shell", "su", "-c", f"{fsName} &"], check=True, timeout=10)
            except subprocess.TimeoutExpired:
                # Timeout is expected when starting background process
                pass

            time.sleep(2)

            # Verify start
            verify_result = subprocess.run(adb_base + ["shell", "ps | grep rida-server"], 
                                         capture_output=True, text=True)
            
            if "rida-server" in verify_result.stdout:
                console.print(f"  [bold green]✔[/bold green] Server     [cyan]{fsName}[/cyan]")
                return True
            else:
                console.print("  [bold red]✖ Server Start Failed!! Check & Try Again[/bold red]")
                return False
            
    except subprocess.CalledProcessError as e:
        console.print(f"  [bold red][!] Error: {e}[/bold red]")
        return False
    except Exception as e:
        console.print(f"  [bold red][!] Unexpected error: {e}[/bold red]")
        return False

def frida_kill(serial=None):
    """Kill all running frida/florida server processes on the device"""
    from .devices import select_device
    serial = select_device(serial)
            
    # List server processes
    ps_out = adb_shell(["ps", "|", "grep", "rida-server"], serial)
    if not ps_out or "rida-server" not in ps_out:
        from rich.console import Console
        Console().print("  [dim][i] No frida/florida server process running.[/dim]")
        return
        
    # Parse PIDs
    procs = []
    for line in ps_out.splitlines():
        if "rida-server" in line:
            parts = line.split()
            pid = None
            for p in parts[1:]:
                if p.isdigit():
                    pid = p
                    break
            if pid:
                procs.append((pid, line))
                
    if not procs:
        from rich.console import Console
        Console().print("  [dim][i] No frida/florida server process running.[/dim]")
        return
        
    if len(procs) > 1:
        print("Multiple server processes found:")
        for pid, line in procs:
            print(f"  PID {pid}: {line}")
        import questionary
        confirm = questionary.confirm(
            "Do you want to kill all server processes?"
        ).ask()
        if not confirm:
            from rich.console import Console
            Console().print("  [dim][i] Abort killing server processes.[/dim]")
            return
            
    for pid, _ in procs:
        # Use correct shell quoting for Android su
        adb_base = ["adb"]
        if serial:
            adb_base += ["-s", serial]
        kill_cmd = f"su -c 'kill -9 {pid}'"
        try:
            subprocess.run(adb_base + ["shell", kill_cmd], check=True)
            from rich.console import Console
            Console().print(f"  [bold green]✔[/bold green] Killed    [cyan]PID {pid} on {serial}[/cyan]")
        except Exception as e:
            from rich.console import Console
            Console().print(f"  [bold red]✖[/bold red] Failed to kill PID {pid}: {e}")
            
    from rich.console import Console
    _console = Console()
    with _console.status("  [dim]Verifying...[/dim]", spinner="dots"):
        frida_status = get_frida_status(serial)
    if "On" in frida_status:
        _console.print(f"  [bold yellow]⚠[/bold yellow] Server still running: [cyan]{frida_status}[/cyan]")
    else:
        _console.print(f"  [bold green]✔[/bold green] Frida     [cyan]stopped[/cyan]")

def get_frida_status(serial):
    """Get frida/florida server status for a device"""
    frida_ps = adb_shell(["ps", "|", "grep", "rida-server"], serial)
    if frida_ps and "rida-server" in frida_ps:
        try:
            pid = None
            user = "shell"
            for line in frida_ps.splitlines():
                if "rida-server" in line:
                    parts = line.split()
                    # First column is usually USER
                    if len(parts) > 0:
                        user = parts[0]
                    for p in parts[1:]:
                        if p.isdigit():
                            pid = p
                            break
                    if pid:
                        break
            return f"On ({user} - PID: {pid})" if pid else f"On ({user})"
        except Exception:
            return "On"
    else:
        return "Off"
