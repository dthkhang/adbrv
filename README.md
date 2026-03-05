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

- 🧩 **Frida & Florida management**
  - `frida-start` to start frida/florida-server automatically with root privileges. Shows an interactive menu if multiple server versions exist!
  - `frida-kill` to kill all running frida/florida-server processes (with confirmation if multiple processes).
  - Status output shows Frida/Florida server user (root/shell) and PID if running.
  - **Important:** The server binary in `/data/local/tmp` must contain `frida-server` or `florida-server` (e.g. `florida-server-16.6.3-android-arm64`). Otherwise, adbrv cannot detect or manage it.
  - **Recommended:** Use server version 16.6.3 for best stability.

- 🗝️ **APK resigning (uber-apk-signer integration)**
  - `--resign` flag allows you to resign APK files directly from adbrv using the integrated [uber-apk-signer](https://github.com/patrickfav/uber-apk-signer).
  - Supports all original uber-apk-signer options and flags.

- 🧪 **Native library symbol checker**
  - `--checksym <apktool_output_folder>` scans native libraries (`.so` files) in your APK decompiled folder.
  - Lists ABI folders (e.g. arm64-v8a, armeabi-v7a), lets you select which to scan.
  - Checks for internal/debug and exported JNI symbols in each `.so` file, highlights library names in blue for easy reading.

- 🔍 **APK .so file finder**
  - `--findso` quickly scans all APK files in current directory to find which ones contain native libraries.
  - Color-coded output: red for APKs without .so files, green for APKs with .so files.
  - Perfect for identifying which APK files contain native code before detailed analysis.

- 🛡️ **Library security analyzer**
  - `--libsec` performs comprehensive security analysis on .so files following MASTG (Mobile Application Security Testing Guide) standards.
  - Checks PIE/PIC (Position Independent Executable/Code) - MASTG-TEST-0222.
  - Verifies Stack Canary protection - MASTG-TEST-0223.
  - Detects debugging symbols presence - MASTG-TEST-0288.
  - Color-coded results: green for PASS, red for FAIL, yellow for WARN.

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
adbrv help
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

adbrv status [--device <serial>]
adbrv frida-start [--device <serial>]
adbrv frida-kill [--device <serial>]
adbrv update
adbrv version
adbrv -h | --help

```bash
adbrv set <local_port> <device_port> [--device <serial>]
  # Set up ADB reverse and HTTP proxy on the Android device
adbrv unset [--device <serial>]
  # Remove proxy and all reverse ports on the selected (or all) devices
adbrv status [--device <serial>]
  # Display proxy, reverse port, and frida-server status for each connected device
adbrv frida-start [--device <serial>]
  # Start frida-server on the device with root privileges
adbrv frida-kill [--device <serial>]
  # Kill all running frida-server processes on the device
  # If multiple processes are found, you will be asked to confirm before killing all
  # After stopping, the status will be checked and displayed
adbrv update
  # Automatically update the script to the latest version from GitHub
adbrv version
  # Show current version
adbrv help
  # Show help message
adbrv resign --apk <file.apk> [any other uber-apk-signer options]
  # Resign APK file using the integrated uber-apk-signer tool
adbrv checksym <apktool_output_folder>
  # Scan native libraries (.so) in the APK decompiled folder, select ABI, and check symbols
adbrv findso
  # Find .so files in APK files in current directory
adbrv libsec
  # Check security features of .so files (PIE, Stack Canary, Debug symbols)
```

---


* Set proxy on the only connected device:

  ```bash
  adbrv set 8083 8083
  ```

* Set proxy on a specific device:

  ```bash
  adbrv set 8083 8083 --device emulator-5554
  ```

* Unset proxy and remove all reverse ports:

  ```bash
  adbrv unset
  adbrv unset --device emulator-5554
  ```

* View current proxy, reverse, and frida-server status:

  ```bash
  adbrv status
  adbrv status --device emulator-5554
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
  adbrv frida-start
  adbrv frida-start --device emulator-5554
  ```

* Kill frida-server:

  ```bash
  adbrv frida-kill
  adbrv frida-kill --device emulator-5554
  ```

* Update the script to the latest version from GitHub:

  ```bash
  adbrv update
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

* Find .so files in APK files:

  ```bash
  adbrv findso
  ```

  Example output:
  ```
  APK: split_config.en.apk
    No .so files found
  APK: split_config.arm64_v8a.apk
      2113640  01-01-1981 01:01   lib/arm64-v8a/libVFaceLib.so
       271976  01-01-1981 01:01   lib/arm64-v8a/libVisionCamera.so
      1973128  01-01-1981 01:01   lib/arm64-v8a/libappmodules.so
  ```

* Check security features of .so files:

  ```bash
  adbrv libsec
  ```

  Example output:
  ```
  ./lib/arm64-v8a/libreactnative.so:
     [PASS] - MASTG-TEST-0222: PIE/PIC enabled - Type: DYN
     [PASS] - MASTG-TEST-0223: Stack Canary detected
     [PASS] - MASTG-TEST-0288: No debugging symbols

  ./lib/arm64-v8a/libc++_shared.so:
     [PASS] - MASTG-TEST-0222: PIE/PIC enabled - Type: DYN
     [FAIL] - MASTG-TEST-0223: Stack Canaries Not Enabled
     [PASS] - MASTG-TEST-0288: No debugging symbols
  ```

---

## 🔍 APK Analysis Workflow

adbrv provides a comprehensive toolkit for Android APK analysis, especially for security researchers and mobile app testers:

### 1. **Quick APK Overview** (`findso`)
```bash
adbrv findso
```
- Quickly identify which APK files contain native libraries
- Color-coded output for easy identification
- Perfect first step in APK analysis

### 2. **Security Assessment** (`libsec`)
```bash
adbrv libsec
```
- Comprehensive security analysis following MASTG standards
- Checks PIE/PIC, Stack Canary, and Debug symbols
- Essential for security testing and compliance

### 3. **Detailed Symbol Analysis** (`checksym`)
```bash
adbrv checksym <apktool_output_folder>
```
- Deep dive into native library symbols
- Identifies internal/debug vs exported symbols
- Useful for reverse engineering and vulnerability research

### 4. **APK Modification** (`resign`)
```bash
adbrv resign --apk <file.apk>
```
- Resign APK files for testing and analysis
- Integrated uber-apk-signer for reliable signing

### Typical Analysis Workflow:
```bash
# 1. Find APKs with native code
adbrv findso

# 2. Check security features
adbrv libsec

# 3. Decompile APK with apktool
apktool d target.apk

# 4. Analyze symbols in decompiled folder
adbrv checksym target

# 5. Resign for testing (if needed)
adbrv resign --apk target.apk
```

---

## 📝 APK Resign & Uber APK Signer Integration

adbrv natively integrates [uber-apk-signer](https://github.com/patrickfav/uber-apk-signer) to help you quickly resign APK files.

### Usage

```bash
adbrv resign --apk <file.apk> [any other uber-apk-signer options]
```

Example:

```bash
adbrv resign --apk retest.apk
```

You can use any original flag of uber-apk-signer, for example:

```bash
adbrv resign -h
adbrv resign --apk my.apk --ks my.keystore --ksAlias alias --ksPass pass
```

> Note: The file `uber-apk-signer-1.3.0.jar` is bundled in `adbrv_module/tools/`. Java must be installed on your system to use this feature.

---
## 📝 Notes
- If no device is specified and multiple devices are connected, you will be prompted to specify a device.
- **Frida/Florida management is fully automated & interactive:** Both start and kill commands are available, and you can pick versions from an interactive menu.
- **Recommended:** Use frida/florida-server version 16.6.3 for best stability.
- **Security analysis:** The `libsec` feature follows MASTG (Mobile Application Security Testing Guide) standards for comprehensive security assessment.
- **APK analysis workflow:** Use `findso` to identify APKs with native code, then `libsec` for security analysis, and `checksym` for detailed symbol inspection.

---

## 📦 Requirements

* Python 3.x
* Android Debug Bridge (`adb`) must be installed and accessible from the system `PATH`
* For `libsec` feature: `greadelf` and `strings` commands (available on macOS with Xcode Command Line Tools, or install `binutils` on Linux)
* For `resign` feature: Java runtime environment

---

## 📄 License

This project is licensed under the [MIT License](LICENSE).  
© 2025 kx4n9