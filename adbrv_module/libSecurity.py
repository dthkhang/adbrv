"""
Library security analysis tools for .so files
"""

import os
import subprocess
import sys
from .utils import print_colored, print_error, print_success, print_warning, RED, GREEN, YELLOW, RESET

def check_lib_security():
    """
    Check security features of .so files in current directory
    """
    # Find all .so files in current directory and subdirectories
    try:
        result = subprocess.run(['find', '.', '-name', '*.so'], capture_output=True, text=True, check=True)
        so_files = [line.strip() for line in result.stdout.splitlines() if line.strip()]
    except subprocess.CalledProcessError:
        print_error("Error finding .so files")
        return
    except FileNotFoundError:
        print_error("'find' command not found. Please ensure you're on a Unix-like system.")
        return
    
    if not so_files:
        print_error("No .so files found in current directory")
        return
    
    for sofile in so_files:
        print(f"{sofile}:")
        
        # Check PIE/PIC (Position Independent Executable/Code)
        pie_result = check_pie_pic(sofile)
        print(f"   {pie_result}")
        
        # Check Stack Canary
        canary_result = check_stack_canary(sofile)
        print(f"   {canary_result}")
        
        # Check Debug Symbols
        debug_result = check_debug_symbols(sofile)
        print(f"   {debug_result}")
        
        print()

def check_pie_pic(sofile):
    """Check if PIE/PIC is enabled"""
    try:
        result = subprocess.run(['greadelf', '-h', sofile], capture_output=True, text=True, check=True)
        for line in result.stdout.splitlines():
            if 'Type:' in line:
                type_value = line.split()[1]
                if type_value == 'DYN':
                    return f"[{GREEN}PASS{RESET}] - MASTG-TEST-0222: PIE/PIC enabled - Type: DYN"
                elif type_value == 'EXEC':
                    return f"{RED}[FAIL] - MASTG-TEST-0222: PIE/PIC not enabled{RESET} - Type: EXEC"
                else:
                    return f"[{YELLOW}WARN{RESET}] - MASTG-TEST-0222: Unknown type ({type_value})"
    except subprocess.CalledProcessError:
        return f"{RED}[ERROR] - MASTG-TEST-0222: Cannot read ELF header{RESET}"
    except FileNotFoundError:
        return f"{RED}[ERROR] - MASTG-TEST-0222: greadelf not found{RESET}"
    return f"{RED}[ERROR] - MASTG-TEST-0222: Cannot determine type{RESET}"

def check_stack_canary(sofile):
    """Check if Stack Canary is enabled"""
    try:
        result = subprocess.run(['strings', sofile], capture_output=True, text=True, check=True)
        if '__stack_chk_fail' in result.stdout:
            return f"[{GREEN}PASS{RESET}] - MASTG-TEST-0223: Stack Canary detected"
        else:
            return f"{RED}[FAIL] - MASTG-TEST-0223: Stack Canaries Not Enabled{RESET}"
    except subprocess.CalledProcessError:
        return f"{RED}[ERROR] - MASTG-TEST-0223: Cannot read strings{RESET}"
    except FileNotFoundError:
        return f"{RED}[ERROR] - MASTG-TEST-0223: strings command not found{RESET}"

def check_debug_symbols(sofile):
    """Check if debug symbols are present"""
    try:
        result = subprocess.run(['greadelf', '-S', sofile], capture_output=True, text=True, check=True)
        if '.debug' in result.stdout:
            return f"{RED}[FAIL] - MASTG-TEST-0288: Debugging symbols present{RESET}"
        else:
            return f"[{GREEN}PASS{RESET}] - MASTG-TEST-0288: No debugging symbols"
    except subprocess.CalledProcessError:
        return f"{RED}[ERROR] - MASTG-TEST-0288: Cannot read sections{RESET}"
    except FileNotFoundError:
        return f"{RED}[ERROR] - MASTG-TEST-0288: greadelf not found{RESET}"
