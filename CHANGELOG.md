# Changelog

All notable changes to this project will be documented in this file.

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
