import sys
import difflib
import gzip
import json
import os
import tarfile
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Union, Dict, Type, Tuple

from data_as_code._step import Step
from data_as_code.misc import PRODUCT, INTERMEDIARY, SOURCE

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

        self._export_metadata()

        self._end()

    def verify(self):
        """
        Verify package contents

        Execute the recipe in a separate workspace to verify that identical
        contents can be produced.

         - check metadata against all files to verify checksums
           - data without metadata warns
           - data with mismatched checksum warns
         - check metadata against verified files
           - destination metadata without verification match warns
           - verification metadata without destination match warns
           - diff in contents between matching metadata warns

         - optional switch to verify only what exists (from point of last
           available)?

        :return:
        """
        with TemporaryDirectory() as container:
            orig = self.destination
            r = self.__class__(container)
            r.execute()

            new_meta = {
                x.relative_to(container): x.read_text()
                for x in r._target.results(metadata=True)
            }
            orig_meta = {
                x.relative_to(orig): x.read_text()
                for x in Path(self.destination, 'metadata').rglob('*')
                if x.is_file()
            }

            new_diff = set(new_meta.keys()).difference(set(orig_meta.keys()))
            if new_diff:
                print(f"Verification contained new file(s):\n")
                for x in new_diff:
                    print(' - ' + x.as_posix())

            orig_diff = set(orig_meta.keys()).difference(set(new_meta.keys()))
            if orig_diff:
                print(f"Project folder contains unexpected file(s):")
                for x in orig_diff:
                    print(' - ' + x.as_posix())

            print("Comparing metadata contents")
            for meta in set(orig_meta.keys()).intersection(new_meta.keys()):
                s1, s2 = orig_meta[meta], new_meta[meta]
                sys.stdout.writelines(
                    difflib.unified_diff(s1, s2, meta.as_posix(), 'verification')
                )

    def _begin(self):
        """
        Begin Recipe

        Prepare to start the recipe by determining if the data package
        destination is valid, then opening a workspace for temporary artifacts
        to be stored. The workspace is a temporary directory, which does not
        exist until this method is call.
        """
        self._target = self._get_targets()

        for v in self._target.results():
            if v.exists() and False is True:  # TODO: make a control for this
                raise FileExistsError(
                    f"{v.as_posix()} exists and `keep.existing == True`."
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
            # TODO: re-enable when I figure out why this runs so slowly
            # self._package()
            self._td.cleanup()

            # TODO: add a parameter to optionally control removal of unexpected files
            expect = self._target.results() + self._target.results(metadata=True)
            for folder in [self._target.data, self._target.metadata]:
                for file in [x for x in folder.rglob('*') if x.is_file()]:
                    if file not in expect:
                        print(f"Removing unexpected file {file}")
                        file.unlink()
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
            recipe = Path(fold, 'recipe.py')

            archive = Path(fold, fold.name + '.tar')
            gzip = Path(fold, fold.name + '.tar.gz')

            @classmethod
            def results(cls, metadata=False):
                lol = [
                    [x._make_relative_path(z[1].path, metadata) for z in x._get_results()]
                    for x in self._steps().values() if x.keep is True
                ]
                return [Path(fold, item) for sublist in lol for item in sublist]

        return Target

    def _package(self):
        # TODO: re-enable using something other than the keep param
        # if self.keep.get('archive', True) is True:
        with tarfile.open(self._target.archive, "w") as tar:
            for k, v in self._target.results():
                if v.is_file():
                    tar.add(v, v.relative_to(self._target.folder))
                else:
                    for file in v.rglob('*'):
                        tar.add(file, file.relative_to(self._target.folder))

        with gzip.open(self._target.gzip, 'wb') as f_out:
            f_out.write(self._target.archive.read_bytes())
        self._target.archive.unlink()

    def _export_metadata(self):
        for result in self._results.values():
            if result.keep is True:
                for k, v in result.metadata.items():
                    if v._relative_to:
                        r = Path(v._relative_to, 'data')
                        pp = Path(self._target.metadata, v.path.relative_to(r))
                    else:
                        pp = Path(
                            self._target.metadata, v._role,
                            v._relative_path.name
                        )
                    pp.parent.mkdir(parents=True, exist_ok=True)

                    d = v.to_dict()
                    j = json.dumps(d, indent=2)
                    Path(pp.as_posix() + '.json').write_text(j)
