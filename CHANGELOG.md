# Changelog

All notable changes to this project will be documented in this file.

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
