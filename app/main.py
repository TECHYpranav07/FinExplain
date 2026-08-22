import sys
import importlib.util
from pathlib import Path

# Ensure backend directory is in sys.path
backend_dir = Path(__file__).resolve().parent.parent / "backend"
backend_main_path = backend_dir / "app" / "main.py"

if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

# Dynamically load the FastAPI application from backend/app/main.py
spec = importlib.util.spec_from_file_location("backend_app_main", str(backend_main_path))
backend_main = importlib.util.module_from_spec(spec)
sys.modules["backend_app_main"] = backend_main
spec.loader.exec_module(backend_main)

# Forward the FastAPI application instance and any module-level symbols
app = backend_main.app
