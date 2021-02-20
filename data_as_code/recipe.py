import gzip
import json
import shutil
import subprocess
import sys
import tarfile
from collections import namedtuple
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Union, List

from data_as_code.metadata import Metadata


class Keep:
    def __init__(self, **kwargs: bool):
        self.product = kwargs.pop('product', True)
        self.metadata = kwargs.pop('metadata', True)
        self.recipe = kwargs.pop('recipe', True)
        self.archive = kwargs.pop('archive', True)
        self.destination = kwargs.pop('destination', False)
        self.artifacts = kwargs.pop('artifacts', False)
        self.workspace = kwargs.pop('workspace', False)
        self.existing = kwargs.pop('existing', True)

        if kwargs:
            raise KeyError(f"Received unexpected keywords {list(kwargs.keys())}")


class Recipe:
    """
    Recipe Class

    This class is responsible for managing the session details involved in
    generation of a data product. It's primarily responsible for setting up
    temporary directories, and moving artifacts to the appropriate location to
    package the results.

    :param destination: (optional) the folder path where the data package
        produced by the recipe will be output. If archiving is enabled in the
        keep parameter, the name of this folder will also dictate the archive
        name.
    :param keep: (optional) controls the behavior of the recipe, determining
        which artifacts should be preserved after the recipe completes, and
        which should be removed from the file-system.
    """
    workspace: Union[str, Path]
    _td: TemporaryDirectory

    def __init__(self, destination: Union[str, Path] = '.', keep=Keep()):
        self.destination = Path(destination)
        self.products: List[Metadata] = []
        self.keep = keep

    def begin(self):
        """
        Begin Recipe

        Prepare to start the recipe by determining if the data package
        destination is valid, then opening a workspace for temporary artifacts
        to be stored. The workspace is a temporary directory, which does not
        exist until this method is call.
        """
        self._destination_check()
        if self.keep.workspace is False:
            self._td = TemporaryDirectory()
            self.workspace = Path(self._td.name)
        else:
            self.workspace = self.destination

    def end(self):
        """
        End Recipe

        Complete the recipe by building the data package from the identified
        products, then removing the workspace (unless otherwise instructed in
        the keep parameter).
        """
        self._package()

        if self.keep.workspace is False:
            self._td.cleanup()

    def _destinations(self):
        x = namedtuple('Destinations', ['directory', 'archive', 'gzip'])
        return x(
            self.destination,
            Path(self.destination.as_posix() + '.tar'),
            Path(self.destination.as_posix() + '.tar.gz')
        )

    def _destination_check(self):
        """
        Destination path checks

        Ensure that all non-temporary paths which will be used by the recipe can
        be formed as paths, and that they do not exist (unless allowed by the
        keep settings).
        """
        for v in self._destinations():
            if v.exists() and self.keep.existing is True:
                raise FileExistsError(
                    f"{v.as_posix()} exists and `keep.existing == True`."
                    "\nChange the keep.existing setting to False to overwrite."
                )

    def __enter__(self):
        self.begin()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.end()

    def _package(self):
        structure = {
            'env/requirements.txt': self._package_env,
            'data/': self._package_data,
            'metadata/': self._package_metadata,
            'recipe.py': self._package_recipe
        }

        d = self._destinations()
        if d.directory.exists():
            shutil.rmtree(d.directory)
        d.directory.mkdir()

        for k, v in structure.items():
            # noinspection PyArgumentList
            v(k)

        if self.keep.archive is True:
            with tarfile.open(d.archive, "w") as tar:
                for file in self.destination.rglob('*'):
                    tar.add(file, file.relative_to(self.destination))

            with gzip.open(d.gzip, 'wb') as f_out:
                f_out.write(d.archive.read_bytes())
            d.archive.unlink()

        if self.keep.destination is False:
            shutil.rmtree(self.destination)

    def _package_env(self, target: str):
        reqs = subprocess.check_output([sys.executable, '-m', 'pip', 'freeze'])
        p = Path(self.destination, target)
        p.parent.mkdir(exist_ok=True, parents=True)
        p.write_bytes(reqs)

    def _package_recipe(self, target: str):
        Path(self.destination, target).write_bytes(Path(__file__).read_bytes())

    def _package_data_prep(self, target: str):
        p = Path(self.destination, target)
        for prod in self.products:
            pp = Path(p, prod.path.relative_to(prod._relative_to))
            pp.parent.mkdir(parents=True, exist_ok=True)
            yield prod, pp

    def _package_data(self, target: str):
        for prod, pp in self._package_data_prep(target):
            shutil.copy(prod.path, pp)

    def _package_metadata(self, target: str):
        for prod, pp in self._package_data_prep(target):
            d = prod.to_dict()
            j = json.dumps(d, indent=2)
            Path(pp.as_posix() + '.json').write_text(j)
