import inspect
import os
from hashlib import md5
from pathlib import Path
from typing import Union, List, Generator, Dict, Tuple
from uuid import uuid4
from zipfile import ZipFile

import requests
from tqdm import tqdm

from data_as_code._metadata import Metadata
from data_as_code._recipe import Recipe


class _Kind:
    s: str

    @classmethod
    def __str__(cls):
        return cls.s


class Source(_Kind):
    s = 'source'


class Intermediary(_Kind):
    s = 'intermediary'


class Product(_Kind):
    s = 'product'


class _Step:
    """
    A process which takes one or more artifacts in a recipe, and transforms it
    into another artifact.

    TODO: recipe, and other params
    """
    inputs: list = []
    kind: Union[Source, Intermediary, Product]
    lineage: List[Union[Metadata, str]] = []

    def __init__(self, recipe: Recipe, product=False, **kwargs):
        self.guid = uuid4()
        self.recipe = recipe

        self.lineage = kwargs.get('lineage', self.lineage)
        self.other = kwargs.get('other')
        self._workspace = kwargs.get('workspace')
        if self._workspace:
            self._workspace = Path(self._workspace)
        else:
            self._workspace = Path(self.recipe.workspace, self.guid.hex)

        self._set_ingredients()
        self.output = self._metadata_outputs()
        if product:
            self.recipe.products.extend(self.output)

    def instructions(self) -> Union[Path, Dict[str, Path]]:
        """
        Step Instructions

        Define the logic for this step which will use the inputs to generate an
        output file, and return the path, or paths, of the output.
        """
        pass

    def _set_ingredients(self):
        """
        Set Input Metadata

        Use the name lineage input defined for the Step class, get the Metadata
        object with the corresponding lineage, and assign the object back to the
        same attribute. This allows explict object assignment and reference in
        the step instructions for files which may not exist until runtime.

        This method must modify self, due to the dynamic naming of attributes.
        """
        inputs = []
        for k, v in inspect.getmembers(self, lambda x: issubclass(type(x), type(self))):
            inputs.append(k)
            self.__setattr__(k, v.output)
        self.inputs = inputs

    def _metadata_outputs(self) -> Union[Metadata, Dict[str, Metadata]]:
        """
        Set Output Metadata

        Use the Path list returned by the Step Instructions to create a list of
        output Metadata for the step. These outputs get added to the Recipe
        artifacts
        """
        lineage = [self.__getattribute__(x) for x in self.inputs] + self.lineage

        original_wd = os.getcwd()
        self._workspace.mkdir(exist_ok=True)
        os.chdir(self._workspace)

        output = self.instructions()
        # force Path output into a list of Path
        if isinstance(output, Path):
            output = self._make_metadata(output, lineage)
        elif isinstance(output, dict):
            output = {k: self._make_metadata(v, lineage) for k, v in output.items()}
        else:
            raise TypeError("instruction return was not a Path or dictionary of Paths")

        os.chdir(original_wd)

        return output

    def _make_metadata(self, x: Path, lineage) -> Metadata:
        return Metadata(
            x.name, Path(self._workspace, x),
            md5(Path(self._workspace, x).read_bytes()).hexdigest(), 'md5',
            str(self.kind), lineage, self.other, Path(self._workspace)
        )


class _Ingredient(_Step):
    output: Union[Path, Dict[str, Path]]

    # noinspection PyMissingConstructor
    def __init__(self, step: _Step):
        self.step = step


def ingredient(step: _Step) -> Union[Metadata, Dict[str, Metadata]]:
    return _Ingredient(step).step.output


class Custom(_Step):
    inputs: List[Union[Path, Dict[str, Path]]] = []
    kind: Union[Source, Intermediary, Product] = Intermediary


class _SourceStep(_Step):
    kind = Source

    def __init__(self, recipe: Recipe, **kwargs):
        super().__init__(recipe, **kwargs)


class SourceHTTP(_SourceStep):
    """Download file from specified URL"""

    def __init__(self, recipe: Recipe, url: str, name: str = None, **kwargs):
        self._url = url
        kwargs['other'] = {**{'url': url}, **kwargs.get('other', {})}
        super().__init__(recipe, **kwargs)

    def instructions(self) -> Path:
        path = Path(Path(self._url).name)
        try:
            print('Downloading from URL:\n' + self._url)
            response = requests.get(self._url, stream=True)
            context = dict(
                total=int(response.headers.get('content-length', 0)),
                desc=path.name, miniters=1
            )
            with path.open('wb') as f:
                with tqdm.wrapattr(f, "write", **context) as stream:
                    for chunk in response.iter_content(chunk_size=4096):
                        stream.write(chunk)

        except requests.HTTPError as te:
            print(f'HTTP error while attempting to download: {self._url}')
            raise te

        return path


class SourceLocal(_SourceStep):
    def __init__(self, recipe: Recipe, path: Union[str, Path], **kwargs):
        self._path = path
        super().__init__(recipe, workspace='.', **kwargs)

    def instructions(self) -> Path:
        return Path(self._path).absolute()

    def _make_metadata(self, x: Path, lineage) -> Metadata:
        return Metadata(
            x.name, x, md5(x.read_bytes()).hexdigest(), 'md5',
            str(self.kind), lineage, self.other, None
        )


class Unzip(_Step):
    def __init__(self, recipe: Recipe, step: _Step, **kwargs):
        self.zip_archive = ingredient(step)
        super().__init__(recipe, **kwargs)

    def instructions(self) -> Dict[str, Path]:
        return {x[0]: x[1] for x in self.unpack()}

    def unpack(self) -> Generator[Tuple[str, Path], None, None]:
        with ZipFile(self.zip_archive) as zf:
            xd = Path(self.recipe.workspace, self.zip_archive.name)
            zf.extractall(xd)
            for file in [x for x in xd.rglob('*') if x.is_file()]:
                yield file.as_posix(), file
