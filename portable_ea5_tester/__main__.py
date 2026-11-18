"""
PyInstaller entry point for portable-ea5-tester.
Launches the GUI control center (menu) in Pro / standalone binary editions,
or forwards CLI arguments in the open-source CLI core repository.

Note (Open-Core design): gui.py is an optional Pro / standalone binary-edition
module intentionally excluded from the open-source CLI repository (not a missing file).
"""

import sys
from portable_ea5_tester.cli import main

if __name__ == "__main__":
    # If no arguments are passed and we are running as a GUI application,
    # default to launching the GUI menu (when gui.py is bundled in Pro/binary builds).
    if len(sys.argv) == 1:
        sys.argv.append("menu")
    main()
