import inspect
from pathlib import Path
from typing import Union, List, Generator, Tuple
from uuid import uuid4
from zipfile import ZipFile

import requests
from tqdm import tqdm

from data_as_code.metadata import Source, Intermediary, Recipe, _th_lineages, InputMetadata


class Step:
    def __init__(self, recipe: Recipe, name: str = None, **kwargs):
        self.name = name
        self.guid = uuid4()
        self.recipe = recipe

        self.inputs: List[str] = []
        self.output: Intermediary
        self.is_product = kwargs.get('is_product', False)

        self._set_inputs()
        self._set_output()

        if self.is_product:
            self._set_product()

    def process(self) -> Path:
        return None

    def _set_product(self):
        self.recipe.products.append(self.output)

    def _set_inputs(self):
        for k, v in inspect.getmembers(self, lambda x: isinstance(x, InputMetadata)):
            self.inputs.append(k)
            self.__setattr__(k, self.recipe.get_artifact(*v.lineage))

    def _set_output(self):
        origins = [self.__getattribute__(x) for x in self.inputs]
        self.output = self.process()
        if isinstance(self.output, list):
            self.output = [Intermediary(origins, x, name=x.name) for x in self.output]
            self.recipe.artifacts.extend(self.output)
        else:
            self.output = Intermediary(origins, self.output, name=self.name)
            self.recipe.artifacts.append(self.output)


class _GetSource(Step):
    def __init__(self, recipe: Recipe, origin: str, name: str = None, **kwargs):
        self.origins = [origin]
        super().__init__(recipe, name=name, **kwargs)


class SourceHTTP(_GetSource):
    def __init__(self, recipe: Recipe, url: str, name: str = None, **kwargs):
        self._url = url
        super().__init__(recipe, origin=url, name=name or Path(url).name, **kwargs)

    def process(self) -> Path:
        tp = Path(self.recipe.workspace, self.guid.hex, Path(self._url).name)
        tp.parent.mkdir()
        try:
            print('Downloading from URL:\n' + self._url)
            response = requests.get(self._url, stream=True)
            context = dict(
                total=int(response.headers.get('content-length', 0)),
                desc=self.name, miniters=1
            )
            with tp.open('wb') as f:
                with tqdm.wrapattr(f, "write", **context) as stream:
                    for chunk in response.iter_content(chunk_size=4096):
                        stream.write(chunk)

        except requests.HTTPError as te:
            print(f'HTTP error while attempting to download: {self._url}')
            raise te

        return tp


class SourceLocalFile(_GetSource):
    def __init__(self, recipe: Recipe, path: Union[str, Path], name: str = None, **kwargs):
        self.path = Path(path)
        super().__init__(
            recipe, origin=self.path.as_posix(), name=name or self.path.name, **kwargs
        )

    def process(self) -> Source:
        return self.path


class Unzip(Step):
    def __init__(self, recipe: Recipe, lineage: _th_lineages, **kwargs):
        self.zip_archive = InputMetadata(lineage)
        super().__init__(recipe, **kwargs)

    def process(self) -> List[Path]:
        return list(self.unpack())

    def unpack(self) -> Generator[Path, None, None]:
        with ZipFile(self.zip_archive.file_path) as zf:
            xd = Path(self.recipe.workspace, 'unzip' + self.zip_archive.file_hash.hexdigest()[:8])
            zf.extractall(xd)
            for file in [x for x in xd.rglob('*') if x.is_file()]:
                yield file


class OutputProducts:
    def __init__(self, recipe: Recipe, lineages: List[Union[str, Tuple[str]]]):
        self.recipe = recipe
        self.recipe.products.extend(
            [self.recipe.get_artifact(*lineage) for lineage in lineages]
        )
