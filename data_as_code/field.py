import re
from typing import Tuple

import pandas as pd


class Handlers:
    """ Raw value handlers """

    @staticmethod
    def integer(x):
        return int(x) if x.strip() else None

    @staticmethod
    def character(x):
        return x.decode('utf-8')


class _Field:
    """ Base Field class """

    @classmethod
    def name(cls):
        return re.sub(r'(?<!^)(?=[A-Z])', '_', cls.__name__).lower()


class _SourceField(_Field):
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


class FixedWidthSource(_SourceField):
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


class Target(_Field):
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
