import subprocess, sys

class AdbError(Exception):
    pass

def get_connected_devices():
    try:
        result = subprocess.run(["adb", "devices"], capture_output=True, text=True)
        lines = result.stdout.strip().splitlines()[1:]  # skip first line
        devices = [line.split()[0] for line in lines if '\tdevice' in line]
        return devices
    except Exception as e:
        raise AdbError(f"Error running adb: {e}")

def select_device(serial_arg=None):
    devices = get_connected_devices()
    if not devices:
        raise AdbError("No devices connected.")
    
    if serial_arg:
        if serial_arg not in devices:
            raise AdbError(f"Device {serial_arg} not found.")
        return serial_arg
        
    if len(devices) == 1:
        return devices[0]
        
    import questionary
    from rich.console import Console
    Console().print("[bold yellow][!] Multiple devices connected.[/bold yellow]")
    selected = questionary.select(
        "Select a device to use:",
        choices=devices,
        instruction="(Use arrow keys)"
    ).ask()
    
    if not selected:
        raise AdbError("No device selected.")
        
    return selected

def get_proxy_status(serial=None):
    adb_base = ["adb"]
    if serial:
        adb_base += ["-s", serial]
    try:
        result = subprocess.run(adb_base + ["shell", "settings", "get", "global", "http_proxy"], capture_output=True, text=True, check=True)
        return result.stdout.strip()
    except subprocess.CalledProcessError:
        raise AdbError("Device disconnected or cannot get proxy status.")

def get_reverse_ports(serial=None):
    adb_base = ["adb"]
    if serial:
        adb_base += ["-s", serial]
    try:
        result = subprocess.run(adb_base + ["reverse", "--list"], capture_output=True, text=True, check=True)
        result_cut = result.stdout.split()[-2:]
        return ' '.join(result_cut) if result_cut else "(none)"
    except subprocess.CalledProcessError:
        raise AdbError("Device disconnected or cannot get reverse ports.")

def print_all_status(serial=None):
    if serial:
        devices = [serial]
    else:
        devices = get_connected_devices()
    if not devices:
        print("[!] No devices connected.")
        return
    for serial in devices:
        proxy = get_proxy_status(serial)
        reverse = get_reverse_ports(serial)
        print(f"Device {serial}:")
        print(f"  Proxy:   {proxy}")
        print(f"  Reverse: {reverse}")

def check_devices_info(serial=None, show_title=True):
    from rich.console import Console
    from rich.table import Table
    from rich import box
    console = Console()
    
    import re
    def adb_shell(cmd, serial=None):
        adb_base = ["adb"]
        if serial:
            adb_base += ["-s", serial]
        try:
            result = subprocess.run(adb_base + ["shell"] + cmd, capture_output=True, text=True, check=True)
            return result.stdout.strip()
        except subprocess.CalledProcessError:
            return None

    if serial:
        devices = [serial]
    else:
        devices = get_connected_devices()
    if not devices:
        console.print("[bold red][!] No devices connected.[/bold red]")
        return
        
    title_text = "Connected Devices Status" if show_title else None
    table = Table(title=title_text, box=box.ROUNDED)
    table.add_column("Device Serial", style="cyan", no_wrap=True)
    table.add_column("Model", style="magenta")
    table.add_column("Android", justify="center")
    table.add_column("Root Access", justify="center")
    table.add_column("Frida", justify="center")
    table.add_column("Proxy", style="yellow")
    table.add_column("Reverse", style="green")

    for s in devices:
        adb_base = ["adb", "-s", s] if s else ["adb"]
        try:
            res = subprocess.run(adb_base + ["shell", "getprop ro.product.model; getprop ro.build.version.release; which su"], capture_output=True, text=True, timeout=5)
            lines = res.stdout.strip().splitlines()
        except:
            lines = []
            
        model = lines[0] if len(lines) > 0 and lines[0].strip() else "?"
        android = lines[1] if len(lines) > 1 and lines[1].strip() else "?"
        su_check = lines[2] if len(lines) > 2 else ""
        
        root = "Yes" if su_check and su_check.strip() else "No"
        root_style = "[bold green]Yes[/bold green]" if root == "Yes" else "[bold red]No[/bold red]"
        
        from .fridaTools import get_frida_status
        frida_status = get_frida_status(s)
        if "On" in frida_status:
            frida_style = f"[bold green]{frida_status}[/bold green]"
        else:
            frida_style = f"[dim]{frida_status}[/dim]"
            
        proxy = get_proxy_status(s)
        reverse = get_reverse_ports(s)
        
        table.add_row(
            s,
            model,
            android,
            root_style,
            frida_style,
            proxy,
            reverse
        )
        
    console.print(table)

def adb_shell(cmd, serial=None, check=True, input_text=None):
    adb_base = ["adb"]
    if serial:
        adb_base += ["-s", serial]
    try:
        result = subprocess.run(adb_base + ["shell"] + cmd, capture_output=True, text=True, check=check, input=input_text)
        return result.stdout.strip()
    except subprocess.CalledProcessError:
        return None



def get_device_info(serial):
    adb_base = ["adb"]
    if serial:
        adb_base += ["-s", serial]
    try:
        res = subprocess.run(adb_base + ["shell", "getprop ro.product.model; getprop ro.build.version.release; which su"], capture_output=True, text=True, timeout=5)
        lines = res.stdout.strip().splitlines()
    except:
        lines = []

    model = lines[0] if len(lines) > 0 and lines[0].strip() else "?"
    android = lines[1] if len(lines) > 1 and lines[1].strip() else "?"
    su_check = lines[2] if len(lines) > 2 else ""
    
    root = "Yes" if su_check and su_check.strip() else "No"
    from .fridaTools import get_frida_status
    frida_status = get_frida_status(serial)
    proxy = get_proxy_status(serial)
    reverse = get_reverse_ports(serial)
    return {
        "serial": serial,
        "model": model,
        "android": android,
        "root": root,
        "frida_status": frida_status,
        "proxy": proxy,
        "reverse": reverse,
    }