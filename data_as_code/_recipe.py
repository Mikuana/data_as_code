import gzip
import inspect
import json
import os
import subprocess
import sys
import tarfile
import warnings
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Union, Dict, Type

from data_as_code._step import Step
from data_as_code.misc import product


class Recipe:
    """
    Recipe Class

    This class is responsible for managing the session details involved in
    generation of a data product. It's primarily responsible for setting up
    temporary directories, and moving artifacts to the appropriate location to
    package the results.
    """
    keep: Dict[str, bool] = {product: True}
    trust_cache = True

    _workspace: Union[str, Path]
    _td: TemporaryDirectory
    _results: Dict[str, Step]

    def __init__(self, destination: Union[str, Path] = '.', keep: Dict[str, bool] = None, trust_cache: bool = None):
        self.destination = Path(destination)
        self.keep = keep or self.keep
        self.trust_cache = trust_cache or self.trust_cache

        self._target = self._get_targets()

    @classmethod
    def steps(cls) -> Dict[str, Type[Step]]:
        return {
            k: v for k, v in cls.__dict__.items()
            if (isinstance(v, type) and issubclass(v, Step))
        }

    def execute(self):
        self._begin()

        self._results = {}
        for name, step in self.steps().items():
            if step.keep is None:
                step.keep = self.keep.get(step.role, False)
            if step.trust_cache is None:
                step.trust_cache = self.trust_cache

            self._results[name] = step(
                self._workspace.absolute(), self._target.folder, self._results
            )

        self._freeze_recipe()
        self._freeze_requirements()
        self._export_metadata()

        self._end()

    def _begin(self):
        """
        Begin Recipe

        Prepare to start the recipe by determining if the data package
        destination is valid, then opening a workspace for temporary artifacts
        to be stored. The workspace is a temporary directory, which does not
        exist until this method is call.
        """
        for k, v in self._target.manifest():
            if v.exists() and self.keep.get('existing', False) is True:
                raise FileExistsError(
                    f"{k} '{v.as_posix()}' exists and `keep.existing == True`."
                    "\nChange the keep.existing setting to False to overwrite."
                )

        self._target.folder.mkdir(exist_ok=True)
        self._td = TemporaryDirectory()
        self._workspace = Path(self._td.name)

    def _end(self):
        """
        End Recipe

        Complete the recipe by building the data package from the identified
        products, then removing the workspace (unless otherwise instructed in
        the keep parameter).
        """
        cwd = os.getcwd()
        try:
            os.chdir(self._target.folder)
            self._package()
            if self.keep.get('workspace', False) is False:
                self._td.cleanup()
        finally:
            os.chdir(cwd)

    def _get_targets(self):
        fold = self.destination.absolute()

        class Target:
            folder = fold
            data = Path(fold, 'data')
            metadata = Path(fold, 'metadata')
            reqs = Path(fold, 'requirements.txt')
            recipe = Path(fold, 'recipe.py')  # TODO: this won't work long-term

            archive = Path(fold, fold.name + '.tar')
            gzip = Path(fold, fold.name + '.tar.gz')

            @classmethod
            def manifest(cls):
                return inspect.getmembers(Target, lambda x: isinstance(x, Path))

        return Target

    def _package(self):
        if self.keep.get('archive', True) is True:
            with tarfile.open(self._target.archive, "w") as tar:
                for k, v in self._target.manifest():
                    if v.is_file():
                        tar.add(v, v.relative_to(self._target.folder))
                    else:
                        for file in v.rglob('*'):
                            tar.add(file, file.relative_to(self._target.folder))

            with gzip.open(self._target.gzip, 'wb') as f_out:
                f_out.write(self._target.archive.read_bytes())
            self._target.archive.unlink()

    def _freeze_requirements(self):
        reqs = subprocess.check_output([sys.executable, '-m', 'pip', 'freeze'])
        self._target.reqs.write_bytes(reqs)

    # noinspection PyMethodMayBeStatic
    def _freeze_recipe(self):  # TODO: should do this
        warnings.warn('Recipe freeze does not do anything yet')
        pass

    def _export_metadata(self):
        for result in self._results.values():
            if result.keep is True:
                if result.metadata._relative_to:
                    r = Path(result.metadata._relative_to, 'data')
                    pp = Path(self._target.metadata, result.metadata.path.relative_to(r))
                else:
                    pp = Path(self._target.metadata, result.metadata.role, result.metadata._relative_path.name)
                pp.parent.mkdir(parents=True, exist_ok=True)

                d = result.metadata.to_dict()
                j = json.dumps(d, indent=2)
                Path(pp.as_posix() + '.json').write_text(j)
