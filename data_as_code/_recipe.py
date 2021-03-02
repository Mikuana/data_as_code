import gzip
import inspect
import json
import os
import shutil
import subprocess
import sys
import tarfile
from collections import namedtuple
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Union, List

from data_as_code._metadata import Metadata


class Keep:
    def __init__(self, **kwargs: bool):
        # TODO: add keep options for sources and intermediaries
        self.product = kwargs.pop('product', True)
        self.metadata = kwargs.pop('metadata', True)
        self.recipe = kwargs.pop('recipe', True)
        self.archive = kwargs.pop('archive', True)
        self.destination = kwargs.pop('destination', True)
        self.artifacts = kwargs.pop('artifacts', False)
        self.workspace = kwargs.pop('workspace', False)
        self.existing = kwargs.pop('existing', False)
        self.sources = kwargs.pop('sources', False)
        self.intermediaries = kwargs.pop('intermediaries', False)

        if kwargs:
            raise KeyError(f"Received unexpected keywords {list(kwargs.keys())}")


class Recipe:
    """
    Recipe Class

    This class is responsible for managing the session details involved in
    generation of a data product. It's primarily responsible for setting up
    temporary directories, and moving artifacts to the appropriate location to
    package the results.

    :param keep: (optional) controls the behavior of the recipe, determining
        which artifacts should be preserved after the recipe completes, and
        which should be removed from the file-system. This parameter is modified
        by passing a :class:`~data_as_code.recipe.Keep` object.
    """
    workspace: Union[str, Path]
    _td: TemporaryDirectory

    def __init__(self, keep=Keep()):
        self.destination = Path().absolute()
        self.sources: List[Metadata] = []
        self.intermediaries: List[Metadata] = []
        self.products: List[Metadata] = []
        self.keep = keep

        self._structure = {
            'metadata/': self._prep_metadata,
            self._recipe_file(): self._prep_recipe,
            'requirements.txt': self._prep_requirements
        }

    @staticmethod
    def _recipe_file():
        """
        Inspect stack to find filename of calling recipe script

        This is likely to break in a lot of situations
        """
        return Path(inspect.stack()[-1].filename).name

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
        cwd = os.getcwd()
        try:
            os.chdir(self.destination)
            self._prepare()
            if self.keep.workspace is False:
                self._td.cleanup()
        finally:
            os.chdir(cwd)

    def _destinations(self):
        x = namedtuple('Destinations', ['archive', 'gzip'])
        return x(
            Path(self.destination.absolute().name + '.tar'),
            Path(self.destination.absolute().name + '.tar.gz')
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

    def _prepare(self):
        for k, v in self._structure.items():
            # noinspection PyArgumentList
            v(k)

        self._package()

    def _package(self):
        d = self._destinations()
        if self.keep.archive is True:
            with tarfile.open(d.archive, "w") as tar:
                for x in self._structure:
                    p = Path(self.destination, x)
                    if p.is_file():
                        tar.add(p, p.relative_to(self.destination))
                    else:
                        for file in p.rglob('*'):
                            tar.add(file, file.relative_to(self.destination))

            with gzip.open(d.gzip, 'wb') as f_out:
                f_out.write(d.archive.read_bytes())
            d.archive.unlink()

        if self.keep.destination is False:
            shutil.rmtree(self.destination)

    def _prep_requirements(self, target: str):
        reqs = subprocess.check_output([sys.executable, '-m', 'pip', 'freeze'])
        p = Path(self.destination, target)
        p.write_bytes(reqs)

    def _prep_recipe(self, target: str):
        # TODO: nothing to see here yet
        pass

    def _package_data_prep(self, target: str):
        p = Path(self.destination, target)
        z = (
            (self.sources, 'source'),
            (self.intermediaries, 'intermediary'),
            (self.products, 'product')
        )
        for artifacts, sub in z:
            for artifact in artifacts:
                if artifact._relative_to:
                    pp = Path(p, sub, artifact._relative_path)
                else:
                    pp = Path(p, sub, artifact._relative_path.name)
                pp.parent.mkdir(parents=True, exist_ok=True)
                yield artifact, pp

    def _prep_metadata(self, target: str):
        for prod, pp in self._package_data_prep(target):
            d = prod.to_dict()
            j = json.dumps(d, indent=2)
            Path(pp.as_posix() + '.json').write_text(j)
