from PySide6.QtWidgets import QApplication, QDialog
from GUI_Screens.MainScreen import MainScreen
from GUI_Screens.Setup import Setup
import os
import sys
import json
import configparser

def get_config_paths():
    """Returns platform-specific paths for config and setup details."""
    if sys.platform == "win32":
        config_dir = os.path.join(os.getenv("ProgramData"), "Hackintoshify")
    elif sys.platform == "darwin":
        config_dir = "/Library/Application Support/Hackintoshify"
    else:  # Linux
        config_dir = os.path.join(os.path.expanduser("~"), ".config", "hackintoshify")
        
    os.makedirs(config_dir, exist_ok=True)
    
    return {
        "config": os.path.join(config_dir, "config.ini"),
        "setup_details": os.path.join(config_dir, "setup_details.json")
    }

def initialize_files():
    """Creates config and setup files if they don't exist."""
    paths = get_config_paths()
    config_path = paths["config"]
    setup_details_path = paths["setup_details"]

    if not os.path.exists(config_path):
        config = configparser.ConfigParser()
        config['Settings'] = {'theme': 'Dark', 'verbose_logging': 'False'}
        with open(config_path, 'w') as f:
            config.write(f)

    if not os.path.exists(setup_details_path):
        with open(setup_details_path, 'w') as f:
            json.dump({}, f)

def is_first_time():
    """Checks if the setup has been completed."""
    setup_details_path = get_config_paths()["setup_details"]
    if not os.path.exists(setup_details_path):
        return True
        
    with open(setup_details_path, 'r') as f:
        try:
            details = json.load(f)
            return not details.get("setup_complete", False)
        except (json.JSONDecodeError, AttributeError):
            return True

if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    initialize_files()

    if is_first_time():
        setup_screen = Setup()
        # The exec() method shows the dialog modally.
        result = setup_screen.exec()
        
        # QDialog.Accepted means the user saved the setup.
        if result == QDialog.Accepted:
            main_screen = MainScreen()
            main_screen.show()
            sys.exit(app.exec())
        else:
            # If the user closes the setup dialog without saving, exit the app.
            sys.exit(0)
    else:
        main_screen = MainScreen()
        main_screen.show()
        sys.exit(app.exec())