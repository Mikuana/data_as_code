import difflib
import gzip
import json
import logging
import os
import tarfile
from enum import Enum, auto
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Union, Dict, Type, List

from data_as_code._metadata import validate_metadata
from data_as_code._step import Step

__all__ = ['Recipe', 'Role']

log = logging.getLogger(__name__)


class Role(Enum):
    """
    Step Role

    This enumerator codifies the distinct roles that a step can play in a
    Recipe. The identification of these roles controls behavior related to
    default retention of artifacts, mandatory path designation, and whether a
    step can be skipped when a recipe is executed as a pickup.
    """

    SOURCE = auto()
    """String which identifies source artifacts, codified as an object"""

    INTERMEDIARY = auto()
    """String which identifies intermediary artifacts, codified as an object"""

    PRODUCT = auto()
    """String which identifies product artifacts, codified as an object"""


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
    :param pickup: (optional) controls behavior of execution to work backwards
        for each product, to determine the latest cached Step in their
        ingredients. The end result is that the recipe will attempt to build the
        products using the least number of steps possible.
    """
    keep: List[Role] = [Role.PRODUCT]
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

    pickup = False
    """Controls behavior of execution to work backwards for each Product to
    determine the latest cached Step in their ingredients. 
    """

    _workspace: Union[str, Path]
    _td: TemporaryDirectory
    _results: Dict[str, Step]

    def __init__(
            self, destination: Union[str, Path] = None,
            keep: Union[Role, List[Role]] = None,
            trust_cache: bool = None,
            pickup: bool = None
    ):
        self.destination = Path(destination) if isinstance(destination, str) \
            else destination or Path()

        self.keep = ([keep] if isinstance(keep, str) else keep) or self.keep
        self.trust_cache = self.trust_cache if trust_cache is None else trust_cache
        self.pickup = self.pickup if pickup is None else pickup

        self._step_check()
        self._target = self._get_targets()

    def execute(self):
        """ Execute Recipe """
        self._begin()
        self._results = {}

        for name, step in self._stepper().items():
            self._results[name] = step._execute(self._workspace)

        self._export_metadata()
        self._end()

    def _reproducible(self) -> bool:
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

        :return: a boolean indicator of whether the contents of the package is
            reproducible from scratch.
        """
        with TemporaryDirectory() as container:
            r = self.__class__(container)
            r.execute()
            return self._compare(container)

    @classmethod
    def _check_it(cls, step_name: str, steps: dict) -> set:
        """
        Iterate through ingredients of each step to determine which antecedents
        are required, if the cache is not available.
        """
        required = {step_name}
        s = steps[step_name]
        if s.check_cache() is False:
            for (x, y) in s.collect_ingredients().values():
                required = required.union(cls._check_it(x, steps))
        return required

    def _stepper(self) -> Dict[str, Step]:
        """
        TODO...

        Start with all products of a recipe, and check the cache for valid
        artifacts. If the product is missing a valid artifact in the cache,
        iterate through the ingredients of that product and check their cache
        status, continuing indefinitely until a valid cache exists.

        The idea is to be able to generate a product from the cache with the
        least number of steps possible, potentially even when some of the data
        used in certain steps is completely unavailable at the time of execution
        of the recipe.
        """
        steps = {}
        roles = self._determine_roles()

        for name, step in self._steps().items():
            if step.keep is None:
                step.keep = roles[name] in self.keep
            if step.trust_cache is None:
                step.trust_cache = self.trust_cache

            steps[name] = step(self._target.folder, {k: v.metadata for k, v in steps.items()})

        if self.pickup is True:  # identify pick steps
            pickups = set()
            for k in [k for k, v in roles.items() if v is Role.PRODUCT]:
                pickups = pickups.union(self._check_it(k, steps))

            return {k: v for k, v in steps.items() if k in pickups}
        else:
            return steps

    def _begin(self):
        """
        Begin Recipe

        Prepare to start the recipe by determining if the data package
        destination is valid, then opening a workspace for temporary artifacts
        to be stored. The workspace is a temporary directory, which does not
        exist until this method is call.
        """
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
                        log.warning(f"Removing unexpected file {file}")
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
    def _products(cls) -> Dict[str, Type[Step]]:
        x = [k for k, v in cls._determine_roles().items() if v is Role.PRODUCT]
        return {k: v for k, v in cls._steps().items() if k in x}

    @classmethod
    def _step_check(cls):
        steps = cls._steps()
        for ix, (k, step) in enumerate(steps.items()):
            priors = list(steps.keys())[:ix]
            for x in step.collect_ingredients().values():
                ingredient = x[0]
                msg = (
                    f"Step '{k}' references ingredient '{ingredient}', but"
                    f" there is no preceding Step with that name in the recipe."
                    f" Valid values are: \n {priors}"
                )
                assert ingredient in priors, msg

    @classmethod
    def _determine_roles(cls) -> Dict[str, Role]:
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
        steps = cls._steps()
        ingredient_list = set(
            v[0] for sublist in steps.values()
            for k, v in sublist.collect_ingredients().items()
        )

        roles = {}
        for k, step in steps.items():
            if not step.collect_ingredients():
                roles[k] = Role.SOURCE
            if k not in ingredient_list:
                roles[k] = Role.PRODUCT
            if roles.get(k) is None:
                roles[k] = Role.INTERMEDIARY

        return roles

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
                    p = Path(self._target.metadata, v.codified.path)
                    p.parent.mkdir(parents=True, exist_ok=True)

                    d = v.to_dict()
                    validate_metadata(d)
                    j = json.dumps(d, indent=2)
                    Path(p.as_posix() + '.json').write_text(j)

    def _compare(self, compare_to: Path):
        """
        Compare the contents of two separate folders to verify that they match.
        """
        match = True
        compare_to = Path(compare_to)
        meta_a = {
            x.relative_to(self.destination): x.read_text()
            for x in Path(self.destination, 'metadata').rglob('*')
            if x.is_file()
        }

        meta_b = {
            x.relative_to(compare_to): x.read_text()
            for x in Path(compare_to, 'metadata').rglob('*')
            if x.is_file()
        }

        only_in_b = set(meta_b.keys()).difference(set(meta_a.keys()))
        if only_in_b:
            match = False
            log.info(f"Comparison contains files(s) not in this package:\n")
            for x in only_in_b:
                log.info(' - ' + x.as_posix())

        only_in_a = set(meta_a.keys()).difference(set(meta_b.keys()))
        if only_in_a:
            match = False
            log.info(f"Package contains file(s) not in the comparison:\n")
            for x in only_in_a:
                log.info(' - ' + x.as_posix())

        # difference in intersecting metadata
        for meta in set(meta_a.keys()).intersection(meta_b.keys()):
            log.info(meta.as_posix())

            if meta_a[meta] != meta_b[meta]:
                match = False
                diff = difflib.unified_diff(
                    meta_a[meta], meta_b[meta], 'Package', 'Comparison'
                )
                log.info(diff)

        return match
