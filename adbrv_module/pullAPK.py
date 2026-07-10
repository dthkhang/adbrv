import os
import shutil
import subprocess
import pty
import re
import select
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich import box
from .devices import select_device, get_connected_devices

console = Console()
percent_pattern = re.compile(r'\[\s*(\d+)%\]')

def get_installed_packages_fast(device=None):
    cmd = ["adb"]
    if device is None:
        devices = get_connected_devices()
        if devices:
            device = devices[0]
            
    if device:
        cmd.extend(["-s", device])
    cmd.extend(["shell", "pm", "list", "packages"])
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=5, stdin=subprocess.DEVNULL)
        if result.returncode != 0:
            return []
            
        packages = []
        for line in result.stdout.splitlines():
            line = line.strip()
            if line.startswith("package:"):
                pkg = line.split(":", 1)[1]
                packages.append({"id": pkg, "name": ""})
        return packages
    except Exception:
        return []

def get_packages_friendly_names(device=None):
    if device is None:
        devices = get_connected_devices()
        if devices:
            device = devices[0]
            
    if not device:
        return {}
        
    frida_cmd = ["frida-ps", "-D", device, "-ia"]
    try:
        frida_res = subprocess.run(frida_cmd, capture_output=True, text=True, timeout=8, stdin=subprocess.DEVNULL)
        if frida_res.returncode == 0:
            name_map = {}
            for line in frida_res.stdout.splitlines():
                parts = line.split()
                if len(parts) >= 3:
                    identifier = parts[-1]
                    name = " ".join(parts[1:-1])
                    name_map[identifier] = name
            return name_map
    except Exception:
        pass
    return {}

def get_installed_packages(device=None):
    # Backward compatibility
    pkgs = get_installed_packages_fast(device)
    names = get_packages_friendly_names(device)
    for p in pkgs:
        if p["id"] in names:
            p["name"] = names[p["id"]]
    pkgs.sort(key=lambda x: not bool(x.get("name")))
    return pkgs

def print_result_panel(package_name, final_dest, apk_type):
    table = Table(box=None, show_header=False, pad_edge=True, padding=(0, 2))
    table.add_column("Key", style="bold cyan")
    table.add_column("Value")
    
    table.add_row("  Package", package_name)
    table.add_row("  Saved @", final_dest)
    table.add_row("  Type", apk_type)
    
    panel = Panel(
        table,
        title="[bold green]✔ Pull Completed Successfully![/bold green]",
        title_align="left",
        border_style="green",
        box=box.ROUNDED
    )
    console.print(panel)

def run_adb_pull_with_progress(target_device, remote_path, local_path, progress, task_id):
    master, slave = pty.openpty()
    pull_cmd = ["adb", "-s", target_device, "pull", remote_path, local_path]
    
    process = subprocess.Popen(
        pull_cmd,
        stdout=slave,
        stderr=slave,
        close_fds=True
    )
    os.close(slave)
    
    last_pct = 0
    buffer = ""
    try:
        while True:
            r, _, _ = select.select([master], [], [], 0.05)
            if master in r:
                try:
                    data = os.read(master, 1024)
                    if not data:
                        break
                    chunk = data.decode('utf-8', errors='replace')
                    buffer += chunk
                    
                    matches = percent_pattern.findall(buffer)
                    if matches:
                        pct = int(matches[-1])
                        if pct > last_pct:
                            progress.update(task_id, advance=pct - last_pct)
                            last_pct = pct
                        buffer = buffer[-100:]
                except OSError:
                    break
            else:
                if process.poll() is not None:
                    break
    finally:
        try:
            os.close(master)
        except:
            pass
            
    process.wait()
    if process.returncode != 0:
        raise subprocess.CalledProcessError(process.returncode, pull_cmd)
        
    if last_pct < 100:
        progress.update(task_id, completed=100)

def fallback_pull_with_progress(target_device, paths, dest_path, is_split, pkg_name):
    console.print("  [yellow][!] Permission denied! Triển khai fallback qua quyền Root...[/yellow]")
    from rich.progress import Progress, TextColumn, BarColumn, TaskProgressColumn, TimeRemainingColumn
    
    if is_split:
        final_dest_dir = os.path.join(dest_path, f"{pkg_name}_apks")
        os.makedirs(final_dest_dir, exist_ok=True)
        success_count = 0
        
        with Progress(
            TextColumn("  [bold cyan]{task.description}"),
            BarColumn(bar_width=40),
            TaskProgressColumn(),
            TimeRemainingColumn(),
            console=console
        ) as progress:
            overall_task = progress.add_task("Fallback Root (Overall)", total=len(paths))
            
            for apk_path in paths:
                filename = os.path.basename(apk_path)
                tmp_path = f"/data/local/tmp/adbrv_pull_{filename}"
                
                cp_cmd = ["adb", "-s", target_device, "shell", "su", "-c", f"cp {apk_path} {tmp_path} && chmod 666 {tmp_path}"]
                subprocess.run(cp_cmd, capture_output=True)
                
                file_task = progress.add_task(f"Pulling {filename}", total=100)
                try:
                    run_adb_pull_with_progress(target_device, tmp_path, os.path.join(final_dest_dir, filename), progress, file_task)
                    success_count += 1
                except subprocess.CalledProcessError:
                    pass
                finally:
                    try:
                        progress.remove_task(file_task)
                    except:
                        pass
                    progress.update(overall_task, advance=1)
                
                rm_cmd = ["adb", "-s", target_device, "shell", "su", "-c", f"rm {tmp_path}"]
                subprocess.run(rm_cmd, capture_output=True)
                
        if success_count > 0:
            print_result_panel(pkg_name, final_dest_dir, f"Split APKs ({success_count}/{len(paths)} files - Fallback Root)")
        else:
            console.print("  [bold red][✖] Failed to pull even with root fallback.[/bold red]")
    else:
        apk_path = paths[0]
        filename = os.path.basename(apk_path)
        tmp_path = f"/data/local/tmp/adbrv_pull_{filename}"
        
        cp_cmd = ["adb", "-s", target_device, "shell", "su", "-c", f"cp {apk_path} {tmp_path} && chmod 666 {tmp_path}"]
        subprocess.run(cp_cmd, capture_output=True)
        
        final_dest = os.path.join(dest_path, filename)
        with Progress(
            TextColumn("  [bold cyan]{task.description}"),
            BarColumn(bar_width=40),
            TaskProgressColumn(),
            TimeRemainingColumn(),
            console=console
        ) as progress:
            task_id = progress.add_task(f"Pulling {filename} (Root)", total=100)
            try:
                run_adb_pull_with_progress(target_device, tmp_path, final_dest, progress, task_id)
                print_result_panel(pkg_name, final_dest, "Single APK (Fallback Root)")
            except subprocess.CalledProcessError:
                console.print("  [bold red][✖] Failed to pull even with root fallback.[/bold red]")
                
        rm_cmd = ["adb", "-s", target_device, "shell", "su", "-c", f"rm {tmp_path}"]
        subprocess.run(rm_cmd, capture_output=True)

def pull_apk(package_name: str, dest_path: str = None, device: str = None):
    target_device = select_device(device)
    if not target_device:
        console.print("[bold red][✖] No devices connected for pull operation.[/bold red]")
        return
    
    if dest_path is None:
        dest_path = os.getcwd()

    dest_path = os.path.abspath(dest_path)

    with console.status(f"[cyan][*] Locating package '{package_name}' on device...[/cyan]", spinner="dots") as status:
        cmd = ["adb", "-s", target_device, "shell", "pm", "path", package_name]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        except subprocess.CalledProcessError:
            status.stop()
            console.print(f"[bold red][✖] Could not find package {package_name} on device {target_device}.[/bold red]")
            return
            
        paths = []
        for line in result.stdout.splitlines():
            line = line.strip()
            if line.startswith("package:"):
                paths.append(line.split(":", 1)[1])
                
        if not paths:
            status.stop()
            console.print(f"[bold red][✖] Package {package_name} not found or has no APK paths.[/bold red]")
            return
            
        from rich.progress import Progress, TextColumn, BarColumn, TaskProgressColumn, TimeRemainingColumn
            
        if len(paths) == 1:
            # Single APK
            apk_path = paths[0]
            filename = os.path.basename(apk_path)
            final_dest = os.path.join(dest_path, filename)
            status.stop()
            
            with Progress(
                TextColumn("  [bold cyan]{task.description}"),
                BarColumn(bar_width=40),
                TaskProgressColumn(),
                TimeRemainingColumn(),
                console=console
            ) as progress:
                task_id = progress.add_task(f"Pulling {filename}", total=100)
                try:
                    run_adb_pull_with_progress(target_device, apk_path, final_dest, progress, task_id)
                    print_result_panel(package_name, final_dest, "Single APK")
                except subprocess.CalledProcessError:
                    progress.stop()
                    fallback_pull_with_progress(target_device, [apk_path], dest_path, False, package_name)
        else:
            # Split APK
            final_dest_dir = os.path.join(dest_path, f"{package_name}_apks")
            os.makedirs(final_dest_dir, exist_ok=True)
            status.stop()
            
            success_count = 0
            with Progress(
                TextColumn("  [bold cyan]{task.description}"),
                BarColumn(bar_width=40),
                TaskProgressColumn(),
                TimeRemainingColumn(),
                console=console
            ) as progress:
                overall_task = progress.add_task("Pulling Split APKs (Overall)", total=len(paths))
                for apk_path in paths:
                    filename = os.path.basename(apk_path)
                    dest_file = os.path.join(final_dest_dir, filename)
                    file_task = progress.add_task(f"Pulling {filename}", total=100)
                    try:
                        run_adb_pull_with_progress(target_device, apk_path, dest_file, progress, file_task)
                        success_count += 1
                    except subprocess.CalledProcessError:
                        try:
                            progress.remove_task(file_task)
                        except:
                            pass
                        progress.stop()
                        fallback_pull_with_progress(target_device, paths, dest_path, True, package_name)
                        return
                    finally:
                        try:
                            progress.remove_task(file_task)
                        except:
                            pass
                        progress.update(overall_task, advance=1)
            
            print_result_panel(package_name, final_dest_dir, f"Split APKs ({success_count}/{len(paths)} files)")
