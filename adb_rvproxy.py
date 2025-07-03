#!/usr/bin/env python3
import sys, subprocess

def print_help():
    print("""
Adb reverse proxy:
  adb-rvproxy <local_port> <device_port> [--device <serial>]
  adb-rvproxy --unset [--device <serial>]
  adb-rvproxy --status
  adb-rvproxy -h | --help
    """)

def is_valid_port(port):
    try:
        port = int(port)
        return 1 <= port <= 65535
    except ValueError:
        return False

def get_connected_devices():
    try:
        result = subprocess.run(["adb", "devices"], capture_output=True, text=True)
        lines = result.stdout.strip().splitlines()[1:]  # skip first line
        devices = [line.split()[0] for line in lines if '\tdevice' in line]
        return devices
    except Exception as e:
        print(f"[!] Error running adb: {e}")
        sys.exit(1)

def set_proxy(local_port, device_port, serial=None):
    adb_base = ["adb"]
    if serial:
        adb_base += ["-s", serial]
    print(f"[+] Reversing tcp:{local_port} → tcp:{device_port}")
    try:
        subprocess.run(adb_base + ["reverse", f"tcp:{local_port}", f"tcp:{device_port}"], check=True)
        print(f"[+] Setting proxy on device to localhost:{local_port}")
        subprocess.run(adb_base + ["shell", "settings", "put", "global", "http_proxy", f"localhost:{local_port}"], check=True)
    except subprocess.CalledProcessError as e:
        print(f"[!] Error: {e}")
        print("[!] Device may have been disconnected during operation.")
        sys.exit(1)

def unset_proxy_and_reverse(serial=None):
    adb_base = ["adb"]
    if serial:
        adb_base += ["-s", serial]
    try:
        print("[+] Unsetting proxy on device")
        subprocess.run(adb_base + ["shell", "settings", "put", "global", "http_proxy", ":0"], check=True)
        print("[+] Removing all reverse ports on device")
        subprocess.run(adb_base + ["reverse", "--remove-all"], check=True)
    except subprocess.CalledProcessError as e:
        print(f"[!] Error: {e}")
        print("[!] Device may have been disconnected during operation.")
        sys.exit(1)

def get_proxy_status(serial=None):
    adb_base = ["adb"]
    if serial:
        adb_base += ["-s", serial]
    try:
        result = subprocess.run(adb_base + ["shell", "settings", "get", "global", "http_proxy"], capture_output=True, text=True, check=True)
        return result.stdout.strip()
    except subprocess.CalledProcessError:
        return "[Error: device disconnected]"

def get_reverse_ports(serial=None):
    adb_base = ["adb"]
    if serial:
        adb_base += ["-s", serial]
    try:
        result = subprocess.run(adb_base + ["reverse", "--list"], capture_output=True, text=True, check=True)
        return result.stdout.strip() or "(none)"
    except subprocess.CalledProcessError:
        return "[Error: device disconnected]"

def print_all_status():
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

def parse_args(argv):
    # Returns: (cmd, local_port, device_port, serial)
    # cmd: 'set', 'unset', 'status', 'help'
    if len(argv) == 2 and argv[1] in ['-h', '--help']:
        return ('help', None, None, None)
    if len(argv) >= 2 and argv[1] == '--status':
        return ('status', None, None, None)
    if len(argv) >= 2 and argv[1] == '--unset':
        serial = None
        if '--device' in argv:
            idx = argv.index('--device')
            if idx+1 < len(argv):
                serial = argv[idx+1]
            else:
                print("[!] Missing serial after --device.")
                sys.exit(1)
        return ('unset', None, None, serial)
    if len(argv) >= 3:
        local_port = argv[1]
        device_port = argv[2]
        serial = None
        if '--device' in argv:
            idx = argv.index('--device')
            if idx+1 < len(argv):
                serial = argv[idx+1]
            else:
                print("[!] Missing serial after --device.")
                sys.exit(1)
        return ('set', local_port, device_port, serial)
    return (None, None, None, None)

def main():
    cmd, local_port, device_port, serial = parse_args(sys.argv)

    if cmd == 'help':
        print_help()
        sys.exit(0)

    elif cmd == 'status':
        print_all_status()
        sys.exit(0)

    elif cmd == 'unset':
        devices = get_connected_devices()
        if not devices:
            print("[!] No devices connected.")
            sys.exit(1)
        if serial:
            if serial not in devices:
                print(f"[!] Device {serial} not found.")
                sys.exit(1)
            unset_proxy_and_reverse(serial)
        else:
            for d in devices:
                unset_proxy_and_reverse(d)
        sys.exit(0)

    elif cmd == 'set':
        if not is_valid_port(local_port) or not is_valid_port(device_port):
            print("[!] Invalid port. Port must be an integer between 1 and 65535.")
            sys.exit(1)
        devices = get_connected_devices()
        if not devices:
            print("[!] No devices connected.")
            sys.exit(1)
        if serial:
            if serial not in devices:
                print(f"[!] Device {serial} not found.")
                sys.exit(1)
            set_proxy(local_port, device_port, serial)
        else:
            if len(devices) > 1:
                print("[!] Multiple devices connected. Please specify --device <serial>.")
                sys.exit(1)
            set_proxy(local_port, device_port, devices[0])
        sys.exit(0)
    else:
        print("[!] Invalid arguments.")
        print_help()
        sys.exit(1)

if __name__ == "__main__":
    main()