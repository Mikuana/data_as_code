import gzip
import inspect
import json
import os
import tarfile
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Union, Dict, Type, Tuple

from data_as_code._step import Step
from data_as_code.misc import PRODUCT, INTERMEDIARY, SOURCE, _pip_freeze

__all__ = ['Recipe']


class Recipe:
    """
    Recipe

    Responsible for managing the session details involved in a series of Steps
    that generate data artifacts. This Recipe acts both as a container of
    individual steps, and an orchestrator to ensure appropriate conditions are
    met. Recipe initially creates all artifacts in temporary directories,
    then moves the artifacts to the destination, according to the various
    settings that control the retention of artifacts.

    :param destination: the path to the project folder where any artifacts that
        should be retained by the recipe will be output. Defaults to the
        "current" directory on initialization.
    :param keep: (optional) controls whether to keep source, intermediate, and
        final product artifacts. Values set here are overwritten by those set in
        individual Step settings.
    :param trust_cache: (optional) controls whether to trust the artifacts which
        may already exist in the destination folder. If set to `true` and the
        anticipated fingerprint of the metadata matches the Step, then the Step
        will skip execution and return the cached data and metadata instead.
        Values set here are overwritten by those set in individual Step
        settings.
    """
    keep: Dict[str, bool] = (PRODUCT,)
    """Controls whether to keep source, intermediate, and final product
    artifacts. Values set here can be overwritten by the `keep`
    parameter during construction, or by those set in individual Step settings.
    Defaults to retaining all products. 
    """

    trust_cache = True
    """Controls whether to trust the artifacts which may already exist in the
    destination folder. If set to `true` and the anticipated fingerprint of the
    metadata matches the Step, then the Step will skip execution and return the
    cached data and metadata instead. Values set here can be overwritten by the
    `trust_cache` parameter during construction, or by those set in individual
    Step settings.
    """

    _workspace: Union[str, Path]
    _td: TemporaryDirectory
    _results: Dict[str, Step]

    def __init__(
            self, destination: Union[str, Path] = '.',
            keep: Union[str, Tuple[str]] = None, trust_cache: bool = None
    ):
        self.destination = Path(destination)
        self.keep = (keep if isinstance(keep, tuple) else (keep,)) or self.keep
        self.trust_cache = trust_cache or self.trust_cache

        self._step_check()
        self._assign_roles()

    def execute(self):
        self._begin()

        self._results = {}
        for name, step in self._steps().items():
            if step.keep is None:
                step.keep = step._role in self.keep
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
        self._target = self._get_targets()

        # TODO: re-enable this, but not using the keep param
        # for k, v in self._target.manifest():
        #     if v.exists() and self.keep.get('existing', False) is True:
        #         raise FileExistsError(
        #             f"{k} '{v.as_posix()}' exists and `keep.existing == True`."
        #             "\nChange the keep.existing setting to False to overwrite."
        #         )

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
            # TODO: re-enable when I figure out why this runs so slowly
            # self._package()
            # TODO: re-enable using something other than the keep param
            # if self.keep.get('workspace', False) is False:
            self._td.cleanup()
        finally:
            os.chdir(cwd)

    @classmethod
    def _steps(cls) -> Dict[str, Type[Step]]:
        return {
            k: v for k, v in cls.__dict__.items()
            if (isinstance(v, type) and issubclass(v, Step))
        }

    @classmethod
    def _step_check(cls):
        steps = cls._steps()
        for ix, (k, step) in enumerate(steps.items()):
            priors = list(steps.keys())[:ix]
            for ingredient in step._get_ingredients():
                ingredient_name = ingredient[1].step_name
                msg = (
                    f"Step '{k}' references ingredient '{ingredient_name}', but"
                    f" there is no preceding Step with that name in the recipe."
                    f" Valid values are: \n {priors}"
                )
                assert ingredient_name in priors, msg

    def _assign_roles(self):
        """
        Role assigner

        Determines the role that a Step result plays by looking at the links to
        other steps, then assigning that role.

        The logic breaks down this way:
         - if a Step has no ingredients, it is a source
         - if a Step is not an ingredient for any other step, then it is a
            product (overwriting previous Source assignment if applicable)
         - if a Step is neither a source or product, then it is an intermediary
        """
        steps = self._steps()
        ingredient_list = set(
            ingredient[1].step_name for sublist in steps.values()
            for ingredient in sublist._get_ingredients()
        )

        for k, step in steps.items():
            role = None
            if not step._get_ingredients():
                role = SOURCE
            if k not in ingredient_list:
                role = PRODUCT
            if role is None:
                role = INTERMEDIARY

            setattr(getattr(self, k), '_role', role)

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
                # TODO: get complete list of output data and metadata files
                # from steps so that manifest can be explicit instead of forcing
                # the package step to use rglob.
                return inspect.getmembers(Target, lambda x: isinstance(x, Path))

        return Target

    def _package(self):
        # TODO: re-enable using something other than the keep param
        # if self.keep.get('archive', True) is True:
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
        self._target.reqs.write_bytes(_pip_freeze())

    def _export_metadata(self):
        for result in self._results.values():
            if result.keep is True:
                if result.metadata._relative_to:
                    r = Path(result.metadata._relative_to, 'data')
                    pp = Path(
                        self._target.metadata,
                        result.metadata.path.relative_to(r)
                    )
                else:
                    pp = Path(
                        self._target.metadata, result.metadata._role,
                        result.metadata._relative_path.name
                    )
                pp.parent.mkdir(parents=True, exist_ok=True)

                d = result.metadata.to_dict()
                j = json.dumps(d, indent=2)
                Path(pp.as_posix() + '.json').write_text(j)
