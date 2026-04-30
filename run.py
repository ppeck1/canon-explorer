#!/usr/bin/env python3
"""CA Explorer v11 — launch script."""
import sys
import os

# Ensure src is importable
sys.path.insert(0, os.path.dirname(__file__))

from src.ui.application import main

if __name__ == "__main__":
    main()
