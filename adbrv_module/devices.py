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
        print("[!] No devices connected.")
        return
    for serial in devices:
        model = adb_shell(["getprop", "ro.product.model"], serial) or "?"
        android = adb_shell(["getprop", "ro.build.version.release"], serial) or "?"
        su_check = adb_shell(["which", "su"], serial)
        root = "Yes" if su_check and su_check != '' else "No"
        frida_ps = adb_shell(["ps", "|", "grep", "frida-server"], serial)
        if frida_ps and "frida-server" in frida_ps:
            try:
                pid = None
                for line in frida_ps.splitlines():
                    if "frida-server" in line:
                        parts = line.split()
                        for p in parts[1:]:
                            if p.isdigit():
                                pid = p
                                break
                        if pid:
                            break
                frida_status = f"On (PID: {pid})" if pid else "On"
            except Exception:
                frida_status = "On"
        else:
            frida_status = "Off"
        proxy = get_proxy_status(serial)
        reverse = get_reverse_ports(serial)
        print(f"Device {serial}")
        print(f"├── Model       : {model}")
        print(f"├── Android     : {android}")
        print(f"├── Root Access : {root}")
        print(f"├── Frida       : {frida_status}")
        print(f"├── Proxy       : {proxy}")
        print(f"└── Reverse     : {reverse}")

def adb_shell(cmd, serial=None, check=True, input_text=None):
    adb_base = ["adb"]
    if serial:
        adb_base += ["-s", serial]
    try:
        result = subprocess.run(adb_base + ["shell"] + cmd, capture_output=True, text=True, check=check, input=input_text)
        return result.stdout.strip()
    except subprocess.CalledProcessError:
        return None

def frida_kill(serial=None):
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
        print("[i] No frida-server process running.")
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
        print("[i] No frida-server process running.")
        return
    if len(procs) > 1:
        print("Multiple frida-server processes found:")
        for pid, line in procs:
            print(f"  PID {pid}: {line}")
        confirm = input("Do you want to kill all frida-server processes? (y/n): ").strip().lower()
        if confirm != 'y':
            print("[i] Abort killing frida-server processes.")
            return
    for pid, _ in procs:
        adb_shell(["su", "-c", f"kill -9 {pid}"], serial)
        print(f"[+] Killed frida-server process PID {pid} on device {serial}.")
    print("[i] Checking frida-server status...")
    check_devices_info(serial)

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
    frida_ps = adb_shell(["ps", "|", "grep", "frida-server"], serial)
    if frida_ps and "frida-server" in frida_ps:
        try:
            pid = None
            for line in frida_ps.splitlines():
                if "frida-server" in line:
                    parts = line.split()
                    for p in parts[1:]:
                        if p.isdigit():
                            pid = p
                            break
                    if pid:
                        break
            frida_status = f"On (PID: {pid})" if pid else "On"
        except Exception:
            frida_status = "On"
    else:
        frida_status = "Off"
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