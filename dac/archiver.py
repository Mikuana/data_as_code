from uuid import uuid4
from hashlib import sha256
from pathlib import Path
from typing import Union, Generator
from zipfile import ZipFile

from dac.source import UnpackedArchive, RetrievedFile
from dac.other import Maker


class Archiver(Maker):
    def unpack(self, target_dir: Union[Path, str]) -> Generator[UnpackedArchive, None, None]:
        with ZipFile(self.source.file_path) as zf:
            xd = Path(target_dir, self.source.guid.hex)
            zf.extractall(xd)
            for file in xd.rglob('*'):
                h = sha256()
                h.update(file.read_bytes())
                yield UnpackedArchive(file.name, self.source, h, file, uuid4())
