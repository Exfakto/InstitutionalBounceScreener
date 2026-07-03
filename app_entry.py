"""
PyInstaller-compatible GUI entry point.

Build tools should target this module so packaged execution and dev execution use
the same application startup path.
"""

from main import main


if __name__ == "__main__":
    main()
