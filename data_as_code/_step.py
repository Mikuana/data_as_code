import inspect
import json
import os
from datetime import datetime
from hashlib import md5
from pathlib import Path
from typing import Union, Dict
from uuid import uuid4

from data_as_code import exceptions as ex
from data_as_code._metadata import Metadata, from_dictionary
from data_as_code.misc import intermediary, _Ingredient


class Step:
    """
    A process which takes one or more artifacts in a recipe, and transforms it
    into another artifact.
    """

    output: Union[Path, str] = None
    role: str = intermediary
    keep: bool = False
    _other_meta: Dict[str, str] = {}

    def __init__(self, workspace: Path, destination: Path, antecedents: Dict[str, 'Step']):

        self._timing = {'started': datetime.utcnow()}
        self._guid = uuid4()
        self._workspace = Path(workspace, self._guid.hex)
        self._destination = destination
        self._antecedents = antecedents

        self._ingredients = self._get_ingredients()

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
        cached = self._check_cache()
        if cached:
            return cached
        else:
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

    def _get_ingredients(self):
        """
        Set Input Metadata

        Use the name lineage input defined for the Step class, get the Metadata
        object with the corresponding lineage, and assign the object back to the
        same attribute. This allows explict object assignment and reference in
        the step instructions for files which may not exist until runtime.

        This method must modify self, due to the dynamic naming of attributes.
        """
        ingredients = []
        for k, v in inspect.getmembers(self, lambda x: isinstance(x, _Ingredient)):
            ingredients.append(self._antecedents[v.step_name].metadata)
            self.__setattr__(k, self._antecedents[v.step_name].metadata.path)
        return ingredients

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
            rp = Path('data', self.role, self.output)
            ap = Path(self._destination, rp).absolute()
            ap.parent.mkdir(parents=True, exist_ok=True)
            p.rename(ap)

        return Metadata(
            absolute_path=ap, relative_path=rp,
            checksum_value=hxd, checksum_algorithm='md5',
            lineage=[x for x in self._ingredients],
            role=self.role, relative_to=self._destination.absolute(),
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
        mp = Path('metadata', self.role, f'{self.output}.json')
        if mp.is_file():
            meta = from_dictionary(
                **json.loads(mp.read_text()),
                relative_to=self._destination.as_posix()
            )
            dp = meta._relative_path
            if dp.is_file():
                try:
                    assert meta.fingerprint == self._mock_fingerprint(dp)
                    assert meta.checksum_value == md5(dp.read_bytes()).hexdigest()
                    print(
                        f"Using cached file for {self.role.title().ljust(13)}"
                        f"'{self.output}'"
                    )
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
            lineage=lineage, role=self.role, step_description=self.__doc__,
            step_instruction=inspect.getsource(self.instructions),
            other=self._other_meta
        )
        return m.fingerprint
