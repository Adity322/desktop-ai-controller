import os
import platform
import subprocess

def open_file(path):
    system = platform.system()

    if system == "Darwin":  # macOS
        # Force Preview.app
        subprocess.run(["open", "-a", "Preview", path])

    elif system == "Windows":
        os.startfile(path)

    else:  # Linux
        subprocess.run(["xdg-open", path])
