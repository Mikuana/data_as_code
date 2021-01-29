import inspect
import os
from hashlib import md5
from pathlib import Path
from typing import Union, List, Generator, Tuple
from uuid import uuid4
from zipfile import ZipFile

import requests
from tqdm import tqdm

from data_as_code._metadata import Metadata, Reference, Input
from data_as_code._recipe import Recipe


class Step:
    """
    A process which takes one or more artifacts in a recipe, and transforms it
    into another artifact.
    """
    name: str = None
    lineage: List[Union[Metadata, str]] = []

    def __init__(self, recipe: Recipe, **kwargs):
        self.guid = uuid4()
        self.recipe = recipe

        self.name = kwargs.get('name', self.name)
        self.lineage = kwargs.get('lineage', self.lineage)
        self.is_product = kwargs.get('is_product', False)

        self._step_dir = Path(self.recipe.workspace, self.guid.hex)

        self.inputs: List[str] = []
        self.output: List[Metadata]

        self._set_input()
        self._set_output()

        if self.is_product:
            self._set_product()

    def process(self) -> Union[Path, List[Path]]:
        return None

    def _set_product(self):
        self.recipe.products.append(self.output)

    def _set_input(self):
        for k, v in inspect.getmembers(self, lambda x: isinstance(x, Input)):
            self.inputs.append(k)
            self.__setattr__(k, self.recipe.get_artifact(*v.lineage))

    def _set_output(self):
        lineage = [self.__getattribute__(x) for x in self.inputs] + self.lineage

        original_wd = os.getcwd()
        self._step_dir.mkdir()
        os.chdir(self._step_dir)

        output = self.process()
        # force Path output into a list of Path
        if isinstance(output, Path):
            output = [output]

        os.chdir(original_wd)

        self.output = [
            Metadata(
                self.name, Path(self._step_dir, x),
                md5(Path(self._step_dir, x).read_bytes()).hexdigest(), 'md5',
                'intermediary', lineage
            )
            for x in output
        ]
        self.recipe.artifacts.extend(self.output)


class _GetSource(Step):
    def __init__(self, recipe: Recipe, name: str = None, **kwargs):
        super().__init__(recipe, name=name, **kwargs)


class SourceHTTP(_GetSource):
    """Download file from specified URL"""

    def __init__(self, recipe: Recipe, url: str, name: str = None, **kwargs):
        self._url = url
        super().__init__(recipe, name=name or Path(self._url).name, **kwargs)

    def process(self) -> Path:
        path = Path(Path(self._url).name)
        try:
            print('Downloading from URL:\n' + self._url)
            response = requests.get(self._url, stream=True)
            context = dict(
                total=int(response.headers.get('content-length', 0)),
                desc=self.name, miniters=1
            )
            with path.open('wb') as f:
                with tqdm.wrapattr(f, "write", **context) as stream:
                    for chunk in response.iter_content(chunk_size=4096):
                        stream.write(chunk)

        except requests.HTTPError as te:
            print(f'HTTP error while attempting to download: {self._url}')
            raise te

        return path


class SourceLocal(_GetSource):
    def __init__(self, recipe: Recipe, path: Union[str, Path], name: str = None, **kwargs):
        self._path = path
        super().__init__(
            recipe, name=name or path.name, path=path, **kwargs
        )

    def process(self) -> Metadata:
        return self._path


class Unzip(Step):
    def __init__(self, recipe: Recipe, lineage: List[Metadata], **kwargs):
        self.zip_archive = Input(lineage)
        super().__init__(recipe, **kwargs)

    def process(self) -> List[Path]:
        return list(self.unpack())

    def unpack(self) -> Generator[Path, None, None]:
        with ZipFile(self.zip_archive.path) as zf:
            xd = Path(self.recipe.workspace, 'unzip' + self.zip_archive.checksum_value[:8])
            zf.extractall(xd)
            for file in [x for x in xd.rglob('*') if x.is_file()]:
                yield file


class Output:
    def __init__(self, recipe: Recipe, lineages: List[Union[str, Tuple[str]]]):
        self.recipe = recipe
        for lin in lineages:
            if isinstance(lin, list):
                self.recipe.products.append(self.recipe.get_artifact(*lin))
            else:
                self.recipe.products.append(self.recipe.get_artifact(lin))
