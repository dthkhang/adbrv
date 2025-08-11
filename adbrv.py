#!/usr/bin/env python3
__version__ = "1.4.1"
import sys
from adbrv_module.proxy import set_proxy, unset_proxy_and_reverse, ProxyError
from adbrv_module.devices import get_connected_devices, print_all_status, check_devices_info, frida_kill, start_frida_server, AdbError
from adbrv_module.core import print_help, is_valid_port, parse_args, update_script, CoreError

def main():
    # Check for --checksym flag
    if '--checksym' in sys.argv:
            import os
            import subprocess
            idx = sys.argv.index('--checksym')
            if idx+1 >= len(sys.argv):
                print('[!] Please provide the apktool output folder (e.g. base)')
                sys.exit(1)
            base_folder = sys.argv[idx+1]
            lib_dir = os.path.join(base_folder, 'lib')
            if not os.path.isdir(lib_dir):
                print(f'[!] lib directory not found: {lib_dir}')
                sys.exit(1)
            abi_folders = [f for f in os.listdir(lib_dir) if os.path.isdir(os.path.join(lib_dir, f))]
            if not abi_folders:
                print(f'[!] No ABI folders found in {lib_dir}')
                sys.exit(1)
            if len(abi_folders) == 1:
                chosen_abi = abi_folders[0]
                print(f'[*] Only one ABI folder found: {chosen_abi}')
            else:
                print('[*] Found ABI folders:')
                for idx, folder in enumerate(abi_folders):
                    print(f'  [{idx+1}] {folder}')
                while True:
                    choice = input(f'Select ABI folder to scan [1-{len(abi_folders)}]: ').strip()
                    if choice.isdigit() and 1 <= int(choice) <= len(abi_folders):
                        chosen_abi = abi_folders[int(choice)-1]
                        break
                    print('Invalid selection. Please enter a valid number.')
            scan_dir = os.path.join(lib_dir, chosen_abi)
            if not os.path.isdir(scan_dir):
                print(f'[!] Selected ABI folder not found: {scan_dir}')
                sys.exit(1)
            # Scan .so files in scan_dir
            nm_path = '/Library/Developer/CommandLineTools/usr/bin/nm' if sys.platform == 'darwin' else '/usr/bin/nm'
            if not os.path.isfile(nm_path):
                print(f'[!] nm tool not found at: {nm_path}')
                sys.exit(1)
            so_files = [f for f in os.listdir(scan_dir) if f.endswith('.so')]
            if not so_files:
                print(f'[!] No .so files found in {scan_dir}')
                sys.exit(1)
            print(f'[*] Scanning .so files in: {scan_dir}')
            print('------------------------------------------------------------')
            BLUE = '\033[94m'
            RESET = '\033[0m'
            for sofile in so_files:
                so_path = os.path.join(scan_dir, sofile)
                print(f'{BLUE}{sofile}{RESET}')
                # Internal/debug symbols
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
                # Exported/dynamic symbols
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
                print('------------------------------------------------------------')
            sys.exit(0)
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