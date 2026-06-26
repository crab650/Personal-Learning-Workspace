from pathlib import Path
import sys


PROJECT_HOME = Path(__file__).resolve().parent
project_home_text = str(PROJECT_HOME)
if project_home_text in sys.path:
    sys.path.remove(project_home_text)
sys.path.insert(0, project_home_text)

from app import create_app


app = create_app()
