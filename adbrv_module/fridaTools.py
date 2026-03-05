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
    
    fs = "/data/local/tmp/*rida-server*"
    
    try:
        # Check if frida-server exists
        result = subprocess.run(adb_base + ["shell", "ls", fs], capture_output=True, text=True)
        
        if result.returncode != 0:
            print_error("Frida/Florida Server Not Found!!")
            print_warning("Please check the server filename in /data/local/tmp. It must contain 'frida-server' or 'florida-server'.")
            return False
            
        # Get server filename
        frida_files = result.stdout.strip().splitlines()
        if not frida_files:
            print_error("No Frida/Florida server files found!")
            print_warning("Please check the server filename in /data/local/tmp. It must contain 'frida-server' or 'florida-server'.")
            return False
            
        if len(frida_files) == 1:
            fsName = frida_files[0]
            print_info(f"Found Server: {fsName}")
        else:
            import questionary
            fsName = questionary.select(
                "Select which server to start:",
                choices=frida_files,
                instruction="(Use arrow keys)"
            ).ask()
            
            if not fsName:  # User cancelled
                return False
                
            print_info(f"Selected Server: {fsName}")

        # Check if already running
        ps_result = subprocess.run(adb_base + ["shell", "ps | grep rida-server"], 
                                 capture_output=True, text=True)

        if "rida-server" in ps_result.stdout:
            print_warning("Frida/Florida Server Is Running")
            return True

        # Start frida-server
        from rich.console import Console
        console = Console()
        with console.status(f"[bold green]Starting {fsName} in background...[/bold green]", spinner="bouncingBar"):
            # Set executable permission
            subprocess.run(adb_base + ["shell", "chmod", "+x", fsName], check=True)

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
                console.print(f"[bold green]✔ Server Start Success!! ({fsName})[/bold green]")
                return True
            else:
                console.print("[bold red]✖ Server Start Failed!! Check & Try Again[/bold red]")
                return False
            
    except subprocess.CalledProcessError as e:
        print_error(f"Error: {e}")
        return False
    except Exception as e:
        print_error(f"Unexpected error: {e}")
        return False

def frida_kill(serial=None):
    """Kill all running frida/florida server processes on the device"""
    from .devices import select_device
    serial = select_device(serial)
            
    # List server processes
    ps_out = adb_shell(["ps", "|", "grep", "rida-server"], serial)
    if not ps_out or "rida-server" not in ps_out:
        print_info("No frida/florida server process running.")
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
        print_info("No frida/florida server process running.")
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
            print_info("Abort killing server processes.")
            return
            
    for pid, _ in procs:
        # Use correct shell quoting for Android su
        adb_base = ["adb"]
        if serial:
            adb_base += ["-s", serial]
        kill_cmd = f"su -c 'kill -9 {pid}'"
        try:
            subprocess.run(adb_base + ["shell", kill_cmd], check=True)
            print_success(f"Killed frida-server process PID {pid} on device {serial}.")
        except Exception as e:
            print_error(f"Failed to kill PID {pid}: {e}")
            
    print_info("Checking frida-server status...")
    from .devices import check_devices_info
    check_devices_info(serial, show_title=False)

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
