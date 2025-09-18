"""
Native library symbol checking tools
"""

import os
import subprocess
import sys
from .utils import get_nm_path, print_colored, print_separator, print_error, print_info

def check_symbols(base_folder):
    """
    Check for internal symbols in .so files in the specified directory
    """
    lib_dir = os.path.join(base_folder, 'lib')
    if not os.path.isdir(lib_dir):
        print_error(f"lib directory not found: {lib_dir}")
        sys.exit(1)
        
    abi_folders = [f for f in os.listdir(lib_dir) if os.path.isdir(os.path.join(lib_dir, f))]
    if not abi_folders:
        print_error(f"No ABI folders found in {lib_dir}")
        sys.exit(1)
        
    # Select ABI folder
    if len(abi_folders) == 1:
        chosen_abi = abi_folders[0]
        print_info(f"Only one ABI folder found: {chosen_abi}")
    else:
        print_info("Found ABI folders:")
        for idx, folder in enumerate(abi_folders):
            print(f"  [{idx+1}] {folder}")
        while True:
            choice = input(f"Select ABI folder to scan [1-{len(abi_folders)}]: ").strip()
            if choice.isdigit() and 1 <= int(choice) <= len(abi_folders):
                chosen_abi = abi_folders[int(choice)-1]
                break
            print("Invalid selection. Please enter a valid number.")
            
    scan_dir = os.path.join(lib_dir, chosen_abi)
    if not os.path.isdir(scan_dir):
        print_error(f"Selected ABI folder not found: {scan_dir}")
        sys.exit(1)
        
    # Check nm tool availability
    nm_path = get_nm_path()
    if not os.path.isfile(nm_path):
        print_error(f"nm tool not found at: {nm_path}")
        sys.exit(1)
        
    # Scan .so files
    so_files = [f for f in os.listdir(scan_dir) if f.endswith('.so')]
    if not so_files:
        print_error(f"No .so files found in {scan_dir}")
        sys.exit(1)
        
    print_info(f"Scanning .so files in: {scan_dir}")
    print_separator()
    
    for sofile in so_files:
        so_path = os.path.join(scan_dir, sofile)
        print_colored(sofile)
        
        # Check internal/debug symbols
        check_internal_symbols(nm_path, so_path)
        
        # Check exported/dynamic symbols
        check_exported_symbols(nm_path, so_path)
        
        print_separator()

def check_internal_symbols(nm_path, so_path):
    """Check for internal/debug symbols using nm -a"""
    try:
        symbol_all = subprocess.run([nm_path, '-a', so_path], capture_output=True, text=True)
        lines_all = [l for l in symbol_all.stdout.splitlines() if 'no symbols' not in l and not l.endswith(':')]
    except Exception:
        lines_all = []
        
    if not lines_all:
        print('[STRIPPED -a] No internal/debug symbols found.')
    else:
        print('[FOUND SYMBOLS -a] Internal/debug symbols may exist. Example:')
        print('\n'.join(lines_all[:5]))

def check_exported_symbols(nm_path, so_path):
    """Check for exported/dynamic symbols using nm -D"""
    try:
        symbol_dyn = subprocess.run([nm_path, '-D', so_path], capture_output=True, text=True)
        lines_dyn = [l for l in symbol_dyn.stdout.splitlines() if 'no symbols' not in l and not l.endswith(':')]
    except Exception:
        lines_dyn = []
        
    if not lines_dyn:
        print('[No Exported JNI Symbols -D] No dynamic (JNI/API) symbols found.')
    else:
        print('[Exported Symbols -D] JNI/public symbols:')
        print('\n'.join(lines_dyn[:5]))
