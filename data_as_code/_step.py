import inspect
import json
import os
from datetime import datetime
from hashlib import md5
from pathlib import Path
from typing import Union, Dict, List, Tuple
from uuid import uuid4

from data_as_code import exceptions as ex
from data_as_code._metadata import Metadata, from_dictionary
from data_as_code.misc import INTERMEDIARY


class _Ingredient:
    def __init__(self, step_name: str):
        self.step_name = step_name


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
            role = PRODUCT

            def instructions(self):
                 self.output.write_text(self.x.read_text())
    """

    output: Union[Path, str] = None
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

    _role: str = INTERMEDIARY
    """The type of role that this step plays in the :class:`data_as_code.Recipe`.
    This influences a number of different processes, such as keep settings,
    name requirements, and pathing of retained artifacts. Should be set using
    one of the constant values: :const:`data_as_code.misc.SOURCE`,
    :const:`data_as_code.misc.INTERMEDIARY`, :const:`data_as_code.misc.PRODUCT`
    """

    _other_meta: Dict[str, str] = {}
    _data_from_cache: bool

    def __init__(
            self, _workspace: Path, _destination: Path,
            _antecedents: Dict[str, 'Step']
    ):

        self._timing = {'started': datetime.utcnow()}
        self._guid = uuid4()
        self._workspace = Path(_workspace, self._guid.hex)
        self._destination = _destination
        self._antecedents = _antecedents

        self._ingredients = self._set_ingredients()

        if self.output is None and self.keep is True:
            raise ex.StepUndefinedOutput(
                "To keep an artifact you must define the output path"
            )
        elif self.output:
            self.output = Path(self.output)
        else:
            self.output = Path(self._guid.hex)

        self.metadata = self._execute()
        self._timing['completed'] = datetime.utcnow()

    def instructions(self):
        """
        Step Instructions

        Define the logic for this step which will use the inputs to generate an
        output file, and return the path, or paths, of the output.
        """
        return None

    def _execute(self) -> Metadata:
        """Do the work"""
        cached = self._check_cache()
        if cached and self.trust_cache is True:
            self._data_from_cache = True
            print(f"Using cache for {self._role} '{self.output}'")
            return cached
        else:
            self._data_from_cache = False
            original_wd = os.getcwd()
            try:
                self._workspace.mkdir(exist_ok=True)
                os.chdir(self._workspace)
                if not self.output.parent.as_posix() == '.':
                    self.output.parent.mkdir(parents=True)

                if self.instructions():
                    raise ex.StepNoReturnAllowed()

                if not self.output.exists():
                    raise ex.StepOutputMustExist()

                return self._make_metadata()
            finally:
                os.chdir(original_wd)

    def _set_ingredients(self):
        """
        Set Input Metadata

        Use the name lineage input defined for the Step class, get the Metadata
        object with the corresponding lineage, and assign the object back to the
        same attribute. This allows explict object assignment and reference in
        the step instructions for files which may not exist until runtime.

        This method must modify self, due to the dynamic naming of attributes.
        """
        ingredients = []
        for k, v in self._get_ingredients():
            ingredients.append(self._antecedents[v.step_name].metadata)
            self.__setattr__(k, self._antecedents[v.step_name].metadata.path)
        return ingredients

    @classmethod
    def _get_ingredients(cls) -> List[Tuple[str, _Ingredient]]:
        return inspect.getmembers(cls, lambda x: isinstance(x, _Ingredient))

    def _make_metadata(self) -> Union[Metadata, Dict[str, Metadata]]:
        """
        Set Output Metadata

        Use the Path list returned by the Step Instructions to create a list of
        output Metadata for the step. These outputs get added to the Recipe
        artifacts
        """
        p = Path(self._workspace, self.output)

        hxd = md5(p.read_bytes()).hexdigest()

        ap, rp = None, None
        if self.output.name == self._guid.hex:
            ap = p
        elif self.keep is True:
            rp = Path('data', self._role, self.output)
            ap = Path(self._destination, rp).absolute()
            ap.parent.mkdir(parents=True, exist_ok=True)
            p.rename(ap)

        return Metadata(
            absolute_path=ap, relative_path=rp,
            checksum_value=hxd, checksum_algorithm='md5',
            lineage=[x for x in self._ingredients],
            role=self._role, relative_to=self._destination.absolute(),
            other=self._other_meta, step_description=self.__class__.__doc__,
            step_instruction=inspect.getsource(self.instructions),
            timing=self._timing
        )

    def _check_cache(self) -> Union[Metadata, None]:
        """
        Check project data folder for existing file before attempting to recreate.
        If fingerprint in the metadata matches the mocked fingerprint, use the
        existing metadata without executing instructions.
        """
        mp = Path(self._destination, 'metadata', self._role, f'{self.output}.json')
        if mp.is_file():
            meta = from_dictionary(
                **json.loads(mp.read_text()),
                relative_to=self._destination.as_posix()
            )
            dp = meta.path
            if dp.is_file():
                try:
                    assert meta.fingerprint == self._mock_fingerprint(dp)
                    assert meta.checksum_value == md5(dp.read_bytes()).hexdigest()
                    return meta
                except AssertionError:
                    return

    def _mock_fingerprint(self, candidate: Path) -> str:
        """ Generate a mock metadata fingerprint """
        lineage = [x for x in self._ingredients]
        hxd = md5(candidate.read_bytes()).hexdigest()
        m = Metadata(
            absolute_path=None, relative_path=candidate,
            checksum_value=hxd, checksum_algorithm='md5',
            lineage=lineage, role=self._role, step_description=self.__doc__,
            step_instruction=inspect.getsource(self.instructions),
            other=self._other_meta
        )
        return m.fingerprint


def ingredient(step: str) -> Path:
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
    return _Ingredient(step)
