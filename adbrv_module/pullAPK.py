import os
import shutil
import subprocess
from rich.console import Console
from rich import print as rprint
from rich.panel import Panel
from rich.table import Table
from rich import box
from .devices import select_device, get_connected_devices

console = Console()

def get_installed_packages(device=None):
    cmd = ["adb"]
    if device is None:
        devices = get_connected_devices()
        if devices:
            device = devices[0]
            
    if device:
        cmd.extend(["-s", device])
    cmd.extend(["shell", "pm", "list", "packages"])
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
        if result.returncode != 0:
            return []
        packages = []
        for line in result.stdout.splitlines():
            line = line.strip()
            if line.startswith("package:"):
                pkg = line.split(":", 1)[1]
                packages.append(pkg)
        return packages
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
        return []

def print_result_panel(package_name, final_dest, apk_type):
    table = Table(box=None, show_header=False, pad_edge=True, padding=(0, 2))
    table.add_column("Key", style="bold cyan")
    table.add_column("Value")
    
    table.add_row("📦 Package", package_name)
    table.add_row("📁 Saved @", final_dest)
    table.add_row("📄 Type", apk_type)
    
    panel = Panel(
        table,
        title="[bold green]✅ Pull Completed Successfully![/bold green]",
        title_align="left",
        border_style="green",
        box=box.ROUNDED
    )
    console.print(panel)


def pull_apk(package_name: str, dest_path: str = None, device: str = None):
    target_device = select_device(device)
    if not target_device:
        console.print("[bold red]❌ No devices connected for pull operation.[/bold red]")
        return
    
    if dest_path is None:
        dest_path = os.getcwd()

    dest_path = os.path.abspath(dest_path)

    with console.status(f"[cyan]🔍 Locating package '{package_name}' on device...[/cyan]", spinner="dots") as status:
        # get paths
        cmd = ["adb", "-s", target_device, "shell", "pm", "path", package_name]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        except subprocess.CalledProcessError:
            status.stop()
            console.print(f"[bold red]❌ Could not find package {package_name} on device {target_device}.[/bold red]")
            return
            
        paths = []
        for line in result.stdout.splitlines():
            line = line.strip()
            if line.startswith("package:"):
                paths.append(line.split(":", 1)[1])
                
        if not paths:
            status.stop()
            console.print(f"[bold red]❌ Package {package_name} not found or has no APK paths.[/bold red]")
            return
            
        if len(paths) == 1:
            # Single APK
            apk_path = paths[0]
            filename = os.path.basename(apk_path)
            final_dest = os.path.join(dest_path, filename)
            status.update(f"[cyan]📦 Package found & Pulling (Single APK)...[/cyan]")
            try:
                pull_cmd = ["adb", "-s", target_device, "pull", apk_path, final_dest]
                subprocess.run(pull_cmd, check=True, capture_output=True, text=True)
                status.stop()
                print_result_panel(package_name, final_dest, "Single APK")
            except subprocess.CalledProcessError:
                fallback_pull(target_device, [apk_path], dest_path, False, package_name, status)
        else:
            # Split APK
            final_dest_dir = os.path.join(dest_path, f"{package_name}_apks")
            os.makedirs(final_dest_dir, exist_ok=True)
            status.update(f"[cyan]📦 Package found & Pulling (Split APKs - {len(paths)} files)...[/cyan]")
            
            try:
                for apk_path in paths:
                    filename = os.path.basename(apk_path)
                    dest_file = os.path.join(final_dest_dir, filename)
                    pull_cmd = ["adb", "-s", target_device, "pull", apk_path, dest_file]
                    subprocess.run(pull_cmd, check=True, capture_output=True, text=True)
                status.stop()
                print_result_panel(package_name, final_dest_dir, f"Split APKs ({len(paths)} files)")
            except subprocess.CalledProcessError:
                fallback_pull(target_device, paths, dest_path, True, package_name, status)

def fallback_pull(target_device, paths, dest_path, is_split, pkg_name, status):
    status.update("[yellow]⚠️ Permission denied! Triển khai fallback qua quyền Root...[/yellow]")
    
    if is_split:
        final_dest_dir = os.path.join(dest_path, f"{pkg_name}_apks")
        os.makedirs(final_dest_dir, exist_ok=True)
        success_count = 0
        for apk_path in paths:
            filename = os.path.basename(apk_path)
            tmp_path = f"/data/local/tmp/adbrv_pull_{filename}"
            cp_cmd = ["adb", "-s", target_device, "shell", "su", "-c", f"cp {apk_path} {tmp_path} && chmod 666 {tmp_path}"]
            subprocess.run(cp_cmd, capture_output=True)
            
            pull_cmd = ["adb", "-s", target_device, "pull", tmp_path, os.path.join(final_dest_dir, filename)]
            try:
                subprocess.run(pull_cmd, check=True, capture_output=True)
                success_count += 1
            except subprocess.CalledProcessError:
                pass
                
            # Cleanup
            rm_cmd = ["adb", "-s", target_device, "shell", "su", "-c", f"rm {tmp_path}"]
            subprocess.run(rm_cmd, capture_output=True)
             
        status.stop()
        if success_count > 0:
            print_result_panel(pkg_name, final_dest_dir, f"Split APKs ({success_count}/{len(paths)} files - Fallback Root)")
        else:
            console.print(f"[bold red]❌ Failed to pull even with root fallback.[/bold red]")
    else:
        apk_path = paths[0]
        filename = os.path.basename(apk_path)
        tmp_path = f"/data/local/tmp/adbrv_pull_{filename}"
        cp_cmd = ["adb", "-s", target_device, "shell", "su", "-c", f"cp {apk_path} {tmp_path} && chmod 666 {tmp_path}"]
        subprocess.run(cp_cmd, capture_output=True)
        
        final_dest = os.path.join(dest_path, filename)
        pull_cmd = ["adb", "-s", target_device, "pull", tmp_path, final_dest]
        try:
            subprocess.run(pull_cmd, check=True, capture_output=True)
            status.stop()
            print_result_panel(pkg_name, final_dest, "Single APK (Fallback Root)")
        except subprocess.CalledProcessError:
            status.stop()
            console.print(f"[bold red]❌ Failed to pull even with root fallback.[/bold red]")
            
        rm_cmd = ["adb", "-s", target_device, "shell", "su", "-c", f"rm {tmp_path}"]
        subprocess.run(rm_cmd, capture_output=True)
