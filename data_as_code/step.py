import inspect
from pathlib import Path
from typing import Union, List, Generator
from uuid import uuid4
from zipfile import ZipFile

import requests
from tqdm import tqdm

from data_as_code.artifact import Source, Intermediary, Recipe, lineages, StepInput


class Step:
    def __init__(self, recipe: Recipe, name: str = None, **kwargs):
        self.name = name
        self.guid = uuid4()
        self.recipe = recipe
        self.materialize_inputs()
        self.result = self.process()

        check = self.result if isinstance(self.result, list) else [self.result]

        if any([not isinstance(x, (Source, Intermediary)) for x in check]):
            raise Exception("process method must did not returned an non-Artifact")

        if isinstance(self.result, list):
            self.recipe.artifacts.extend(self.result)
        else:
            self.recipe.artifacts.append(self.result)

    def process(self) -> Intermediary:
        pass

    def materialize_inputs(self):
        for k, v in inspect.getmembers(self, lambda x: isinstance(x, StepInput)):
            self.__setattr__(k, self.artifact(*v.lineage))

    def artifact(self, *args: str) -> Union[Source, Intermediary]:
        lineage = [*args]
        candidates = [x.is_descendent(*lineage) for x in self.recipe.artifacts]
        if sum(candidates) == 1:
            return self.recipe.artifacts[candidates.index(True)]
        elif sum(candidates) > 1:
            raise Exception("Lineage matches multiple candidates")
        else:
            raise Exception(
                "Lineage does not match any candidate" + '\n',
                f"{lineage}" + "\n",
                f"{self.recipe.artifacts}"
            )


class _Getter(Step):
    def __init__(self, recipe: Recipe, origin: str, name: str = None, **kwargs):
        self.origin = origin
        super().__init__(recipe, name=name, **kwargs)

    def retrieve(self, target_dir: Union[Path, str]) -> Source:
        pass


class GetHTTP(_Getter):
    def __init__(self, recipe: Recipe, url: str, name: str = None, **kwargs):
        super().__init__(recipe, origin=url, name=name or Path(url).name, **kwargs)

    def process(self) -> Source:
        tp = Path(self.recipe.wd, self.guid.hex + Path(self.name).suffix)
        try:
            print('Downloading from URL:\n' + self.origin)
            response = requests.get(self.origin, stream=True)
            context = dict(
                total=int(response.headers.get('content-length', 0)),
                desc=self.name, miniters=1
            )
            with tp.open('wb') as f:
                with tqdm.wrapattr(f, "write", **context) as stream:
                    for chunk in response.iter_content(chunk_size=4096):
                        stream.write(chunk)

        except requests.HTTPError as te:
            print(f'HTTP error while attempting to download: {self.origin}')
            raise te

        return Source(self.origin, tp, name=self.name)


class GetLocalFile(_Getter):
    def __init__(self, recipe: Recipe, path: Union[str, Path], name: str = None, **kwargs):
        self.path = Path(path)
        super().__init__(
            recipe, origin=self.path.as_posix(), name=name or self.path.name, **kwargs
        )

    def process(self) -> Source:
        return Source(self.origin, self.path, name=self.name, rename=False)


class Unzip(Step):
    def __init__(self, recipe: Recipe, lineage: lineages, name: str = None, **kwargs):
        self.zip_archive = StepInput(lineage)
        super().__init__(recipe, name=name, **kwargs)

    def process(self) -> List[Intermediary]:
        return list(self.unpack())

    def unpack(self) -> Generator[Intermediary, None, None]:
        with ZipFile(self.zip_archive.file_path) as zf:
            xd = Path(self.recipe.wd, 'unzip-' + self.zip_archive.file_hash.hexdigest()[:8])
            zf.extractall(xd)
            for file in xd.rglob('*'):
                yield Intermediary(self.zip_archive, file, name=file.name, rename=False)

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
