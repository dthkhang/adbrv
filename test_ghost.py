import sys
from adbrv_module.ghost import run_ghost

if len(sys.argv) > 1:
    run_ghost(sys.argv[1])
else:
    print("Please provide a package name")
