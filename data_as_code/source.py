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
    notes: str

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

    def digest(self):
        return dict(
            name=self.name,
            file_path=self.file_path.as_posix(),
            file_hash=self.file_hash.hexdigest(),
            origin=self.origin.digest() if isinstance(self.origin, Source) else self.origin
        )


class Intermediary(Source):
    pass
