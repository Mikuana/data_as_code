import requests
from hashlib import sha256
from pathlib import Path
from tqdm import tqdm
from typing import Union
from uuid import uuid4

from dac.source import RetrievedFile
from dac.other import Maker


class Retriever(Maker):
    name: str = None

    def retrieve(self, target_dir: Union[Path, str]) -> RetrievedFile:
        pass


class GetHTTP(Retriever):
    def __init__(self, url, name: str = None, archived=False):
        self.url = url
        self.name = name or Path(self.url).name
        self.archived = archived
        self.guid = uuid4()

    def retrieve(self, target_dir: Union[Path, str]) -> RetrievedFile:
        tp = Path(target_dir, self.guid.hex + Path(self.name).suffix)
        try:
            print('Downloading from URL:\n' + self.url)
            response = requests.get(self.url, stream=True)
            context = dict(
                total=int(response.headers.get('content-length', 0)),
                desc=self.name, miniters=1
            )
            with tp.open('wb') as f:
                with tqdm.wrapattr(f, "write", **context) as stream:
                    for chunk in response.iter_content(chunk_size=4096):
                        stream.write(chunk)

        except requests.HTTPError as te:
            print(f'HTTP error while attempting to download: {self.url}')
            raise te

        h = sha256()
        h.update(tp.read_bytes())
        return RetrievedFile(self.name, self.url, h, tp.absolute(), self.guid, self.archived)
