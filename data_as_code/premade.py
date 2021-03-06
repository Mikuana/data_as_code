import inspect
import shutil
from hashlib import md5
from pathlib import Path
from typing import Union, Type

import requests
from tqdm import tqdm

from data_as_code import Step
from data_as_code._metadata import Metadata


def source_local(path: Union[Path, str], keep=False) -> Type[Step]:
    v_path = Path(path)
    v_keep = keep

    class PremadeSourceLocal(Step):
        """Source file from available file system."""
        output = v_path
        keep = v_keep
        role = 'source'

        def instructions(self):
            pass

        def _execute(self):
            cached = self._check_cache()
            if cached:
                return cached
            else:
                return self._make_metadata()

        def _make_metadata(self) -> Metadata:
            rp = Path('data', self.role, self.output.name)
            if self.keep is True:
                ap = Path(self._destination, rp)
                ap.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy(self.output.absolute(), ap)
            else:
                ap = self.output.absolute()

            return Metadata(
                absolute_path=ap, relative_path=rp,
                checksum_value=md5(self.output.read_bytes()).hexdigest(),
                checksum_algorithm='md5',
                lineage=[x for x in self._ingredients],
                role=self.role, step_description=self.__doc__,
                step_instruction=inspect.getsource(self.instructions)
            )

    return PremadeSourceLocal


def source_http(url: str, keep=False) -> Type[Step]:
    v_url = url
    v_keep = keep

    class PremadeSourceHTTP(Step):
        """Retrieve file from URL via HTTP."""
        output = Path(Path(v_url).name)
        keep = v_keep
        role = 'source'

        _url = v_url
        _other_meta = dict(url=v_url)

        def instructions(self):
            try:
                print('Downloading from URL:\n' + self._url)
                response = requests.get(self._url, stream=True)
                context = dict(
                    total=int(response.headers.get('content-length', 0)),
                    desc=self.output.name, miniters=1
                )
                with self.output.open('wb') as f:
                    with tqdm.wrapattr(f, "write", **context) as stream:
                        for chunk in response.iter_content(chunk_size=4096):
                            stream.write(chunk)

            except requests.HTTPError as te:
                print(f'HTTP error while attempting to download: {self._url}')
                raise te

    return PremadeSourceHTTP
