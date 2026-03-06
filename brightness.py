import os
import platform

def increase_brightness():
    if platform.system() == "Darwin":  # macOS
        os.system('osascript -e \'tell application "System Events" to key code 144\'')
    else:
        print("Brightness control not configured for this OS")

def decrease_brightness():
    if platform.system() == "Darwin":
        os.system('osascript -e \'tell application "System Events" to key code 145\'')
    else:
        print("Brightness control not configured for this OS")