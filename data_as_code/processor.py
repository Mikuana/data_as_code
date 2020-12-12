from typing import List, Union, Iterable

from data_as_code.artifact import Source, Intermediary

from pathlib import Path
from typing import List, Union, Generator, Tuple
from uuid import uuid4
from zipfile import ZipFile
import gzip

import pandas as pd
import requests
from tqdm import tqdm

from data_as_code.field import _SourceField, Target, FixedWidthSource
from data_as_code.artifact import _Artifact, Source, Intermediary


t_lstr = Union[str, List[str]]
t_art = List[Union[Source, Intermediary]]

class _Processor:
    def __init__(self, lineage: t_lstr, artifacts: t_art, name: str = None):
        self.name = name
        self.guid = uuid4()
        self.artifact = self.get_descendent(
            [lineage] if isinstance(lineage, str) else lineage, artifacts
        )

    def process(self, artifacts: List[Union[Source, Intermediary]]) -> Intermediary:
        pass

    @staticmethod
    def get_descendent(lineage: Union[str, Iterable[str]], artifacts: List[Union[Source, Intermediary]]):
        """
        Get Descendent

        Descend lineage names to select the Artifact which matches the specified
        chain from the available Artifacts.
        """
        lineage = [lineage] if isinstance(lineage, str) else lineage
        candidates = [x.is_descendent(*lineage) for x in artifacts]
        if sum(candidates) == 1:
            return artifacts[candidates.index(True)]
        elif sum(candidates) > 1:
            # TODO: this needs to give more hints to assist resolution
            raise Exception("Lineage matches multiple candidates")
        else:
            raise Exception("Lineage does not match any candidate")


class _Getter(_Processor):
    def __init__(self, origin: str, name: str = None):
        super().__init__(name=name)
        self.origin = origin

    def retrieve(self, target_dir: Union[Path, str]) -> _Artifact:
        pass


class GetHTTP(_Getter):
    def __init__(self, url, name: str = None):
        super().__init__(origin=url, name=name or Path(url).name)

    def retrieve(self, target_dir: Union[Path, str]) -> _Artifact:
        tp = Path(target_dir, self.guid.hex + Path(self.name).suffix)
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
    def __init__(self, path: Union[str, Path], name: str = None):
        self.path = Path(path)
        super().__init__(origin=self.path.as_posix(), name=name or self.path.name)

    def retrieve(self, target_dir: Union[Path, str]) -> _Artifact:
        return Source(self.origin, self.path, name=self.name)


class Unzip(_Processor):
    def process(self, artifacts: List[Union[Source, Intermediary]]) -> List[Intermediary]:

    def unpack(self, target_dir: Union[Path, str]) -> Generator[_Artifact, None, None]:
        with ZipFile(self.artifact.file_path) as zf:
            xd = Path(target_dir, self.artifact.guid.hex)
            zf.extractall(xd)
            for file in xd.rglob('*'):
                yield Intermediary(self.artifact, file, name=file.name)


class _Parser(_Processor):
    def __init__(self, lineage: List[str], fields: Tuple[Union[_SourceField, Target]]):
        super().__init__(lineage)
        self.fields = fields

    def remap(self, target_dir: Union[Path, str]) -> _Artifact:
        df = pd.DataFrame()
        return df


class ParseFixedWidth(_Parser):
    def __init__(self, lineage: List[str], fields: List[Union[FixedWidthSource, Target]]):
        super().__init__(lineage=lineage, fields=fields)

    def remap(self, target_dir: Union[Path, str], **kwargs) -> _Artifact:
        name = Path(self.artifact.name).with_suffix('.parquet')
        p = Path(target_dir, self.guid.hex + '.parquet')

        fd = self._extract_text(kwargs.get('sample_size'))

        new_keys = [x.name() for x in fd.keys()]
        fd = dict(zip(new_keys, fd.values()))
        df = pd.DataFrame.from_dict(fd)

        df.to_parquet(p)
        return Intermediary(self.artifact, p, name=name)

    def _extract_text(self, sample_size=0) -> dict:
        print(f"Counting rows in {self.artifact.file_path}")
        if sample_size:
            total = sample_size
        else:
            with self.artifact.file_path.open() as r:
                total = sum(1 for _ in r)
        print(f"Found {total:,} rows in {self.artifact.file_path}")

        fd = {x: [] for x in self.fields if issubclass(x, _SourceField)}
        print(f"Extracting raw data from {self.artifact.file_path}")
        with self.artifact.file_path.open() as r:
            for ix, line in enumerate(tqdm(r, total=total)):
                if sample_size and ix > sample_size:
                    break
                if not line.isspace():
                    for k, v in fd.items():
                        fd[k].append(k.parse_from_row(line))
        return fd

    def _extract_gzip(self, sample_size=0) -> dict:
        if sample_size:
            total = sample_size
        else:
            with gzip.open(self.artifact.file_path, 'rt') as r:
                total = sum(1 for _ in r)
        print(f"Found {total:,} rows in {self.artifact.file_path}")

        fd = {x: [] for x in self.fields if issubclass(x, _SourceField)}
        print(f"Extracting raw data from {self.artifact.file_path}")
        with gzip.open(self.artifact.file_path, 'rt') as r:
            for ix, line in enumerate(tqdm(r, total=total)):
                if sample_size and ix > sample_size:
                    break
                if not line.isspace():
                    for k, v in fd.items():
                        fd[k].append(k.parse_from_row(line))
        return fd
