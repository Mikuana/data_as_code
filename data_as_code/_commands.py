import sys
import argparse
import os
import venv
from pathlib import Path
from typing import Union

from data_as_code.misc import _pipenv_init


def menu(args=None):
    args = _parse_args(args)
    args.func(args)


def _parse_args(args: list = None):
    parser = argparse.ArgumentParser(
        prog='data_as_code',
        description="Data-as-Code command line actions"
    )
    subparsers = parser.add_subparsers(
        title='commands', description="", required=True, metavar=''
    )

    parser_init = subparsers.add_parser(
        'init', help='initialize a project folder'
    )
    parser_init.add_argument(
        '-d', type=str,
        help='the path to the directory that should be initialized'
    )
    parser_init.add_argument(
        '--git', action='store_true',
        help='include git artifacts in folder'
    )
    parser_init.set_defaults(func=initialize_folder)

    return parser.parse_args(args)


def initialize_folder(arg: argparse.Namespace):
    _InitializeFolder(path=arg.d)


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
        if p.exists():
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
