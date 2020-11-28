from typing import Tuple
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
