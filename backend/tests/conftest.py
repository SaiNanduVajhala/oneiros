import os
import sys

# Ensure backend folder is in path
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if backend_dir not in sys.path:
    sys.path.append(backend_dir)

# Override DATABASE_PATH environment variable for tests to use a dedicated test database file
os.environ["DATABASE_PATH"] = os.path.join(backend_dir, "data", "test_brain.db")
