"""
Native library symbol checking tools
"""

import os
import subprocess
import sys
from rich.console import Console
from rich.table import Table
from rich import box
from rich.panel import Panel

console = Console()

def get_nm_path():
    # Helper from utils (assuming get_nm_path logic is there or we can inline it here if we want but wait, I can just import it from .utils)
    from .utils import get_nm_path
    return get_nm_path()

def check_symbols(base_folder):
    """
    Check for internal symbols in .so files in the specified directory
    """
    lib_dir = os.path.join(base_folder, 'lib')
    if not os.path.isdir(lib_dir):
        console.print(f"[bold red][!] lib directory not found: {lib_dir}[/bold red]")
        sys.exit(1)
        
    abi_folders = [f for f in os.listdir(lib_dir) if os.path.isdir(os.path.join(lib_dir, f))]
    if not abi_folders:
        console.print(f"[bold red][!] No ABI folders found in {lib_dir}[/bold red]")
        sys.exit(1)
        
    # Select ABI folder
    if len(abi_folders) == 1:
        chosen_abi = abi_folders[0]
        console.print(f"[cyan][*] Only one ABI folder found: {chosen_abi}[/cyan]")
    else:
        console.print("[cyan][*] Found ABI folders:[/cyan]")
        for idx, folder in enumerate(abi_folders):
            console.print(f"  [{idx+1}] {folder}")
        while True:
            choice = input(f"Select ABI folder to scan [1-{len(abi_folders)}]: ").strip()
            if choice.isdigit() and 1 <= int(choice) <= len(abi_folders):
                chosen_abi = abi_folders[int(choice)-1]
                break
            console.print("[bold yellow]Invalid selection. Please enter a valid number.[/bold yellow]")
            
    scan_dir = os.path.join(lib_dir, chosen_abi)
    if not os.path.isdir(scan_dir):
        console.print(f"[bold red][!] Selected ABI folder not found: {scan_dir}[/bold red]")
        sys.exit(1)
        
    # Check nm tool availability
    nm_path = get_nm_path()
    if not os.path.isfile(nm_path):
        console.print(f"[bold red][!] nm tool not found at: {nm_path}[/bold red]")
        sys.exit(1)
        
    # Scan .so files
    so_files = [f for f in os.listdir(scan_dir) if f.endswith('.so')]
    if not so_files:
        console.print(f"[bold red][!] No .so files found in {scan_dir}[/bold red]")
        sys.exit(1)
        
    console.print(f"\n[bold blue]Scanning .so files in: {scan_dir}[/bold blue]")
    
    for sofile in so_files:
        so_path = os.path.join(scan_dir, sofile)
        
        # Check internal/debug symbols
        internal_content, has_internal = check_internal_symbols(nm_path, so_path)
        
        # Check exported/dynamic symbols
        exported_content, has_exported = check_exported_symbols(nm_path, so_path)
        
        content = f"[bold magenta]Internal/Debug Symbols:[/bold magenta]\n{internal_content}\n\n[bold magenta]Exported/Dynamic Symbols:[/bold magenta]\n{exported_content}"
        
        border_style = "green" if not has_internal else "yellow"
        
        panel = Panel(
            content,
            title=f"[bold]{sofile}[/bold]",
            border_style=border_style,
            box=box.ROUNDED,
            expand=False
        )
        console.print(panel)
        console.print()

def check_internal_symbols(nm_path, so_path):
    """Check for internal/debug symbols using nm -a"""
    has_internal = False
    try:
        symbol_all = subprocess.run([nm_path, '-a', so_path], capture_output=True, text=True)
        lines_all = [l for l in symbol_all.stdout.splitlines() if 'no symbols' not in l and not l.endswith(':')]
    except Exception:
        lines_all = []
        
    if not lines_all:
        content = "[green]✔ [STRIPPED -a] No internal/debug symbols found.[/green]"
    else:
        has_internal = True
        sample = '\n'.join(lines_all[:5])
        content = f"[yellow]⚠ [FOUND SYMBOLS -a] Internal/debug symbols may exist. Example:[/yellow]\n[dim]{sample}[/dim]"
    
    return content, has_internal

def check_exported_symbols(nm_path, so_path):
    """Check for exported/dynamic symbols using nm -D"""
    has_exported = False
    try:
        symbol_dyn = subprocess.run([nm_path, '-D', so_path], capture_output=True, text=True)
        lines_dyn = [l for l in symbol_dyn.stdout.splitlines() if 'no symbols' not in l and not l.endswith(':')]
    except Exception:
        lines_dyn = []
        
    if not lines_dyn:
        content = "[dim][No Exported JNI Symbols -D] No dynamic (JNI/API) symbols found.[/dim]"
    else:
        has_exported = True
        sample = '\n'.join(lines_dyn[:5])
        content = f"[cyan][Exported Symbols -D] JNI/public symbols:[/cyan]\n[dim]{sample}[/dim]"
    
    return content, has_exported
