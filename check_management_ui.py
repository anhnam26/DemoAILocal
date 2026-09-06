"""Current workspace UI regression entry point."""
from pathlib import Path
import runpy
runpy.run_path(str(Path(__file__).with_name("check_workspace_ui.py")),run_name="__main__")
