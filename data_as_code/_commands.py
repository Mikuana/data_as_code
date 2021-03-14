import os
import venv
from pathlib import Path
from typing import Union

from data_as_code.misc import _pipenv_init


def initialize_folder(path: Union[Path, str] = '.', exist_ok=False):
    _InitializeFolder(path, exist_ok)


class _InitializeFolder:
    def __init__(self, path: Union[Path, str] = '.', exist_ok=False):
        self.wd = Path(path).absolute()
        self.exist_ok = exist_ok

        # self.make_folder('.')  # create project folder
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


if __name__ == '__main__':
    import shutil

    p = Path(Path.home(), "Downloads", 'yyz')
    if p.is_dir():
        shutil.rmtree(p)

    initialize_folder(p)
