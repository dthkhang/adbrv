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

def check_devices_info(serial=None):
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
        
    table = Table(title="Connected Devices Status", box=box.ROUNDED)
    table.add_column("Device Serial", style="cyan", no_wrap=True)
    table.add_column("Model", style="magenta")
    table.add_column("Android", justify="center")
    table.add_column("Root Access", justify="center")
    table.add_column("Frida", justify="center")
    table.add_column("Proxy", style="yellow")
    table.add_column("Reverse", style="green")

    for s in devices:
        model = adb_shell(["getprop", "ro.product.model"], s) or "?"
        android = adb_shell(["getprop", "ro.build.version.release"], s) or "?"
        su_check = adb_shell(["which", "su"], s)
        root = "Yes" if su_check and su_check != '' else "No"
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
    def adb_shell(cmd, serial=None):
        adb_base = ["adb"]
        if serial:
            adb_base += ["-s", serial]
        try:
            result = subprocess.run(adb_base + ["shell"] + cmd, capture_output=True, text=True, check=True)
            return result.stdout.strip()
        except subprocess.CalledProcessError:
            return None
    model = adb_shell(["getprop", "ro.product.model"], serial) or "?"
    android = adb_shell(["getprop", "ro.build.version.release"], serial) or "?"
    su_check = adb_shell(["which", "su"], serial)
    root = "Yes" if su_check and su_check != '' else "No"
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