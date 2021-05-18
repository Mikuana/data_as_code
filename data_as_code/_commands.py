import argparse
import os
import subprocess
import sys
import venv
from pathlib import Path
from typing import Union

from data_as_code import __version__


def menu(args=None):
    args = _parse_args(args)
    args.func(args)


def _parse_args(args: list = None):
    program = 'data-as-code'
    parser = argparse.ArgumentParser(
        prog=program,
        description="data-as-code utilities"
    )
    parser.add_argument(
        '--version', action='version',
        version=f'{program} version {__version__}'
    )

    commands = parser.add_subparsers(metavar='')

    # init submodule
    cmd_init = commands.add_parser(
        'init', help='initialize a project folder'
    )
    cmd_init.set_defaults(func=initialize_folder)
    cmd_init.add_argument(
        '-d', type=str, default='.',
        help='path to project folder. Defaults to current directory'
    )
    cmd_init.add_argument(
        '-x', action='store_true', default=False,
        help='ignore error if folder or objects already exist'
    )
    cmd_init.add_argument(
        '--git', action='store_true', default=False,
        help='include git artifacts in folder'
    )

    if not len(sys.argv) > 1:  # if no args, print help to stderr
        parser.print_help(sys.stderr)
        sys.exit(1)
    else:
        return parser.parse_args(args)


def initialize_folder(arg: argparse.Namespace):
    _InitializeFolder(path=arg.d, exist_ok=arg.x)


class _InitializeFolder:
    def __init__(self, path: Union[Path, str] = None, exist_ok=False):
        self.wd = Path(path or '.').absolute()
        self.exist_ok = exist_ok

        self.wd.mkdir(exist_ok=True)
        self.make_folder('data/')
        self.make_folder('metadata/')
        self.make_recipe('recipe.py')
        self.make_gitignore('.gitignore')
        self.make_pipenv()

    def make_folder(self, folder):
        Path(self.wd, folder).mkdir(exist_ok=self.exist_ok)

    def make_venv(self, folder):
        venv.create(Path(self.wd, folder))

    def _make_file(self, x: str, txt: str):
        p = Path(self.wd, x)
        if p.exists() and self.exist_ok is False:
            raise FileExistsError(f"{x} already exists in {self.wd}")
        else:
            if isinstance(txt, bytes):
                p.write_bytes(txt)
            else:
                p.write_text(txt)

    def make_recipe(self, file):
        self._make_file(file, 'this is my recipe')

    def make_pipenv(self):
        cwd = os.getcwd()
        try:
            os.chdir(self.wd)
            Path('Pipfile').touch()
            _pipenv_init()
        finally:
            os.chdir(cwd)

    def make_gitignore(self, file):
        patterns = [
            'data/',
        ]
        txt = '\n'.join(patterns)
        self._make_file(file, txt)


def _pip_freeze() -> bytes:
    return subprocess.check_output([sys.executable, '-m', 'pip', 'freeze'])


def _pipenv_init():
    reqs = ['requests', 'tqdm']
    subprocess.check_output([sys.executable, '-m', 'pipenv', 'install'] + reqs)