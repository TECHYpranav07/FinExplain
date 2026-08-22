import sys
from pathlib import Path

# Ensure backend directory is in sys.path
backend_dir = Path(__file__).resolve().parent.parent / "backend"
backend_app_dir = backend_dir / "app"

if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

# Extend package search path so submodules (app.core, app.api, etc.) load from backend/app
if backend_app_dir.exists() and str(backend_app_dir) not in __path__:
    __path__.append(str(backend_app_dir))
