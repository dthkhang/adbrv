"""
Frida server management tools for Android devices
"""

import subprocess
import time
from .devices import get_connected_devices, adb_shell, AdbError
from .utils import print_success, print_error, print_info, print_warning

def start_frida_server(serial=None):
    """Start frida-server on Android device"""
    devices = get_connected_devices()
    if not devices:
        raise AdbError("No devices connected.")
    if not serial:
        if len(devices) == 1:
            serial = devices[0]
        else:
            raise AdbError("Multiple devices connected. Please specify --device <serial>.")
    
    adb_base = ["adb"]
    if serial:
        adb_base += ["-s", serial]
    
    fs = "/data/local/tmp/frida-server*"
    
    try:
        # Check if frida-server exists
        result = subprocess.run(adb_base + ["shell", "ls", fs], capture_output=True, text=True)
        
        if result.returncode != 0:
            print_error("Frida Server Not Found!!")
            print_warning("Please check the frida-server filename in /data/local/tmp. It must start with 'frida-server'.")
            return False
            
        # Get frida-server filename
        frida_files = result.stdout.strip().splitlines()
        if not frida_files:
            print_error("No frida-server files found!")
            print_warning("Please check the frida-server filename in /data/local/tmp. It must start with 'frida-server'.")
            return False
            
        if len(frida_files) == 1:
            fsName = frida_files[0]
            print_info(f"Found Frida Server: {fsName}")
        else:
            print_info(f"Found {len(frida_files)} Frida Server files:")
            for idx, fname in enumerate(frida_files):
                print(f"  [{idx+1}] {fname}")
            while True:
                choice = input(f"Select which frida-server to start [1-{len(frida_files)}]: ").strip()
                if choice.isdigit() and 1 <= int(choice) <= len(frida_files):
                    fsName = frida_files[int(choice)-1]
                    break
                print("Invalid selection. Please enter a valid number.")
            print_info(f"Selected Frida Server: {fsName}")

        # Check if already running
        ps_result = subprocess.run(adb_base + ["shell", "ps", "|", "grep", "frida-server"], 
                                 capture_output=True, text=True)

        if "frida-server" in ps_result.stdout:
            print_warning("Frida Server Is Running")
            return True

        # Start frida-server
        print_info("Start Frida Server...")
        print_info("Please wait...")

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
        verify_result = subprocess.run(adb_base + ["shell", "ps", "|", "grep", "frida-server"], 
                                     capture_output=True, text=True)
        
        if "frida-server" in verify_result.stdout:
            print_success("Frida Server Start Success!!")
            return True
        else:
            print_error("Frida Server Start Failed!! Check & Try Again")
            return False
            
    except subprocess.CalledProcessError as e:
        print_error(f"Error: {e}")
        return False
    except Exception as e:
        print_error(f"Unexpected error: {e}")
        return False

def frida_kill(serial=None):
    """Kill all running frida-server processes on the device"""
    devices = get_connected_devices()
    if not devices:
        raise AdbError("No devices connected.")
    if not serial:
        if len(devices) == 1:
            serial = devices[0]
        else:
            raise AdbError("Multiple devices connected. Please specify --device <serial>.")
            
    # List frida-server processes
    ps_out = adb_shell(["ps", "|", "grep", "frida-server"], serial)
    if not ps_out or "frida-server" not in ps_out:
        print_info("No frida-server process running.")
        return
        
    # Parse PIDs
    procs = []
    for line in ps_out.splitlines():
        if "frida-server" in line:
            parts = line.split()
            pid = None
            for p in parts[1:]:
                if p.isdigit():
                    pid = p
                    break
            if pid:
                procs.append((pid, line))
                
    if not procs:
        print_info("No frida-server process running.")
        return
        
    if len(procs) > 1:
        print("Multiple frida-server processes found:")
        for pid, line in procs:
            print(f"  PID {pid}: {line}")
        confirm = input("Do you want to kill all frida-server processes? (y/n): ").strip().lower()
        if confirm != 'y':
            print_info("Abort killing frida-server processes.")
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
    check_devices_info(serial)

def get_frida_status(serial):
    """Get frida-server status for a device"""
    frida_ps = adb_shell(["ps", "|", "grep", "frida-server"], serial)
    if frida_ps and "frida-server" in frida_ps:
        try:
            pid = None
            user = "shell"
            for line in frida_ps.splitlines():
                if "frida-server" in line:
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
