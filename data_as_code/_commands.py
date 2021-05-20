import argparse
import importlib.util
import importlib.util
import inspect
import logging
import os
import subprocess
import sys
import venv
from pathlib import Path
from typing import Type
from typing import Union

from data_as_code import Recipe, Role
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

    parser.add_argument(
        '-v', '--verbose', action='count', dest='verbosity', default=0,
        help="verbose output (repeat for increased verbosity)"
    )

    parser.add_argument(
        '-q', '--quiet', action='store_const', const=-1, default=0,
        dest='verbosity', help="quiet output (show errors only)"
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

    # execution submodule
    cmd_execute = commands.add_parser(
        'execute', help='execute a recipe'
    )
    cmd_execute.set_defaults(func=execute_recipe)
    cmd_execute.add_argument(
        'recipe', help='path to python file containing recipe'
    )
    cmd_execute.add_argument(
        '-d', '--directory', help='recipe folder where artifacts will be stored'
    )
    cmd_execute.add_argument(
        '-ks', '--keep-source', action='store_true',
        help='switch to control whether to keep source artifacts'
    )
    cmd_execute.add_argument(
        '-ki', '--keep-intermediary', action='store_true',
        help='switch to control whether to keep intermediary artifacts'
    )
    cmd_execute.add_argument(
        '-ic', '--ignore-cache', action='store_false',
        help='switch to ignore existing cache when executing recipe'
    )
    cmd_execute.add_argument(
        '-p', '--pickup', action='store_true',
        help='switch to instruct recipe to pickup Steps from latest possible'
    )

    if not len(sys.argv) > 1:  # if no args, print help to stderr
        parser.print_help(sys.stderr)
        sys.exit(1)
    else:
        return parser.parse_args(args)


def initialize_folder(arg: argparse.Namespace):
    setup_logging(arg.verbosity)
    InitializeFolder(path=arg.d, exist_ok=arg.x)


def execute_recipe(arg: argparse.Namespace):
    setup_logging(arg.verbosity)
    rp = Path(arg.recipe).absolute()
    spec = importlib.util.spec_from_file_location("*", rp)
    mod = importlib.util.module_from_spec(spec)
    # noinspection PyUnresolvedReferences
    spec.loader.exec_module(mod)

    recipes = inspect.getmembers(
        mod, lambda x:
        x != Recipe and isinstance(x, type) and issubclass(x, Recipe)
    )
    if len(recipes) == 0:
        raise Exception("no Recipe found in file")
    elif len(recipes) > 1:
        raise Exception("only one Recipe per file is allowed")

    recipe: Type[Recipe] = recipes[0][1]

    keep = [Role.PRODUCT]
    if arg.keep_source:
        keep.append(Role.SOURCE)
    if arg.keep_intermediary:
        keep.append(Role.INTERMEDIARY)

    r = recipe(
        destination=arg.directory, keep=keep, trust_cache=arg.ignore_cache,
        pickup=arg.pickup
    )
    r._execute()


class InitializeFolder:
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
            pipenv_init()
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


def pipenv_init():
    reqs = ['data_as_code']
    subprocess.check_output([sys.executable, '-m', 'pipenv', 'install'] + reqs)


def setup_logging(verbosity):
    base_loglevel = 30
    verbosity = min(verbosity, 2)
    loglevel = base_loglevel - (verbosity * 10)
    logging.basicConfig(level=loglevel, format='%(message)s')
