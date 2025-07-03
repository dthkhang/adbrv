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
  - `--status` displays all connected devices, active proxy settings, and reverse port mappings.

- ⚙️ **Reliable subprocess execution**
  - Uses `subprocess` instead of `os.system` for better control and output handling.

- 🚫 **Handles disconnects gracefully**
  - Detects and reports if a device disconnects during execution.

---

## 📥 Installation

### 1. Clone the repository

```bash
git clone https://github.com/yourusername/adb-rvproxy.git
cd adb-rvproxy
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

```bash
adbrv <local_port> <device_port> [--device <serial>]
    # Set up ADB reverse and HTTP proxy on the Android device

adbrv --unset [--device <serial>]
    # Remove proxy and all reverse ports on the selected (or all) devices

adbrv --status
    # Display proxy and reverse port status for each connected device

adbrv --update
    # Automatically update the script to the latest version from GitHub

adbrv -h | --help
    # Show help message
```

---

## 📚 Examples

* Set proxy on the only connected device:

  ```bash
  adbrv 8083 8083
  ```

* Set proxy on a specific device:

  ```bash
  adbrv 8083 8083 --device emulator-5554
  ```

* Unset proxy and remove all reverse ports:

  ```bash
  adbrv --unset
  ```

* View current proxy and reverse status:

  ```bash
  adbrv --status
  ```

* Update the script to the latest version from GitHub:

  ```bash
  adbrv --update
  ```

  > The script will automatically download the latest version from GitHub, overwrite the current file (and create a backup as `adb_rvproxy.py.bak`). After updating, simply re-run the script to use the newest version.

---

## 📦 Requirements

* Python 3.x
* Android Debug Bridge (`adb`) must be installed and accessible from the system `PATH`

---

## 📄 License

This project is licensed under the [MIT License](LICENSE).  
© 2025 kx4n9