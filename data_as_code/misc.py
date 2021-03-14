import subprocess
import sys

__all__ = [
    'SOURCE', 'INTERMEDIARY', 'PRODUCT'
]

SOURCE = 'source'
"""String which identifies source artifacts, codified as an object"""

INTERMEDIARY = 'intermediary'
"""String which identifies intermediary artifacts, codified as an object"""

PRODUCT = 'product'
"""String which identifies product artifacts, codified as an object"""


def _pip_freeze() -> bytes:
    return subprocess.check_output([sys.executable, '-m', 'pip', 'freeze'])
