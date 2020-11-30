from hashlib import sha256
from pathlib import Path
from typing import List, Union, Generator, Tuple
from uuid import uuid4
from zipfile import ZipFile

import pandas as pd
import requests
from tqdm import tqdm

from data_as_code.field import _SourceField, Target, FixedWidthSource
from data_as_code.source import Source


class _Worker:
    def __init__(self, lineage: Union[str, List[str]] = None, name: str = None):
        self.name = name
        self.guid = uuid4()
        self.lineage = [lineage] if isinstance(lineage, str) else lineage
        self.source: Source = None

    def source_descendent(self, sources: List[Source]):
        """
        Source Descendent

        Descend lineage names to select the source from available which matches
        the specified chain.
        """
        candidates = [x.is_descendent(*self.lineage) for x in sources]
        if sum(candidates) == 1:
            self.source = sources[candidates.index(True)]
        elif sum(candidates) > 1:
            # TODO: this needs to give more hints to assist resolution
            raise Exception("Lineage matches multiple candidates")
        else:
            raise Exception("Lineage does not match any candidate")

    @staticmethod
    def sha256(path: Path):
        h = sha256()
        h.update(path.read_bytes())
        return h


class _Retriever(_Worker):
    def __init__(self, origin: str, name: str = None):
        super().__init__(name=name)
        self.origin = origin

    def retrieve(self, target_dir: Union[Path, str]) -> Source:
        pass


class GetHTTP(_Retriever):
    def __init__(self, url, name: str = None):
        super().__init__(origin=url, name=name or Path(url).name)

    def retrieve(self, target_dir: Union[Path, str]) -> Source:
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

        return Source(
            self.name, self.origin, self.sha256(tp), tp, self.guid
        )


class GetLocalFile(_Retriever):
    def __init__(self, path: Union[str, Path], name: str = None):
        self.path = Path(path)
        super().__init__(origin=self.path.as_posix(), name=name or self.path.name)

    def retrieve(self, target_dir: Union[Path, str]) -> Source:
        return Source(
            self.name, self.origin, self.sha256(self.path), self.path, self.guid
        )


class Unzip(_Worker):
    def unpack(self, target_dir: Union[Path, str]) -> Generator[Source, None, None]:
        with ZipFile(self.source.file_path) as zf:
            xd = Path(target_dir, self.source.guid.hex)
            zf.extractall(xd)
            for file in xd.rglob('*'):
                yield Source(
                    file.name, self.source, self.sha256(file), file, uuid4()
                )


class _Parser(_Worker):
    def __init__(self, lineage: List[str], fields: Tuple[Union[_SourceField, Target]]):
        super().__init__(lineage)
        self.fields = fields

    def remap(self, target_dir: Union[Path, str]) -> Source:
        df = pd.DataFrame()
        pass


class ParseFixedWidth(_Parser):
    def __init__(self, lineage: List[str], fields: List[Union[FixedWidthSource, Target]]):
        super().__init__(lineage=lineage, fields=fields)

    def remap(self, target_dir: Union[Path, str], **kwargs) -> Source:
        name = Path(self.source.name).with_suffix('.parquet')
        p = Path(target_dir, self.guid.hex + '.parquet')

        fd = self._extract_text(kwargs.get('sample_size'))

        new_keys = [x.name() for x in fd.keys()]
        fd = dict(zip(new_keys, fd.values()))
        df = pd.DataFrame.from_dict(fd)

        df.to_parquet(p)
        return Source(name, self.source, self.sha256(p), p, self.guid)

    def _extract_text(self, sample_size=0) -> dict:
        print(f"Counting rows in {self.source.file_path}")
        if sample_size:
            total = sample_size
        else:
            with self.source.file_path.open() as r:
                total = sum(1 for _ in r)
        print(f"Found {total:,} rows in {self.source.file_path}")

        fd = {x: [] for x in self.fields if issubclass(x, _SourceField)}
        print(f"Extracting raw data from {self.source.file_path}")
        with self.source.file_path.open() as r:
            for ix, line in enumerate(tqdm(r, total=total)):
                if sample_size and ix > sample_size:
                    break
                if not line.isspace():
                    for k, v in fd.items():
                        fd[k].append(k.parse_from_row(line))
        return fd

    def _extract_gzip(self, sample_size=0) -> dict:
        # TODO: make gzip equivalent
        pass
