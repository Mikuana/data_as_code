from hashlib import sha256
from uuid import uuid4
from pathlib import Path
import pandas as pd
import re
from typing import Tuple, Union, List
from tqdm import tqdm
from dac.source import Source, RemappedFile, Descendent
from dac.other import Maker

class Handlers:
    """ Raw value handlers """

    @staticmethod
    def integer(x):
        return int(x) if x.strip() else None

    @staticmethod
    def character(x):
        return x.decode('utf-8')


class Field:
    """ Base Field class """

    @classmethod
    def name(cls):
        return re.sub(r'(?<!^)(?=[A-Z])', '_', cls.__name__).lower()


class SourceField(Field):
    """ SourceField Field """
    handler: callable
    na_value = None
    labels = {}

    @classmethod
    def prep(cls, value: str):
        return cls.handler(value)

    @classmethod
    def decode(cls, value):
        if cls.labels:
            return cls.labels.get(value)
        else:
            return None if value == cls.na_value else value


class FixedWidthSource(SourceField):
    """
    Fixed Width Field

    A column that exists in the source fixed-width-file. This class maps positions,
    NA value placeholders, and data labels if applicable. SourceField columns are not
    necessarily included in the final output, but are instead used to provide data
    for Target columns.
    """
    positions: Tuple[int, int]

    @classmethod
    def parse_from_row(cls, row: list):
        value = row[cls.positions[0] - 1:cls.positions[1]]
        value = cls.prep(value)
        value = cls.decode(value)
        return value


class Target(Field):
    """
    Target Column

    A column which is included in the final data output. This must include a
    pandas data type, and methods to combine multiple SourceField columns together
    when necessary.
    """
    pd_type: str = None

    @classmethod
    def remap(cls, data_frame: pd.DataFrame):
        return data_frame[cls.name()]


class Mapper(Maker):
    def __init__(self, lineage: List[str], fields: Tuple[Union[SourceField, Target]]):
        super().__init__(lineage)
        self.fields = fields

    def remap(self, target_dir: Union[Path, str]) -> RemappedFile:
        df = pd.DataFrame()
        pass


class FixedWidthMapper(Mapper):
    def __init__(self, lineage: List[str], fields: List[Union[FixedWidthSource, Target]]):
        super().__init__(lineage, fields)

    def remap(self, target_dir: Union[Path, str], sample_size=0) -> RemappedFile:
        name = Path(self.source.name).with_suffix('.parquet')
        p = Path(target_dir, self.guid.hex + '.parquet')

        print(f"Counting rows in {self.source.file_path}")
        if sample_size:
            total = sample_size
        else:
            with self.source.file_path.open() as r:
                total = sum(1 for _ in r)
        print(f"Found {total:,} rows in {self.source.file_path}")

        fd = {x: [] for x in self.fields if issubclass(x, SourceField)}
        print(f"Extracting raw data from {self.source.file_path}")
        with self.source.file_path.open() as r:
            for ix, line in enumerate(tqdm(r, total=total)):
                if sample_size and ix > sample_size:
                    break
                if not line.isspace():
                    for k, v in fd.items():
                        fd[k].append(k.parse_from_row(line))

        new_keys = [x.name() for x in fd.keys()]
        fd = dict(zip(new_keys, fd.values()))
        df = pd.DataFrame.from_dict(fd)

        df.to_parquet(p)
        h = sha256()
        h.update(p.read_bytes())
        return RemappedFile(name, self.source, h, p, self.guid)
