import difflib
import inspect
import json
import logging
import os
from hashlib import md5
from pathlib import Path
from typing import Union, Dict, List, Tuple
from uuid import uuid4

from data_as_code import exceptions as ex
from data_as_code._metadata import Metadata, Codified, Derived, Incidental

log = logging.getLogger(__name__)


class _Ingredient:
    def __init__(self, step_name: str, result_name: str = None):
        self.step_name = step_name
        self.result_name = result_name


def ingredient(step: str, result_name: str = None) -> Path:
    """
    Declare step ingredient

    Use the metadata from a previously executed step as an ingredient for
    another step. This function is a wrapper to allowing passing the results of
    a previous step directly to the next, while still allowing context hints to
    function appropriately.

    The typehint says that the return is a :class:`pathlib.Path` object, but
    that is a lie; the return is actually a semi-private Ingredient class. This
    mismatch is done intentionally to allow all ingredients in a step to be
    identified without first knowing the names of the attributes that they will
    be assigned to. Once the ingredients are captured, the attribute is
    reassigned to the path attribute for the ingredient, allowing the path to
    be called directly from inside the :class:`Step.instructions`

    :param step: the name of the previous step class that is an ingredient in
        this step.
    :param result_name: the name of the particular result from the previous Step
        which will be used as an ingredient in this step. This is only necessary
        if the referenced Step included multiple results; if there is only one,
        this method will select it by default.

    :return: an object built from a semi-private class, which will ultimately be
        converted into a Path object for use in the Step instructions method.
    """
    # noinspection PyTypeChecker
    return _Ingredient(step, result_name)


class _Result:
    def __init__(self, path: Union[str, Path]):
        self.path = Path(path)


def result(path: Union[str, Path]) -> Path:
    """
    Declare step result path

    Prepare a Step for writing to results to an object at the provided relative
    path.

    The typehint says that the return is a :class:`pathlib.Path` object, but
    that is a lie; the return is actually a semi-private Ingredient class. This
    mismatch is done intentionally to allow all ingredients in a step to be
    identified without first knowing the names of the attributes that they will
    be assigned to. Once the ingredients are captured, the attribute is
    reassigned to the path attribute for the ingredient, allowing the path to
    be called directly from inside the :class:`Step.instructions`

    :param path: a Path or path-like string which provides the relative path
        where this result will be written.
    :return: an object built from a semi-private Result class, which will
        ultimately be converted into a Path object for use in the Step
        instructions method.
    """
    # noinspection PyTypeChecker
    return _Result(path)


class Step:
    """
    Base Step Class

    A class which provides a scaffolding to specify a step in the process of
    creating a data product. This class must be declared as part of a Recipe
    class to work correctly, and is not meant to be initialized by the user
    (hence the lack of parameter documentation). Instead, the user is meant to
    provide values for the documented attributes::

        from data_as_code import Step, ingredient, PRODUCT

        class MyStep(Step):
            output = 'my.csv'
            x = ingredient('their_csv')

            def instructions(self):
                 self.output.write_text(self.x.read_text())
    """

    output: Union[_Result, Path] = None
    """The relative path of the output artifact of the step. Optional, unless
    `keep` is set to True. This path must be relative, because the ultimate
    destination of the artifact is controlled by the
    :class:`data_as_code.Recipe`. 
    """

    keep: bool = None
    """Controls whether to keep the artifact produced by this step in the cache.
    If set to `None`, then this step will use the settings that are passed to it
    from the :class:`data_as_code.Recipe`.
    """

    trust_cache: bool = None
    """Controls whether to trust the artifacts which may already exist in the
    cache. If set to `None`, then this step will use the settings that are
    passed to it from the :class:`data_as_code.Recipe`.
    """

    _other_meta: Dict[str, str] = {}
    _data_from_cache: bool
    _ingredients: Dict[str, Metadata] = {}

    metadata: Dict[str, Metadata]

    def __init__(self, destination: Path, antecedents: Dict[str, Dict[str, Metadata]]):
        self._guid = uuid4()
        self.antecedents = antecedents
        self.destination = destination
        self.metadata = self.construct_metadata()

    def construct_metadata(self) -> Dict[str, Metadata]:
        lineage = []
        for v in self.collect_ingredients().values():
            m = self.antecedents[v[0]]
            if v[1] is None:
                if len(m) == 1:
                    lineage.append(next(iter(m.values())))
                else:
                    raise Exception(
                        f"No specified result_name for Step Metadata '{v[0]}', "
                        f"and there are multiple results to choose from. You "
                        f"must provide a result_name in order to use this step "
                        f"as an ingredient."
                    )
            else:
                try:
                    lineage.append(m[v[1]])
                except KeyError:
                    raise KeyError(
                        f"ingredient specified result_name '{v[1]}' for Step "
                        f"Metadata '{v[0]}', but it does not exist."
                    )

        results = self._get_results()
        if not results and self.keep is True:
            raise ex.StepUndefinedOutput(
                f'{self.__class__.__name__} keep is True, but no output is defined'
            )
        elif not results:
            results = [('output', None)]

        metadata = {}
        for (k, v) in results:
            metadata[k] = Metadata(
                codified=Codified(
                    path=v.path if v else None,
                    instructions=self._instruction_digest(),
                    description=self.__doc__,
                    lineage=lineage if lineage else None
                ),
                lineage=lineage if lineage else None
            )
        return metadata

    def instructions(self):
        """
        Step Instructions

        Define the logic for this step which will use the inputs to generate an
        output file, and return the path, or paths, of the output.
        """
        return Exception  # instructions must be redefined on all subclasses

    def _instruction_digest(self) -> str:
        source = inspect.getsource(self.instructions)
        return md5(source.encode('utf-8')).hexdigest()

    def _execute(self, _workspace: Path):
        """
        Execute Step

        This is semi-private, and not meant to be called directly by the user.

        This method performs numerous actions before and after  execution of
        instructions, to first check the cache (and determine if that should be
        used), set up the step workspace, execute the instructions, collect
        metadata, and manage the file system.
        """
        if self.check_cache() is True:
            return self
        else:
            self._workspace = Path(_workspace, self._guid.hex)
            for k, v in self.metadata.items():
                if v.codified.path:
                    p = v.codified.path
                else:
                    p = Path(self._guid.hex, 'output')
                p = Path(self._workspace, p).absolute()

                self.metadata[k].incidental = Incidental(path=p)
                self.__setattr__(k, p)

            self._convert_ingredients()

            original_wd = os.getcwd()
            try:
                self._workspace.mkdir(exist_ok=True)
                os.chdir(self._workspace)

                for v in self.metadata.values():
                    if not v.incidental.path.parent.as_posix() == '.':
                        v.incidental.path.parent.mkdir(parents=True, exist_ok=True)

                if self.instructions():  # execute instructions
                    raise ex.StepNoReturnAllowed()

                for v in self.metadata.values():
                    if not v.incidental.path.is_file():
                        raise ex.StepOutputMustExist()

                self._make_metadata()
            finally:
                os.chdir(original_wd)

        return self

    @classmethod
    def collect_ingredients(cls) -> Dict[str, Tuple[str, Union[str, None]]]:
        """
        Collect Step Ingredients

        Identify all ingredients used by the step, by examining the dictionary
        of the constructed object, and checking if it is a Result class.

        :return: a dictionary of the results, identifying the previous step by
            name, as well as the sub-result (if applicable).
        """
        return {
            k: (v.step_name, v.result_name)
            for k, v in inspect.getmembers(cls, lambda x: isinstance(x, _Ingredient))
        }

    def _convert_ingredients(self):
        """
        Set Input Metadata

        Use the name lineage input defined for the Step class, get the Metadata
        object with the corresponding lineage, and assign the object back to the
        same attribute. This allows explict object assignment and reference in
        the step instructions for files which may not exist until runtime.

        This method must modify self, due to the dynamic naming of attributes.
        """
        for k, v in self.collect_ingredients().items():
            ante = self.antecedents[v[0]]
            if v[1] is None:
                m = list(ante.values())[0]
            else:
                m = ante[v[1]]

            self._ingredients[k] = m
            setattr(self, k, m.incidental.path)

    @classmethod
    def _get_results(cls) -> List[Tuple[str, _Result]]:
        return inspect.getmembers(cls, lambda x: isinstance(x, _Result))

    @classmethod
    def _make_relative_path(cls, p, metadata=False) -> Path:
        if metadata is True:
            return Path('metadata', p.with_suffix(p.suffix + '.json'))
        else:
            return Path('data', p)

    def _make_absolute_path(self, p, metadata=False) -> Path:
        p = Path(self.destination, self._make_relative_path(p, metadata))
        return p.absolute()

    def _make_metadata(self):
        """
        Set Output Metadata

        Use the Path list returned by the Step Instructions to create a list of
        output Metadata for the step. These outputs get added to the Recipe
        artifacts
        """
        for k, v in self.metadata.items():
            if self.keep is True:
                ap = self._make_absolute_path(v.codified.path)
                ap.parent.mkdir(parents=True, exist_ok=True)
                v.incidental.path = v.incidental.path.rename(ap)

            v.derived = Derived(
                checksum=md5(v.incidental.path.read_bytes()).hexdigest(),
                lineage=v.lineage
            )

    def check_cache(self) -> bool:
        """
        Check project data folder for existing file before attempting execution.
        If codified fingerprint in the metadata matches, and the checksum of the
        referenced file matches the metadata checksum, then update the derived
        and incidental metadata to reflect the use of the cache. This allows us
        to skip execution.

        :return: a boolean value indicating whether the metadata was updated
            using the cache. If True, the execution of instructions can be
            skipped.
        """
        log.info(f'Check cache for: {self.__class__.__name__}')
        try:
            assert self.trust_cache is True, f"cache is not trusted"
            cache = {}
            for k, v in self.metadata.items():
                assert v.codified.path is not None, \
                    f"result {k} does not have a codified output path"

                mp = self._make_absolute_path(v.codified.path, metadata=True)
                assert mp.is_file(), f"expected metadata {mp} does not exist"

                meta = Metadata.from_dict(json.loads(mp.read_text()))
                diff = difflib.unified_diff(
                    json.dumps(v.codified.to_dict(), indent=2).split('\n'),
                    json.dumps(meta.codified.to_dict(), indent=2).split('\n'),
                    'Recipe', 'Cached'
                )
                if list(diff):
                    log.debug(
                        f'Difference between step {self.__class__.__name__} codified '
                        f'and metadata cached in {mp.as_posix()}\n' +
                        '\n'.join([line for line in diff])
                    )

                dp = self._make_absolute_path(meta.codified.path)

                assert dp.is_file(), f"expected file {dp} does not exist"
                assert meta.codified.fingerprint() == v.codified.fingerprint(), \
                    "codified fingerprint does not match cache"
                assert meta.derived.checksum == md5(dp.read_bytes()).hexdigest(), \
                    f"checksum does not match file {dp}"
                meta.incidental.path = dp
                meta.incidental.usage = 'cached'
                cache[k] = meta

        except AssertionError as e:
            log.info(f'Ignoring cache: ' + str(e))
            return False

        log.info(
            "Using cache for files: " +
            ','.join([v.codified.path.as_posix() for v in cache.values()])
        )
        for k, v in self.metadata.items():
            self.metadata[k].derived = cache[k].derived
            self.metadata[k].incidental = cache[k].incidental
            self.metadata[k].lineage = cache[k].lineage

        return True
