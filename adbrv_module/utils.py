"""
Common utilities and constants for adbrv module
"""

# Color constants for terminal output
BLUE = '\033[94m'
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
RESET = '\033[0m'

def get_nm_path():
    """Get the appropriate nm tool path"""
    import shutil
    return shutil.which('nm')

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

def check_dependencies(tools_list):
    """Check if required system tools are installed"""
    import shutil, sys
    missing = []
    for tool in tools_list:
        if shutil.which(tool) is None:
            missing.append(tool)
    if missing:
        from rich.console import Console
        Console().print(f"[bold red][:x:] Missing system dependencies: {', '.join(missing)}[/bold red]")
        Console().print("[bold yellow][!] Please install these tools before running this feature.[/bold yellow]")
        sys.exit(1)

def print_separator():
    """Print a separator line"""
    print('------------------------------------------------------------')
