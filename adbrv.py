#!/usr/bin/env python3
__version__ = "1.3.0"
import sys
from adbrv_module.proxy import set_proxy, unset_proxy_and_reverse, ProxyError
from adbrv_module.devices import get_connected_devices, print_all_status, check_devices_info, frida_kill, start_frida_server, AdbError
from adbrv_module.core import print_help, is_valid_port, parse_args, update_script, CoreError

def main():
    try:
        # Check for --resign flag and forward to uber-apk-signer if present
        if '--resign' in sys.argv:
            import subprocess
            import os
            idx = sys.argv.index('--resign')
            # All args after --resign are for uber-apk-signer
            resign_args = sys.argv[idx+1:]
            jar_path = os.path.join(os.path.dirname(__file__), 'adbrv_module', 'tools', 'uber-apk-signer-1.3.0.jar')
            if not os.path.isfile(jar_path):
                print(f"[!] uber-apk-signer jar not found at {jar_path}")
                sys.exit(1)
            cmd = ['java', '-jar', jar_path] + resign_args
            try:
                result = subprocess.run(cmd)
                sys.exit(result.returncode)
            except Exception as e:
                print(f"[!] Error running uber-apk-signer: {e}")
                sys.exit(1)

        # ...existing code...
        cmd, local_port, device_port, serial = parse_args(sys.argv)
        if cmd == 'help':
            print_help()
            sys.exit(0)
        elif cmd == 'status':
            devices = get_connected_devices()
            if serial:
                if serial not in devices:
                    print(f"[!] Device {serial} not found.")
                    sys.exit(1)
                check_devices_info(serial)
            else:
                check_devices_info()
            sys.exit(0)
        elif cmd == 'update':
            update_script()
            sys.exit(0)
        elif cmd == 'version':
            print(f"adbrv version {__version__}")
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
        elif cmd == 'frida_kill':
            frida_kill(serial)
            sys.exit(0)
        elif cmd == 'frida_start':
            start_frida_server(serial)
            sys.exit(0)
        else:
            print("[!] Invalid arguments.")
            print_help()
            sys.exit(1)
    except (AdbError, ProxyError, CoreError) as e:
        print(f"[!] {e}")
        sys.exit(1)
if __name__ == "__main__":
    main()