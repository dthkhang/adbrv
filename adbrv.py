#!/usr/bin/env python3
__version__ = "1.5.0"
import sys
from adbrv_module.proxy import set_proxy, unset_proxy_and_reverse, ProxyError
from adbrv_module.devices import get_connected_devices, print_all_status, check_devices_info, AdbError
from adbrv_module.fridaTools import frida_kill, start_frida_server
from adbrv_module.checkSymbols import check_symbols
from adbrv_module.resignAPK import resign_apk
from adbrv_module.findSOfile import find_so_files
from adbrv_module.libSecurity import check_lib_security
from adbrv_module.core import print_help, is_valid_port, parse_args, update_script, CoreError

def main():
    # Check for --checksym flag
    if '--checksym' in sys.argv:
        idx = sys.argv.index('--checksym')
        if idx+1 >= len(sys.argv):
            print('[!] Please provide the apktool output folder (e.g. base)')
            sys.exit(1)
        base_folder = sys.argv[idx+1]
        check_symbols(base_folder)
        sys.exit(0)
    
    # Check for --findso flag
    if '--findso' in sys.argv:
        find_so_files()
        sys.exit(0)
    
    # Check for --libsec flag
    if '--libsec' in sys.argv:
        check_lib_security()
        sys.exit(0)
    
    try:
        # Check for --resign flag and forward to uber-apk-signer if present
        if '--resign' in sys.argv:
            idx = sys.argv.index('--resign')
            # All args after --resign are for uber-apk-signer
            resign_args = sys.argv[idx+1:]
            resign_apk(resign_args)

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