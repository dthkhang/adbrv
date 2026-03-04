import subprocess, sys

class ProxyError(Exception):
    pass

def set_proxy(local_port, device_port, serial=None):
    adb_base = ["adb"]
    if serial:
        adb_base += ["-s", serial]
    print(f"[+] Reversing tcp:{local_port} -> tcp:{device_port}")
    try:
        subprocess.run(adb_base + ["reverse", f"tcp:{local_port}", f"tcp:{device_port}"], check=True)
        print(f"[+] Setting proxy on device to localhost:{local_port}")
        
        # Some devices (like Xiaomi) throw Permission denial unless using su for settings
        cmd = f"settings put global http_proxy localhost:{local_port}"
        su_result = subprocess.run(adb_base + ["shell", "su", "-c", cmd], capture_output=True)
        
        # If su failed or not rooted, try normal shell
        if su_result.returncode != 0:
            subprocess.run(adb_base + ["shell", "settings", "put", "global", "http_proxy", f"localhost:{local_port}"], check=True)
    except subprocess.CalledProcessError as e:
        raise ProxyError(f"Error setting proxy or reverse: {e}")

def unset_proxy_and_reverse(serial=None):
    adb_base = ["adb"]
    if serial:
        adb_base += ["-s", serial]
    try:
        print("[+] Unsetting proxy on device")
        
        cmd = "settings put global http_proxy :0"
        su_result = subprocess.run(adb_base + ["shell", "su", "-c", cmd], capture_output=True)
        if su_result.returncode != 0:
            subprocess.run(adb_base + ["shell", "settings", "put", "global", "http_proxy", ":0"], check=True)
            
        print("[+] Removing all reverse ports on device")
        subprocess.run(adb_base + ["reverse", "--remove-all"], check=True)
    except subprocess.CalledProcessError as e:
        raise ProxyError(f"Error unsetting proxy or reverse: {e}")