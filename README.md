# adbrv

> 🔄 A Python utility for setting up **ADB reverse port forwarding** and configuring **HTTP proxy** on Android devices — ideal for debugging, traffic interception, and mobile app analysis.

`adbrv` is a lightweight command-line script designed to streamline the process of forwarding Android device traffic through your host machine. It enables reverse ADB port forwarding and sets system-wide HTTP proxy settings on the device, making it easier to inspect or intercept network requests using tools like Burp Suite, ZAP, or mitmproxy.

---


## ✨ Features

- 🔢 **Port validation**
  - Rejects invalid ports (non-integer or outside range 1–65535).

- 📱 **Device connection checks**
  - Alerts when no device is connected.
  - Prompts for `--device <serial>` if multiple devices are attached.

- 🎯 **Device targeting**
  - Supports selecting specific devices with `--device <serial>`.

- 🌐 **Proxy setup & teardown**
  - Sets ADB reverse and HTTP proxy on a specific or the only connected device.
  - `--unset` will remove all reverse ports and reset HTTP proxy settings.

- 📊 **Status reporting**
  - `--status` displays all connected devices, active proxy settings, and reverse port mappings in a clear tree format.
  - Enhanced Frida status shows user (root/shell) and PID information.

- 🧩 **Frida management**
  - `--frida on` to start frida-server automatically with root privileges.
  - `--frida kill` to kill all running frida-server processes (with confirmation if multiple processes).
  - Status output shows Frida server user (root/shell) and PID if running.
  - **Recommended:** Use frida-server version 16.6.3 for best stability.

- 🗝️ **APK resigning (uber-apk-signer integration)**
  - `--resign` flag allows you to resign APK files directly from adbrv using the integrated [uber-apk-signer](https://github.com/patrickfav/uber-apk-signer).
  - Supports all original uber-apk-signer options and flags.

- ⚙️ **Reliable subprocess execution**
  - Uses `subprocess` instead of `os.system` for better control and output handling.

- 🚫 **Handles disconnects gracefully**
  - Detects and reports if a device disconnects during execution.

---

## 📥 Installation

### 1. Clone the repository

```bash
git clone https://github.com/dthkhang/adbrv.git
cd adbrv
```

### 2. Install as CLI tool

```bash
pip install .
```

This will install `adbrv` as a global command. You can now run it from anywhere in your terminal:

```bash
adbrv --help
```

> If you're using a virtual environment (recommended), activate it before running `pip install .`

---

## 📱 Device setup & permissions

Make sure your Android device:

- 🔓 Has **USB debugging** enabled (in Developer Options)
- ✅ Is **authorized** via ADB (`adb devices` must list the device as "device")
- ⚠️ Accepts reverse port and proxy settings (some OEMs may block this)

You can verify connectivity with:

```bash
adb devices
```

If no device appears, try:

- Replugging the USB cable
- Enabling "Trust this computer" on the Android screen
- Running `adb kill-server && adb start-server`

---

## 🚀 Usage

adbrv --status [--device <serial>]
adbrv --frida on [--device <serial>]
adbrv --frida kill [--device <serial>]
adbrv --update
adbrv --version
adbrv -h | --help

```bash
adbrv --set <local_port> <device_port> [--device <serial>]
    # Set up ADB reverse and HTTP proxy on the Android device
adbrv --unset [--device <serial>]
    # Remove proxy and all reverse ports on the selected (or all) devices
adbrv --status [--device <serial>]
    # Display proxy, reverse port, and frida-server status for each connected device
adbrv --frida on [--device <serial>]
    # Start frida-server on the device with root privileges
adbrv --frida kill [--device <serial>]
    # Kill all running frida-server processes on the device
    # If multiple processes are found, you will be asked to confirm before killing all
    # After stopping, the status will be checked and displayed
adbrv --update
    # Automatically update the script to the latest version from GitHub
adbrv --version
    # Show current version
adbrv -h | --help
    # Show help message
adbrv --resign --apk <file.apk> [any other uber-apk-signer options]
    # Resign APK file using the integrated uber-apk-signer tool
```

---


* Set proxy on the only connected device:

  ```bash
  adbrv --set 8083 8083
  ```

* Set proxy on a specific device:

  ```bash
  adbrv --set 8083 8083 --device emulator-5554
  ```

* Unset proxy and remove all reverse ports:

  ```bash
  adbrv --unset
  adbrv --unset --device emulator-5554
  ```

* View current proxy, reverse, and frida-server status:

  ```bash
  adbrv --status
  adbrv --status --device emulator-5554
  ```

  Example output:
  ```
  Device 0A091FDD4000G0
  ├── Model       : Pixel 5
  ├── Android     : 14
  ├── Root Access : Yes
  ├── Frida       : On (root - PID: 11499)
  ├── Proxy       : localhost:8083
  └── Reverse     : tcp:8083 tcp:8083
  ```

* Start frida-server:

  ```bash
  adbrv --frida on
  adbrv --frida on --device emulator-5554
  ```

* Kill frida-server:

  ```bash
  adbrv --frida kill
  adbrv --frida kill --device emulator-5554
  ```

* Update the script to the latest version from GitHub:

  ```bash
  adbrv --update
  ```

* Check the current version:

  ```bash
  adbrv --version
  ```

* Show help:

  ```bash
  adbrv --help
  adbrv -h
  ```

---



## 📝 APK Resign & Uber APK Signer Integration

adbrv natively integrates [uber-apk-signer](https://github.com/patrickfav/uber-apk-signer) to help you quickly resign APK files.

### Usage

```bash
adbrv --resign --apk <file.apk> [any other uber-apk-signer options]
```

Example:

```bash
adbrv --resign --apk retest.apk
```

You can use any original flag of uber-apk-signer, for example:

```bash
adbrv --resign -h
adbrv --resign --apk my.apk --ks my.keystore --ksAlias alias --ksPass pass
```

> Note: The file `uber-apk-signer-1.3.0.jar` is bundled in `adbrv_module/tools/`. Java must be installed on your system to use this feature.

---
## 📝 Notes
- If no device is specified and multiple devices are connected, you will be prompted to specify a device.
- **Frida management is fully automated:** Both start and kill commands are available.
- **Recommended:** Use frida-server version 16.6.3 for best stability.

---

## 📦 Requirements

* Python 3.x
* Android Debug Bridge (`adb`) must be installed and accessible from the system `PATH`

---

## 📄 License

This project is licensed under the [MIT License](LICENSE).  
© 2025 kx4n9