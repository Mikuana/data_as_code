import inspect
import json
import os
from hashlib import md5
from pathlib import Path
from typing import Union, Dict, List, Tuple
from uuid import uuid4

from data_as_code import exceptions as ex
from data_as_code._metadata import Metadata


class _Ingredient:
    def __init__(self, step_name: str, result_name: str = None):
        self.step_name = step_name
        self.result_name = result_name


def ingredient(step: str, result_name: str = None) -> Path:
    """
    Prepare step ingredient

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
    """
    # noinspection PyTypeChecker
    return _Ingredient(step, result_name)


class _Result:
    def __init__(self, path: Union[str, Path]):
        self.path = Path(path)


def result(path: Union[str, Path]) -> Path:
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

    output: _Result = None
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

    def __init__(self, _destination: Path, _antecedents: Dict[str, 'Step']):

        self._guid = uuid4()
        self._destination = _destination
        self._antecedents = _antecedents

        self._results = self._set_results()
        if not self._results:
            if self.keep is True:
                raise ex.StepUndefinedOutput(
                    "To keep an artifact you must define the output path"
                )
            else:
                self.output = Path(self._guid.hex)
                # noinspection PyTypeChecker
                self._results['output'] = self.output

        self._cache = self._check_cache()

    # def _mock_metadata(self):
    #     lineage = [x for x in self._ingredients.values()]
    #     hxd = md5(candidate.read_bytes()).hexdigest()
    #     m = Metadata(
    #         absolute_path=None, relative_path=rel_path,
    #         checksum_value=hxd, checksum_algorithm='md5',
    #         lineage=lineage, step_description=self.__doc__,
    #         step_instruction=inspect.getsource(self.instructions),
    #         other=self._other_meta
    #     )

    def instructions(self):
        """
        Step Instructions

        Define the logic for this step which will use the inputs to generate an
        output file, and return the path, or paths, of the output.
        """
        return None

    def _execute(self, _workspace: Path):
        """Do the work"""
        self._workspace = Path(_workspace, self._guid.hex)
        self._convert_ingredients()

        if self._cache and self.trust_cache is True:
            self._data_from_cache = True
            print(
                f'Step {self.__class__.__name__} using cache for files\n',
                '\n'.join([f" {x.path.absolute().as_posix()}" for x in self._cache.values()])
            )
            self.metadata = self._cache
            return self
        else:
            self._data_from_cache = False
            original_wd = os.getcwd()
            try:
                self._workspace.mkdir(exist_ok=True)
                os.chdir(self._workspace)

                for k, v in self._results.items():
                    if not v.parent.as_posix() == '.':
                        v.parent.mkdir(parents=True)

                if self.instructions():  # execute instructions
                    raise ex.StepNoReturnAllowed()

                for k, v in self._results.items():
                    if not v.is_file():
                        raise ex.StepOutputMustExist()

                self.metadata = self._make_metadata()
            finally:
                os.chdir(original_wd)
        return self

    @classmethod
    def _collect_ingredients(cls) -> Dict[str, Tuple[str, Union[str, None]]]:
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
        for k, v in self._collect_ingredients().items():
            ante = self._antecedents[v[0]]
            if v[1] is None:
                if len(ante.metadata) == 1:
                    m = list(ante.metadata.values())[0]
                else:
                    raise Exception
            else:
                m = ante.metadata[v[1]]

            self._ingredients[k] = m
            setattr(self, k, m.path)

    def _set_results(self) -> Dict[str, Path]:
        """Set Outputs"""
        results = {}
        for k, v in self._get_results():
            results[k] = v.path
            self.__setattr__(k, v.path)
        return results

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
        p = Path(self._destination, self._make_relative_path(p, metadata))
        return p.absolute()

    def _make_metadata(self) -> Dict[str, Metadata]:
        """
        Set Output Metadata

        Use the Path list returned by the Step Instructions to create a list of
        output Metadata for the step. These outputs get added to the Recipe
        artifacts
        """
        meta_dict = {}
        for k, v in self._results.items():
            p = Path(self._workspace, v)
            hxd = md5(p.read_bytes()).hexdigest()

            if self.keep is True:
                rp = self._make_relative_path(v)
                ap = self._make_absolute_path(v)
                ap.parent.mkdir(parents=True, exist_ok=True)
                p.rename(ap)
            else:
                ap = p
                rp = None

            meta_dict[k] = Metadata(
                absolute_path=ap, relative_path=rp,
                checksum_value=hxd, checksum_algorithm='md5',
                lineage=[x for x in self._ingredients.values()],
                relative_to=self._destination.absolute(),
                other=self._other_meta, step_description=self.__class__.__doc__,
                step_instruction=inspect.getsource(self.instructions),
            )
        for k, v in meta_dict.items():
            setattr(self, k, v)
        return meta_dict

    def _check_cache(self) -> Union[Dict[str, Metadata], None]:
        """
        Check project data folder for existing file before attempting to recreate.
        If fingerprint in the metadata matches the mocked fingerprint, use the
        existing metadata without executing instructions.
        """
        cache = {}
        for k, v in self._results.items():
            mp = self._make_absolute_path(v, metadata=True)
            if mp.is_file():
                meta = from_dictionary(
                    **json.loads(mp.read_text()),
                    relative_to=self._destination.as_posix()
                )
                dp = meta.path.absolute()
                if dp.is_file():
                    try:
                        assert meta.prep_fingerprint == self._mock_fingerprint(dp, meta._relative_path)
                        assert meta.checksum_value == md5(dp.read_bytes()).hexdigest()
                        cache[k] = meta
                    except AssertionError:
                        return
        return cache

    def _mock_fingerprint(self, candidate: Path, rel_path: Path) -> str:
        """ Generate a mock metadata fingerprint """
        lineage = [x for x in self._ingredients.values()]
        hxd = md5(candidate.read_bytes()).hexdigest()
        m = Metadata(
            absolute_path=None, relative_path=rel_path,
            checksum_value=hxd, checksum_algorithm='md5',
            lineage=lineage, step_description=self.__doc__,
            step_instruction=inspect.getsource(self.instructions),
            other=self._other_meta
        )
        return m.fingerprint
