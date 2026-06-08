#!/usr/bin/env python
import os
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent))


def main():
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")
    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
