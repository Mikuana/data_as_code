from typing import Tuple, Union
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

    def is_descendent(self, *args: str):
        origin = self.origin
        for name in args:
            if issubclass(type(origin), Source) and origin.name == name:
                origin = origin.origin
            else:
                raise KeyError("does not exist")  # TODO: make better
        return True

@dataclass
class RetrievedFile(Source):
    guid: uuid4
    archived: bool


@dataclass
class UnpackedArchive(Source):
    origin: RetrievedFile


@dataclass
class RemappedFile(Source):
    origin: [RetrievedFile, UnpackedArchive]
    guid: uuid4
