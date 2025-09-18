"""
Common utilities and constants for adbrv module
"""

# Color constants for terminal output
BLUE = '\033[94m'
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
RESET = '\033[0m'

# Common file paths
NM_PATH_MACOS = '/Library/Developer/CommandLineTools/usr/bin/nm'
NM_PATH_LINUX = '/usr/bin/nm'

def get_nm_path():
    """Get the appropriate nm tool path based on platform"""
    import sys
    if sys.platform == 'darwin':
        return NM_PATH_MACOS
    else:
        return NM_PATH_LINUX

def print_colored(text, color=BLUE):
    """Print colored text to terminal"""
    print(f"{color}{text}{RESET}")

def print_success(text):
    """Print success message in green"""
    print(f"{GREEN}[+]{RESET} {text}")

def print_error(text):
    """Print error message in red"""
    print(f"{RED}[!]{RESET} {text}")

def print_info(text):
    """Print info message in yellow"""
    print(f"{YELLOW}[i]{RESET} {text}")

def print_warning(text):
    """Print warning message in yellow"""
    print(f"{YELLOW}[!]{RESET} {text}")

def print_separator():
    """Print a separator line"""
    print('------------------------------------------------------------')
