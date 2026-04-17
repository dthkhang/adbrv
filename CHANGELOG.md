# Changelog

All notable changes to this project will be documented in this file.

## [2.4.5] - 2026-04-17

### Fixed
- **frida-start chmod permission bug**: `frida-start` no longer crashes when the server binary is owned by `root`. The fix applies a 3-step strategy: (1) try `su -c chmod +x` first, (2) fallback to plain `shell chmod +x`, (3) if both fail, log a warning and proceed anyway since the file may already have execute permission (`--x`). This resolves the `Operation not permitted` error for `florida-server` and any other root-owned server binaries.

### Improved
- **ADB Command Batching**: Device info queries (`Model`, `Android version`, `Root check`) are now sent as a single batched `adb shell` command instead of 3 sequential calls, tripling the speed of the `status` command especially when multiple devices are connected.
- **Dynamic Tool Path Resolution**: Removed all hardcoded binary paths (e.g. `/Library/Developer/CommandLineTools/usr/bin/nm`). Now uses `shutil.which()` to automatically resolve the correct path on any OS/environment (macOS Homebrew, macOS CLT, Kali Linux, NixOS, etc.).
- **Dependency Pre-flight Checks**: Added graceful dependency validation before running analysis features. If `java`, `unzip`, `greadelf`, `strings`, or `nm` are missing, the tool now prints a clear red error message instead of crashing with a raw `FileNotFoundError`.

## [2.4.4] - 2026-03-09

### Added
- **Global Input Freeze on Warning**: Implemented a lockdown mechanism that disables all keyboard inputs (including arrows, enter, tab, and generic typing) whenever an invalid command warning is actively displayed in the autocomplete menu. This forces the user to resolve the error using Backspace.
- **Smart History Autocompletion**: Overridden the default history navigation mechanics (`Up`/`Down` keys when the menu is closed) to instantly trigger the autocomplete & warning engine upon loading a command from history. This ensures old, contextually invalid commands like `frida-kill` (when Frida is off) are caught immediately.

## [2.4.3] - 2026-03-09

### Added
- **Real-Time Workspace Cache Invalidation**: The REPL now intelligently and explicitly flushes the status cache (`devices`, `frida`, `unset`, and `packages_cache`) immediately after any command executes, ensuring data stays 100% accurate and fresh.
- **ADB Track-Devices Monitor**: Embedded a background thread powered by `adb track-devices` that live-streams hardware connection events. Automatically clears outdated suggestions if a USB cable is unplugged mid-session.
- **Graceful Thread Cleanup**: Complete memory cleanup via an explicit `try...finally` block to kill dangling background polls when escaping the workspace.
- **Refined Autocomplete Navigation**: Navigating the prompt toolkit menus with `Up`/`Down` arrows now isolates menu selection natively without automatically hijacking and pasting the content into the command line buffer.
- **Silent Status Fetching**: Eliminated jarring `<ansiyellow>[!] Checking...` intermediate prompts to ensure a smoother typing experience; validations silently optimistically succeed and only interrupt the user if genuinely invalid.

## [2.4.2] - 2026-03-06

### Added
- **Accent Folding for Smart Autocompletion**: The `pull` command's interactive App Name lookup now supports typeless diacritics (e.g., typing "Tai" auto-matches "Tải", "Nhac" auto-matches "Nhạc"). 
  - Resolves searching friction for localized applications (like Vietnamese app names) by normalizing UTF-8 Unicode to strictly ASCII NFKD format behind-the-scenes.
  - Display UI perfectly retains the original colorful, accented characters without compromising terminal search behavior.

## [2.4.1] - 2026-03-06

### Added
- **"Easter Egg" Pull Autocompletion**: The `pull` command in the interactive Workspace now features an intelligent, Frida-powered auto-complete engine. 
  - Automatically hooks into `frida-ps` (if active) via a background thread to fetch Human-Readable Application Names mapped to their Package Identifiers.
  - Contextual two-column Popup UI: Cleanly displays App Name on the left column and the Package Identifier on the right. User can search by both Native Name (e.g., "YouTube") or its ID ("com.google.android.youtube"), but the CLI ensures only the precise ID is inserted upon selection.
  - Apps with resolved names are automatically sorted and pinned to the top of the suggestion list for a native-like user experience.
  - Adaptive Layout System: gracefully falls back to a sleek single-column ID list without trailing whitespaces when Frida is offline or no names can be extracted, preserving terminal aesthetic integrity.

## [2.4.0] - 2026-03-06

### Added
- **Smart APK Pull Engine**: Introduced the `pull` command / workspace keyword to extract installed APKs directly from connected Android devices by their package name.
  - Automatically identifies and handles App Split files, seamlessly aggregating base & config split APKs into a single directory while retaining original application bundle filenames.
  - Robust **Root Fallback** strategy via `/data/local/tmp` using `su -c` for devices with permission restrictions on `/data/app/`.
  - Implemented dynamic Rich spinner UI and formatted status panels for elegant log outputs without spam or stutters.
- **TUI & REPL Enhancements**:
  - The interactive workspace now pre-fetches the list of all installed packages on the device into the `packages_cache` via an asynchronous background thread.
  - Contextual Auto-completion for the `pull` command: instantly suggests valid package names, followed by targeted hints like paths and the `-d` device flag.

## [2.3.0] - 2026-03-05

### Added
- **Strict REPL Grammar & Syntax Validation**: The interactive workspace now prevents invalid characters mid-command by actively validating keystrokes against building syntax rules. Typing malformed input (like `set 8080 x`) is completely blocked, ensuring foolproof execution.
- **Context-Aware Autocomplete Paths**: The workspace autocomplete now anticipates input states, showing contextual hints like `-d` right after finishing `unset ` or `frida-kill `, and `"enter your port xxxx xxxx"` after `set `, giving quick and seamless visual guidance.

## [2.2.0] - 2026-03-05

### Added
- **Default Interactive Workspace (REPL)**: Inspired by tools like Metasploit, running `adbrv` directly with no arguments now automatically drops you into a persistent `adbrv>` interactive session. Inside this shell, you can natively re-run commands like `status` or `frida-start` without exiting back to your OS console!
- **Workspace Context Awareness**: The REPL workspace is now restricted to only network and Frida-related commands (`set`, `unset`, `status`, `frida-start`, `frida-kill`), preventing irrelevant commands from cluttering the session.
- **Smart Status Output**: Commands like `set`, `unset`, and `frida-start` now automatically display device status immediately without requiring an additional `status` command, and cleanly strip the table title for a more streamlined readout.
- **Tailored Help Menu**: Entering `help` inside the workspace now beautifully renders a custom UI table that specifically lists only the permitted commands, complete with examples formatted precisely like the Typer CLI outside the workspace.

## [2.1.0] - 2026-03-05
### Added
- **Interactive TUI Menus**: Integrated `questionary` for arrow-key navigable console menus. Hand-typing inputs or blindly copying device IDs is a thing of the past!
  - `adbrv checksym` auto-displays a menu to select ABI folders when multiple architectures are found.
  - `adbrv frida-start` lets you pick right from a list if multiple `frida-server`/`florida-server` binaries reside in `/data/local/tmp`.
  - **Multi-device auto-prompt**: If multiple devices are plugged in (for any command like `set`, `status`, `frida-start`, `unset`), adbrv intercepts and shows a quick interactive menu to choose which device you want to target, removing the strict need for `--device ...` args.
- **Florida Server Support**: Fully extended the Frida management suite (`frida-start` / `frida-kill` / `status`) to dynamically recognize and manage `florida-server` binaries alongside `frida-server` automatically.

## [2.0.0] - 2026-03-04

### Added
- **Modern CLI Interface**: Fully migrated to `typer` framework for robust command-line parsing, argument validation, and out-of-the-box generated help documentation.
- **Beautiful Console Output**: Integrated `rich` library for aesthetic command-line output, including dynamic Spinners for loading tasks, aligned Tables for device status and examples, and fully colored/formatted error and success messages.
- **Smart System Fallback**: The proxy `set` and `unset` commands now leverage `su` to modify global settings directly (falling back to standard shell if `su` fails), avoiding arbitrary `Security exception: Permission denial` on devices with strict ROMs like Xiaomi.
- **Robust Auto-Update Mechanism**: The `update` command now intelligently handles modular Python packages by running `pip install --upgrade` against the GitHub repository rather than downloading arbitrary raw python text.

### Changed
- Replaced the legacy double-dash (`--set`, `--status`, `--frida on`) monolithic command argument parser with a robust set of modular Typer sub-commands (e.g. `adbrv set`, `adbrv status`, `adbrv frida-start`).

## [1.5.0] - 2025-01-27

### Added
- **APK .so file finder** (`--findso`): Quickly scan APK files to identify which ones contain native libraries
- **Library security analyzer** (`--libsec`): Comprehensive security analysis following MASTG standards
  - MASTG-TEST-0222: PIE/PIC (Position Independent Executable/Code) check
  - MASTG-TEST-0223: Stack Canary protection verification
  - MASTG-TEST-0288: Debug symbols detection
- **Modular architecture**: Refactored code into separate modules for better maintainability
  - `fridaTools.py`: Frida server management
  - `checkSymbols.py`: Native library symbol checking
  - `resignAPK.py`: APK resigning functionality
  - `findSOfile.py`: APK .so file finder
  - `libSecurity.py`: Library security analysis
  - `utils.py`: Common utilities and constants
- **Enhanced documentation**: Updated README with comprehensive APK analysis workflow
- **Color-coded output**: Improved visual feedback with colored terminal output

### Changed
- **Code organization**: Separated concerns into dedicated modules
- **Error handling**: Improved error messages and user feedback
- **Documentation**: Enhanced README with new features and usage examples

### Technical Details
- All new features follow MASTG (Mobile Application Security Testing Guide) standards
- Modular design allows for easier testing and maintenance
- Backward compatibility maintained for all existing features

## [1.4.1] - Previous Version

### Features
- ADB reverse port forwarding
- HTTP proxy configuration
- Frida server management
- APK resigning with uber-apk-signer
- Native library symbol checking
- Device status monitoring
