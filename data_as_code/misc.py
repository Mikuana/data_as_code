from enum import Enum, auto
import subprocess
import sys

__all__ = ['Role']


class Role(Enum):
    SOURCE = auto()
    """String which identifies source artifacts, codified as an object"""

    INTERMEDIARY = auto()
    """String which identifies intermediary artifacts, codified as an object"""

    PRODUCT = auto()
    """String which identifies product artifacts, codified as an object"""


def _pip_freeze() -> bytes:
    return subprocess.check_output([sys.executable, '-m', 'pip', 'freeze'])


def _pipenv_init():
    reqs = ['requests', 'tqdm']
    subprocess.check_output([sys.executable, '-m', 'pipenv', 'install'] + reqs)
