import inspect
import json
import os
import shutil
from datetime import datetime
from hashlib import md5
from pathlib import Path
from typing import Union, Dict, Type
from uuid import uuid4

import requests
from tqdm import tqdm

from data_as_code import exceptions as ex
from data_as_code._metadata import Metadata, from_dictionary
from data_as_code._misc import intermediary

__all__ = ['Step', 'source_local', 'source_http']


class Step:
    """
    A process which takes one or more artifacts in a recipe, and transforms it
    into another artifact.
    """

    output: Union[Path, str] = None
    role: str = intermediary
    keep: bool = False
    _other_meta: Dict[str, str] = {}

    def __init__(self, workspace: Path, destination: Path):
        self._timing = {'started': datetime.utcnow()}
        self._guid = uuid4()

        self._workspace = Path(workspace, self._guid.hex)
        self._destination = destination
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
            ingredients.append(v.step.metadata)
            self.__setattr__(k, v.step.metadata.path)
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
            ap = Path(self._destination, rp)
            ap.parent.mkdir(parents=True, exist_ok=True)
            p.rename(ap)

        return Metadata(
            absolute_path=ap, relative_path=rp,
            checksum_value=hxd, checksum_algorithm='md5',
            lineage=[x for x in self._ingredients],
            role=self.role, relative_to=None,
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


class _Ingredient:
    def __init__(self, step: Step):
        self.step = step


def ingredient(step: Step) -> Path:
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


def source_local(path: Union[Path, str], keep=False) -> Type[Step]:
    v_path = Path(path)
    v_keep = keep

    class PremadeSourceLocal(Step):
        """Source file from available file system."""
        output = v_path
        keep = v_keep
        role = 'source'

        def instructions(self):
            pass

        def _execute(self):
            cached = self._check_cache()
            if cached:
                return cached
            else:
                return self._make_metadata()

        def _make_metadata(self) -> Metadata:
            rp = Path('data', self.role, self.output.name)
            if self.keep is True:
                ap = Path(self._destination, rp)
                ap.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy(self.output.absolute(), ap)
            else:
                ap = self.output.absolute()

            return Metadata(
                absolute_path=ap, relative_path=rp,
                checksum_value=md5(self.output.read_bytes()).hexdigest(),
                checksum_algorithm='md5',
                lineage=[x for x in self._ingredients],
                role=self.role, step_description=self.__doc__,
                step_instruction=inspect.getsource(self.instructions)
            )

    return PremadeSourceLocal


def source_http(url: str, keep=False) -> Type[Step]:
    v_url = url
    v_keep = keep

    class PremadeSourceHTTP(Step):
        """Retrieve file from URL via HTTP."""
        output = Path(Path(v_url).name)
        keep = v_keep
        role = 'source'

        _url = v_url
        _other_meta = dict(url=v_url)

        def instructions(self):
            try:
                print('Downloading from URL:\n' + self._url)
                response = requests.get(self._url, stream=True)
                context = dict(
                    total=int(response.headers.get('content-length', 0)),
                    desc=self.output.name, miniters=1
                )
                with self.output.open('wb') as f:
                    with tqdm.wrapattr(f, "write", **context) as stream:
                        for chunk in response.iter_content(chunk_size=4096):
                            stream.write(chunk)

            except requests.HTTPError as te:
                print(f'HTTP error while attempting to download: {self._url}')
                raise te

    return PremadeSourceHTTP
