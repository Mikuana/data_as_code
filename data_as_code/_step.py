import inspect
import os
from hashlib import md5
from pathlib import Path
from typing import Union, Generator, Dict, Tuple
from uuid import uuid4
from zipfile import ZipFile

import requests
from tqdm import tqdm

from data_as_code import exceptions as ex
from data_as_code.metadata import Metadata
from data_as_code.recipe import Recipe


class Step:
    """
    A process which takes one or more artifacts in a recipe, and transforms it
    into another artifact.
    """
    output: Union[Path, str] = None  # TODO: support multi-output

    def __init__(self, recipe: Recipe, product=False):
        self._guid = uuid4()
        self._recipe = recipe
        self._workspace = Path(self._recipe.workspace, self._guid.hex)
        self._ingredients = self._get_ingredients()

        if product and self.output is None:
            raise ex.StepUndefinedOutput("Products must have output defined")
        elif self.output:
            self.output = Path(self.output)
        else:
            self.output = Path(self._guid.hex)

        self._execute()
        self._metadata = self._get_metadata()

        if product:
            self._recipe.products.extend(
                self._metadata.values() if isinstance(self._metadata, dict)
                else [self._metadata]
            )

    def instructions(self):
        """
        Step Instructions

        Define the logic for this step which will use the inputs to generate an
        output file, and return the path, or paths, of the output.
        """
        return None

    def _execute(self):
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

        if isinstance(self.output, Path):
            return self._make_metadata(self.output, lineage)
        elif isinstance(self.output, dict):
            return {k: self._make_metadata(v, lineage) for k, v in self.output.items()}
        else:
            raise ex.StepError("instruction return was not a Path or dictionary of Paths")

    def _make_metadata(self, x: Path, lineage) -> Metadata:
        p = Path(self._workspace, x)
        hxd = md5(p.read_bytes()).hexdigest()
        if x.name == self._guid.hex:
            p = p.rename(Path(p.parent, hxd))

        return Metadata(p, hxd, 'md5', lineage, Path(self._workspace))


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

    def __init__(self, recipe: Recipe, **kwargs):
        super().__init__(recipe, **kwargs)


class _SourceHTTP(_SourceStep):
    """Download file from specified URL"""

    def __init__(self, recipe: Recipe, url: str, **kwargs):
        self._url = url
        kwargs['other'] = {**{'url': url}, **kwargs.get('other', {})}
        self.output = Path(Path(self._url).name)
        super().__init__(recipe, **kwargs)

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
    def __init__(self, recipe: Recipe, path: Union[str, Path], **kwargs):
        self.output = path
        super().__init__(recipe, **kwargs)

    def instructions(self):
        pass

    def _execute(self):
        pass

    def _make_metadata(self, x: Path, lineage) -> Metadata:
        return Metadata(  # TODO: un-absolute this
            x.absolute(), md5(x.read_bytes()).hexdigest(), 'md5',
            lineage, None
        )


class _Unzip(Step):
    output: dict = None

    def __init__(self, recipe: Recipe, step: Step, **kwargs):
        self.zip_archive = ingredient(step)
        super().__init__(recipe, **kwargs)

    def instructions(self):
        self.output = {x[0]: x[1] for x in self.unpack()}

    def unpack(self) -> Generator[Tuple[str, Path], None, None]:
        with ZipFile(self.zip_archive.path) as zf:
            xd = Path(self._recipe.workspace, self.zip_archive.path.name)
            zf.extractall(xd)
            for file in [x for x in xd.rglob('*') if x.is_file()]:
                yield file.as_posix(), file