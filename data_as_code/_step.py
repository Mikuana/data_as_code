import inspect
import json
import os
from hashlib import md5
from pathlib import Path
from typing import Union, Generator, Dict, Tuple
from uuid import uuid4
from zipfile import ZipFile

import requests
from tqdm import tqdm

from data_as_code import exceptions as ex
from data_as_code._metadata import Metadata, from_dictionary
from data_as_code._recipe import Recipe

source = 'source'
intermediary = 'intermediary'
product = 'product'


class Step:
    """
    A process which takes one or more artifacts in a recipe, and transforms it
    into another artifact.
    """

    output: Union[Path, str] = None  # TODO: support multi-output
    role: str = intermediary
    keep: bool = False

    def _determine_keep(self):
        """ Assigned type must be a valid choice """
        assert self.role in (source, intermediary, product)
        if self.role == product:  # always keep product
            return True

        elif self.role == intermediary:
            return self.keep or self._recipe.keep.intermediaries

        elif self.role == source:
            return self.keep or self._recipe.keep.sources

    def __init__(self, recipe: Recipe, other: dict = None):
        self._guid = uuid4()
        self._other_meta = other
        self._recipe = recipe
        self._workspace = Path(self._recipe.workspace, self._guid.hex)
        self._ingredients = self._get_ingredients()
        self.keep = self._determine_keep()

        if self.output is None and self.keep is True:
            raise ex.StepUndefinedOutput(
                "To keep an artifact you must define the output path"
            )
        elif self.output:
            self.output = Path(self.output)
        else:
            self.output = Path(self._guid.hex)

        self._metadata = self._execute()

        if self.keep is True:
            if self.role == product:
                self._recipe.products.append(self._metadata)

            elif self.role == intermediary:
                self._recipe.intermediaries.append(self._metadata)

            elif self.role == source:
                self._recipe.sources.append(self._metadata)

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

                return self._get_metadata()
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
            ingredients.append(k)
            self.__setattr__(k, v.step._metadata)
        return ingredients

    def _get_metadata(self) -> Union[Metadata, Dict[str, Metadata]]:
        """
        Set Output Metadata

        Use the Path list returned by the Step Instructions to create a list of
        output Metadata for the step. These outputs get added to the Recipe
        artifacts
        """
        lineage = [self.__getattribute__(x) for x in self._ingredients]

        return self._make_metadata(self.output, lineage)

    def _make_metadata(self, x: Path, lineage) -> Metadata:
        p = Path(self._workspace, x)

        hxd = md5(p.read_bytes()).hexdigest()

        ap, rp = None, None
        if x.name == self._guid.hex:
            ap = p
        elif self.keep is True:
            rp = Path('data', self.role, x)
            ap = Path(self._recipe.destination, rp)
            ap.parent.mkdir(parents=True, exist_ok=True)
            p.rename(ap)

        return Metadata(
            absolute_path=ap, relative_path=rp,
            checksum_value=hxd, checksum_algorithm='md5',
            lineage=lineage, role=self.role, relative_to=None,
            other=self._other_meta
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
                relative_to=self._recipe.destination.as_posix()
            )
            dp = meta.relative_path
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
        lineage = [self.__getattribute__(x) for x in self._ingredients]
        hxd = md5(candidate.read_bytes()).hexdigest()
        m = Metadata(
            absolute_path=None, relative_path=candidate,
            checksum_value=hxd, checksum_algorithm='md5',
            lineage=lineage, role=self.role, other=self._other_meta
        )
        return m.fingerprint


class _Ingredient:
    def __init__(self, step: Step):
        self.step = step


def ingredient(step: Step) -> Metadata:
    """
    Prepare step ingredient

    Use the metadata from a previously executed step as an ingredient for
    another step. This function is a wrapper to allowing passing the results of
    a previous step directly to the next, while still allowing context hints to
    function appropriately.
    """
    # noinspection PyTypeChecker
    return _Ingredient(step)


class _SourceStep(Step):
    role = 'source'

    def __init__(self, recipe: Recipe, keep=False, **kwargs):
        self.keep = keep
        super().__init__(recipe, **kwargs)


class _SourceHTTP(_SourceStep):
    """Download file from specified URL"""

    def __init__(self, recipe: Recipe, url: str, **kwargs):
        self._url = url
        self.output = Path(Path(self._url).name)
        super().__init__(recipe, other=dict(url=url), **kwargs)

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


class _SourceLocal(_SourceStep):
    role = 'source'

    def __init__(self, recipe: Recipe, path: Union[str, Path], **kwargs):
        self.output = path
        super().__init__(recipe, **kwargs)

    def instructions(self):
        pass

    def _execute(self):
        pass

    def _make_metadata(self, x: Path, lineage) -> Metadata:
        rp = Path('data', self.role, x.name)
        return Metadata(  # TODO: un-absolute this
            absolute_path=x.absolute(), relative_path=rp,
            checksum_value=md5(x.read_bytes()).hexdigest(), checksum_algorithm='md5',
            lineage=lineage, role=self.role
        )


class _Unzip(Step):
    output: dict = None

    def __init__(self, recipe: Recipe, step: Step):
        self.zip_archive = ingredient(step)
        super().__init__(recipe)

    def instructions(self):
        self.output = {x[0]: x[1] for x in self.unpack()}

    def unpack(self) -> Generator[Tuple[str, Path], None, None]:
        with ZipFile(self.zip_archive.path) as zf:
            xd = Path(self._recipe.workspace, self.zip_archive.path.name)
            zf.extractall(xd)
            for file in [x for x in xd.rglob('*') if x.is_file()]:
                yield file.as_posix(), file
