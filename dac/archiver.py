from hashlib import sha256
from pathlib import Path
from typing import Union, Generator
from zipfile import ZipFile

from dac.source import UnpackedArchive, RetrievedFile


class Archiver:
    def __init__(self, archive: RetrievedFile):
        self.archive = archive

    def unpack(self, target_dir: Union[Path, str]) -> Generator[UnpackedArchive, None, None]:
        with ZipFile(self.archive.file_path) as zf:
            xd = Path(target_dir, self.archive.guid.hex)
            zf.extractall(xd)
            for file in xd.rglob('*'):
                h = sha256()
                h.update(file.read_bytes())
                yield UnpackedArchive(file.name, self.archive, h, file)
