import sys

class CoreError(Exception):
    pass

def print_help():
        print("""
Usage:

Command                                Description
---------------------------------------------------------------
adbrv --set <local_port> <device_port>  Set up reverse proxy
adbrv --unset [--device <serial>]      Remove proxy/reverse
adbrv --frida on [--device <serial>]   Start frida-server
adbrv --frida kill [--device <serial>]  Kill frida-server
adbrv --status [--device <serial>]     Show device status
adbrv --resign --apk <file.apk> [options]  Resign APK using integrated uber-apk-signer
adbrv --checksym <path/to/base>  Check for internal symbols in .so files
adbrv --update                         Update this script
adbrv --version                        Show version
adbrv -h | --help                      Show help

Examples:

  Command                                 Description
  ---------------------------------------------------------------
  adbrv --set 8083 8083                   Set up reverse proxy
  adbrv --set 8083 8083 --device <serial> Set up reverse proxy for specific device
  adbrv --unset                           Remove proxy/reverse
  adbrv --unset --device <serial>         Remove proxy/reverse for specific device
  adbrv --status --device <serial>        Show status for specific device
  adbrv --frida kill                      Kill frida-server
  adbrv --frida on [--device <serial>]    Start frida-server on the device
  adbrv --frida kill [--device <serial>]  Kill all running frida-server processes on the device. If multiple processes are found, you will be asked to confirm before killing all. After stopping, the status will be checked and displayed.
  adbrv --resign --apk my.apk             Resign APK file (all uber-apk-signer options supported)
  adbrv --checksym base                   Check for internal symbols in .so files in the specified directory (point to the folder containing full source code, e.g. 'base' from apktool d base.apk)
  adbrv --status                          Show device status
  adbrv --update                          Update this script
  adbrv --version                         Show version
  adbrv --help / adbrv -h                 Show help

Notes:
- If no device is specified and multiple devices are connected, you will be prompted to specify a device.
- When stopping frida-server, you must confirm (y/n) if multiple processes are found.
- For APK resigning, Java is required. All original uber-apk-signer flags are supported.
""")

def is_valid_port(port):
    try:
        port = int(port)
        return 1 <= port <= 65535
    except ValueError:
        return False

def parse_args(argv):
    # Returns: (cmd, local_port, device_port, serial)
    # cmd: 'set', 'unset', 'status', 'help', 'update', 'version', 'frida_kill'
    if len(argv) == 2 and argv[1] in ['-h', '--help']:
        return ('help', None, None, None)
    if len(argv) >= 2 and argv[1] == '--status':
        serial = None
        if '--device' in argv:
            idx = argv.index('--device')
            if idx+1 < len(argv):
                serial = argv[idx+1]
            else:
                raise CoreError("Missing serial after --device.")
        return ('status', None, None, serial)
    if len(argv) >= 2 and argv[1] == '--unset':
        serial = None
        if '--device' in argv:
            idx = argv.index('--device')
            if idx+1 < len(argv):
                serial = argv[idx+1]
            else:
                raise CoreError("Missing serial after --device.")
        return ('unset', None, None, serial)
    if len(argv) >= 2 and argv[1] == '--update':
        return ('update', None, None, None)
    if len(argv) >= 2 and argv[1] == '--version':
        return ('version', None, None, None)
    if len(argv) >= 2 and argv[1] == '--frida':
        if len(argv) < 3:
            return ('help', None, None, None)
        if argv[2] == 'kill':
            serial = None
            if '--device' in argv:
                idx = argv.index('--device')
                if idx+1 < len(argv):
                    serial = argv[idx+1]
                else:
                    raise CoreError("Missing serial after --device.")
            return ('frida_kill', None, None, serial)
        elif argv[2] == 'on':
            serial = None
            if '--device' in argv:
                idx = argv.index('--device')
                if idx+1 < len(argv):
                    serial = argv[idx+1]
                else:
                    raise CoreError("Missing serial after --device.")
            return ('frida_start', None, None, serial)
        else:
            return ('help', None, None, None)
    if len(argv) >= 4 and argv[1] == '--set':
        local_port = argv[2]
        device_port = argv[3]
        serial = None
        if '--device' in argv:
            idx = argv.index('--device')
            if idx+1 < len(argv):
                serial = argv[idx+1]
            else:
                raise CoreError("Missing serial after --device.")
        return ('set', local_port, device_port, serial)
    return (None, None, None, None)

def update_script():
    import os, shutil, re, urllib.request, subprocess, sys
    print("[+] Checking for updates from GitHub...")
    try:
        # Get current version
        from adbrv import __version__
        current_version = __version__
        
        # Check if we're running from installed package
        import adbrv
        script_path = os.path.realpath(adbrv.__file__)
        
        # If running from installed package, auto update via pip
        if "site-packages" in script_path:
            print("[i] You are using the installed package version.")
            print("[+] Auto-updating via pip...")
            
            try:
                # Run pip install --upgrade from GitHub
                result = subprocess.run(
                    [sys.executable, "-m", "pip", "install", "--upgrade", "git+https://github.com/dthkhang/adbrv.git"],
                    capture_output=True,
                    text=True,
                    check=True
                )
                print("[+] Update successful!")
                print("[i] Please re-run the script to use the new version.")
                return
            except subprocess.CalledProcessError as e:
                print(f"[-] Update failed: {e}")
                print("[i] You can try manually: pip install --upgrade git+https://github.com/dthkhang/adbrv.git")
                return
            except Exception as e:
                print(f"[-] Unexpected error during update: {e}")
                print("[i] You can try manually: pip install --upgrade git+https://github.com/dthkhang/adbrv.git")
                return
        
        # If running from source, update from GitHub
        GITHUB_RAW_URL = "https://raw.githubusercontent.com/dthkhang/adbrv/main/adbrv.py"
        with urllib.request.urlopen(GITHUB_RAW_URL) as response:
            new_code = response.read().decode('utf-8')
        
        # Extract version from new_code
        m = re.search(r'__version__\s*=\s*"([^"]+)"', new_code)
        new_version = m.group(1) if m else None
        
        if new_version is None:
            raise CoreError("Could not determine version of the downloaded script.")
        if new_version == current_version:
            print(f"[i] You are already using the latest version ({current_version}).")
            return
        
        # Backup current script
        backup_dir = os.path.join(os.path.dirname(script_path), "backup")
        os.makedirs(backup_dir, exist_ok=True)
        backup_path = os.path.join(backup_dir, f"adbrv.py.bak.{current_version}")
        shutil.copy2(script_path, backup_path)
        
        # Write new code
        with open(script_path, "w", encoding="utf-8") as f:
            f.write(new_code)
        
        print(f"[+] Update successful! (Backup saved as {backup_path})")
        print("[!] Please re-run the script.")
    except Exception as e:
        raise CoreError(f"Update failed: {e}")