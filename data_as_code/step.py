import inspect
from pathlib import Path
from typing import Union, List, Generator
from uuid import uuid4
from zipfile import ZipFile

import requests
from tqdm import tqdm

from data_as_code.artifact import Artifact, Source, Intermediary, Recipe, lineages, InputArtifact


class Step:
    def __init__(self, recipe: Recipe, name: str = None, **kwargs):
        self.name = name
        self.guid = uuid4()
        self.recipe = recipe

        self.inputs: List[str] = []
        self.output: Intermediary

        self._set_inputs()
        self._set_output()

    def process(self) -> Path:
        return None

    def _set_inputs(self):
        for k, v in inspect.getmembers(self, lambda x: isinstance(x, InputArtifact)):
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


class _Getter(Step):
    def __init__(self, recipe: Recipe, origin: str, name: str = None, **kwargs):
        self.origins = [origin]
        super().__init__(recipe, name=name, **kwargs)


class GetHTTP(_Getter):
    def __init__(self, recipe: Recipe, url: str, name: str = None, **kwargs):
        self._url = url
        super().__init__(recipe, origin=url, name=name or Path(url).name, **kwargs)

    def process(self) -> Path:
        tp = Path(self.recipe.wd, self.guid.hex, Path(self._url).name)
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


class GetLocalFile(_Getter):
    def __init__(self, recipe: Recipe, path: Union[str, Path], name: str = None, **kwargs):
        self.path = Path(path)
        super().__init__(
            recipe, origin=self.path.as_posix(), name=name or self.path.name, **kwargs
        )

    def process(self) -> Source:
        return self.path


class Unzip(Step):
    def __init__(self, recipe: Recipe, lineage: lineages, **kwargs):
        self.zip_archive = InputArtifact(lineage)
        super().__init__(recipe, **kwargs)

    def process(self) -> List[Path]:
        return list(self.unpack())

    def unpack(self) -> Generator[Path, None, None]:
        with ZipFile(self.zip_archive.file_path) as zf:
            xd = Path(self.recipe.wd, 'unzip' + self.zip_archive.file_hash.hexdigest()[:8])
            zf.extractall(xd)
            for file in [x for x in xd.rglob('*') if x.is_file()]:
                yield file

# class _Parser(_Processor):
#     def __init__(self, lineage: List[str], fields: Tuple[Union[_SourceField, Target]]):
#         super().__init__(lineage)
#         self.fields = fields
#
#     def remap(self, target_dir: Union[Path, str]) -> _Artifact:
#         df = pd.DataFrame()
#         return df
#
#
# class ParseFixedWidth(_Parser):
#     def __init__(self, lineage: List[str], fields: List[Union[FixedWidthSource, Target]]):
#         super().__init__(lineage=lineage, fields=fields)
#
#     def remap(self, target_dir: Union[Path, str], **kwargs) -> _Artifact:
#         name = Path(self.artifact.name).with_suffix('.parquet')
#         p = Path(target_dir, self.guid.hex + '.parquet')
#
#         fd = self._extract_text(kwargs.get('sample_size'))
#
#         new_keys = [x.name() for x in fd.keys()]
#         fd = dict(zip(new_keys, fd.values()))
#         df = pd.DataFrame.from_dict(fd)
#
#         df.to_parquet(p)
#         return Intermediary(self.artifact, p, name=name)
#
#     def _extract_text(self, sample_size=0) -> dict:
#         print(f"Counting rows in {self.artifact.file_path}")
#         if sample_size:
#             total = sample_size
#         else:
#             with self.artifact.file_path.open() as r:
#                 total = sum(1 for _ in r)
#         print(f"Found {total:,} rows in {self.artifact.file_path}")
#
#         fd = {x: [] for x in self.fields if issubclass(x, _SourceField)}
#         print(f"Extracting raw data from {self.artifact.file_path}")
#         with self.artifact.file_path.open() as r:
#             for ix, line in enumerate(tqdm(r, total=total)):
#                 if sample_size and ix > sample_size:
#                     break
#                 if not line.isspace():
#                     for k, v in fd.items():
#                         fd[k].append(k.parse_from_row(line))
#         return fd
#
#     def _extract_gzip(self, sample_size=0) -> dict:
#         if sample_size:
#             total = sample_size
#         else:
#             with gzip.open(self.artifact.file_path, 'rt') as r:
#                 total = sum(1 for _ in r)
#         print(f"Found {total:,} rows in {self.artifact.file_path}")
#
#         fd = {x: [] for x in self.fields if issubclass(x, _SourceField)}
#         print(f"Extracting raw data from {self.artifact.file_path}")
#         with gzip.open(self.artifact.file_path, 'rt') as r:
#             for ix, line in enumerate(tqdm(r, total=total)):
#                 if sample_size and ix > sample_size:
#                     break
#                 if not line.isspace():
#                     for k, v in fd.items():
#                         fd[k].append(k.parse_from_row(line))
#         return fd
