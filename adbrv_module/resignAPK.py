"""
APK resigning tools using uber-apk-signer
"""

import os
import subprocess
import sys
from .utils import print_error, print_info

def resign_apk(resign_args):
    """
    Resign APK file using integrated uber-apk-signer
    """
    jar_path = os.path.join(os.path.dirname(__file__), 'tools', 'uber-apk-signer-1.3.0.jar')
    if not os.path.isfile(jar_path):
        print_error(f"uber-apk-signer jar not found at {jar_path}")
        sys.exit(1)
        
    cmd = ['java', '-jar', jar_path] + resign_args
    try:
        result = subprocess.run(cmd)
        sys.exit(result.returncode)
    except Exception as e:
        print_error(f"Error running uber-apk-signer: {e}")
        sys.exit(1)
