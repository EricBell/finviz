import sys
from pathlib import Path

TOOLS_ROOT = Path(__file__).resolve().parent.parent
REPO_ROOT = TOOLS_ROOT.parent

for path in (TOOLS_ROOT, REPO_ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))
