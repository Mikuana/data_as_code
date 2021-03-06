import gzip
import inspect
import json
import os
import subprocess
import sys
import tarfile
from collections import defaultdict
from collections import namedtuple
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Union, Dict, Type

from data_as_code._step import Step


class Recipe:
    """
    Recipe Class

    This class is responsible for managing the session details involved in
    generation of a data product. It's primarily responsible for setting up
    temporary directories, and moving artifacts to the appropriate location to
    package the results.

    """
    workspace: Union[str, Path]
    _td: TemporaryDirectory

    def __init__(self, destination: Union[str, Path] = '.', keep: Dict[str, bool] = None):
        self.destination = Path(destination).absolute()
        self.keep = defaultdict(lambda: True, **(keep or {}))  # default to True for now

        self._results: Dict[str, Step] = {}
        self._structure = {
            'metadata/': self._prep_metadata,
            self._recipe_file(): self._prep_recipe,
            'requirements.txt': self._prep_requirements
        }

    @classmethod
    def steps(cls) -> Dict[str, Type[Step]]:
        return {
            k: v for k, v in cls.__dict__.items()
            if (isinstance(v, type) and issubclass(v, Step))
        }

    def execute(self):
        self._begin()

        for name, step in self.steps().items():
            if self.keep[step.role] is True:
                step.keep = True

            self._results[name] = step(
                self.workspace.absolute(), self.destination, self._results
            )

        self._end()

    def _begin(self):
        """
        Begin Recipe

        Prepare to start the recipe by determining if the data package
        destination is valid, then opening a workspace for temporary artifacts
        to be stored. The workspace is a temporary directory, which does not
        exist until this method is call.
        """
        self.destination.mkdir(exist_ok=True)
        self._destination_check()
        self._td = TemporaryDirectory()
        self.workspace = Path(self._td.name)

    def _end(self):
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
            if self.keep.get('workspace', False) is False:
                self._td.cleanup()
        finally:
            os.chdir(cwd)

    def _destinations(self):
        x = namedtuple('Destinations', ['archive', 'gzip'])
        return x(
            Path(self.destination, self.destination.name + '.tar'),
            Path(self.destination, self.destination.name + '.tar.gz')
        )

    def _destination_check(self):
        """
        Destination path checks

        Ensure that all non-temporary paths which will be used by the recipe can
        be formed as paths, and that they do not exist (unless allowed by the
        keep settings).
        """
        for v in self._destinations():
            if v.exists() and self.keep.get('existing', False) is True:
                raise FileExistsError(
                    f"{v.as_posix()} exists and `keep.existing == True`."
                    "\nChange the keep.existing setting to False to overwrite."
                )

    def _prepare(self):
        for k, v in self._structure.items():
            # noinspection PyArgumentList
            v(k)

        self._package()

    def _package(self):
        d = self._destinations()
        if self.keep.get('archive', True) is True:
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

    @staticmethod
    def _recipe_file():
        """
        Inspect stack to find filename of calling recipe script

        This is likely to break in a lot of situations
        """
        return Path(inspect.stack()[-1].filename).name

    def _prep_requirements(self, target: str):
        reqs = subprocess.check_output([sys.executable, '-m', 'pip', 'freeze'])
        p = Path(self.destination, target)
        p.write_bytes(reqs)

    def _prep_recipe(self, target: str):
        # TODO: nothing to see here yet
        pass

    def _prep_metadata(self, target: str):
        p = Path(self.destination, target)
        for result in self._results.values():
            if result.keep is True:
                if result.metadata._relative_to:
                    r = Path(result.metadata._relative_to, 'data')
                    pp = Path(p, result.metadata.path.relative_to(r))
                else:
                    pp = Path(p, result.metadata.role, result.metadata._relative_path.name)
                pp.parent.mkdir(parents=True, exist_ok=True)

                d = result.metadata.to_dict()
                j = json.dumps(d, indent=2)
                Path(pp.as_posix() + '.json').write_text(j)
