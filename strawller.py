#!/usr/bin/env python3
"""Top-level launcher: python strawller.py"""

import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from strawller.main import main

if __name__ == "__main__":
    sys.exit(main())
