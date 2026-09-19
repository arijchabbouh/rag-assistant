import os
from pathlib import Path

# Reads the key from a file named ".env" in the project folder, so it works in any terminal.
# A real environment variable, if you have one, takes priority.
env_file = Path(__file__).parent / ".env"
if env_file.exists():
    for line in env_file.read_text(encoding="utf-8-sig").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            name, value = line.split("=", 1)
            os.environ.setdefault(name.strip(), value.strip().strip('"').strip("'"))