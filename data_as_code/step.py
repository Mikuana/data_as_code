import inspect
import os
from pathlib import Path
from typing import Union, List, Generator, Tuple
from uuid import uuid4
from zipfile import ZipFile

import requests
from tqdm import tqdm

from data_as_code.metadata import (
    Metadata, Source, Intermediary, Recipe, _th_lineages, Input, Reference
)


class Step:
    name: str = None
    origins: List[Union[Metadata, str]] = []

    def __init__(self, recipe: Recipe, **kwargs):
        self.name = kwargs.get('name', self.name)
        self.origins = kwargs.get('origins')

        # TODO: ew
        if self.origins:
            self.origins = self.origins if isinstance(self.origins, list) else [self.origins]
        else:
            self.origins = []

        self.guid = uuid4()
        self.recipe = recipe

        self.inputs: List[str] = []
        self.output: Intermediary
        self.is_product = kwargs.get('is_product', False)

        self._step_dir = Path(self.recipe.workspace, self.guid.hex)

        self._set_inputs()
        self._set_output()

        if self.is_product:
            self._set_product()

    def process(self) -> Path:
        return None

    def _set_product(self):
        self.recipe.products.append(self.output)

    def _set_inputs(self):
        for k, v in inspect.getmembers(self, lambda x: isinstance(x, Input)):
            self.inputs.append(k)
            self.__setattr__(k, self.recipe.get_artifact(*v.lineage))

    def _set_output(self):
        origins = [self.__getattribute__(x) for x in self.inputs] + self.origins

        original_wd = os.getcwd()
        self._step_dir.mkdir()
        os.chdir(self._step_dir)
        self.output = self.process()
        os.chdir(original_wd)

        if isinstance(self.output, list):

            self.output = [
                Intermediary(
                    origins, Path(self._step_dir, x), name=x.name, ref_path=x,
                    notes=self.__doc__
                )
                for x in self.output]
            self.recipe.artifacts.extend(self.output)
        else:
            self.output = Intermediary(
                origins, Path(self._step_dir, self.output),
                name=self.name or self.output.name, ref_path=self.output, notes=self.__doc__
            )
            self.recipe.artifacts.append(self.output)


class _GetSource(Step):
    def __init__(self, recipe: Recipe, name: str = None, **kwargs):
        super().__init__(recipe, name=name, **kwargs)


class SourceHTTP(_GetSource):
    """Download file from specified URL"""

    def __init__(self, recipe: Recipe, url: str, name: str = None, **kwargs):
        self._url = url
        if kwargs.get('mock'):
            origins = Reference(kwargs.pop('mock'), url=url)
        else:
            origins = url
        super().__init__(recipe, origins=origins, name=name or Path(url).name, **kwargs)

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
        self.path = Path(path)
        if kwargs.get('reference'):
            origins = Reference(kwargs.pop('reference'), path=self.path.as_posix())
        else:
            origins = self.path.as_posix()

        super().__init__(
            recipe, origins=origins, name=name or self.path.name, **kwargs
        )

    def process(self) -> Source:
        return self.path


class Unzip(Step):
    def __init__(self, recipe: Recipe, lineage: _th_lineages, **kwargs):
        self.zip_archive = Input(lineage)
        super().__init__(recipe, **kwargs)

    def process(self) -> List[Path]:
        return list(self.unpack())

    def unpack(self) -> Generator[Path, None, None]:
        with ZipFile(self.zip_archive.path) as zf:
            xd = Path(self.recipe.workspace, 'unzip' + self.zip_archive.checksum.hexdigest()[:8])
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
