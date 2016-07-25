from __future__ import print_function
import sys


def err_print(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)
