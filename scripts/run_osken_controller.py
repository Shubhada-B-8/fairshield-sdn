#!/usr/bin/env python3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# Load FairShield source and retain access to virtualenv dependencies.
sys.path.insert(0, str(ROOT / "src"))
sys.path.append(
    str(ROOT / ".venv/lib/python3.10/site-packages")
)

from os_ken.cmd.manager import main

if __name__ == "__main__":
    main()
