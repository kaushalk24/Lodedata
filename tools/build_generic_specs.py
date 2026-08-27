#!/usr/bin/env python3
"""Write the bundled generic equipment library into ``specs/generic``."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from lode.library import generic750

OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                   "specs", "generic")


def main() -> None:
    spec_set = generic750()
    written = spec_set.save_dir(OUT)
    for kind, path in sorted(written.items()):
        print(f"  {kind:<12} {os.path.relpath(path)}")
    warnings = spec_set.validate()
    if warnings:
        print("\nwarnings:")
        for warning in warnings:
            print(f"  - {warning}")
    else:
        print("\nspec set validates cleanly")


if __name__ == "__main__":
    main()
