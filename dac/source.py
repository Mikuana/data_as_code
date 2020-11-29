from typing import Union
from dataclasses import dataclass

from hashlib import sha256
from pathlib import Path
from uuid import uuid4


@dataclass
class Source:
    name: str
    origin: str
    file_hash: sha256
    file_path: Path
    guid: uuid4

    def is_descendent(self, *args: str):
        origin = self
        for name in args:
            if issubclass(type(origin), Source) and origin.name == name:
                origin = origin.origin
            elif isinstance(origin, str) and origin == name:
                origin = None
            else:
                return False
        return True


@dataclass
class RetrievedFile(Source):
    archived: bool


@dataclass
class UnpackedArchive(Source):
    origin: RetrievedFile


@dataclass
class RemappedFile(Source):
    origin: [RetrievedFile, UnpackedArchive]


class Descendent:
    def __init__(self, *args: str):
        self.lineage = args
