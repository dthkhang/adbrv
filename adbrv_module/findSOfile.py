"""
Find .so files in APK files
"""

import os
import subprocess
import sys
from .utils import print_colored, print_error, print_success, RED, GREEN

def find_so_files():
    """
    Find .so files in all APK files in current directory
    """
    # Get all APK files in current directory
    apk_files = [f for f in os.listdir('.') if f.endswith('.apk')]
    
    if not apk_files:
        print_error("No APK files found in current directory")
        return
    
    for apk in apk_files:
        try:
            # Use unzip -l to list contents and grep for .so files
            result = subprocess.run(
                ['unzip', '-l', apk], 
                capture_output=True, 
                text=True, 
                check=True
            )
            
            # Filter for .so files (only actual .so files, not files with .so in name)
            so_files = [line for line in result.stdout.splitlines() if line.strip().endswith('.so')]
            
            if so_files:
                # Found .so files - print APK name in green
                print_colored(f"APK: {apk}", GREEN)
                for so_file in so_files:
                    print(f"  {so_file}")
            else:
                # No .so files found - print APK name in red
                print_colored(f"APK: {apk}", RED)
                print("  No .so files found")
                
        except subprocess.CalledProcessError as e:
            print_colored(f"APK: {apk}", RED)
            print_error(f"Error reading APK: {e}")
        except Exception as e:
            print_colored(f"APK: {apk}", RED)
            print_error(f"Unexpected error: {e}")
