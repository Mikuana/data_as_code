from pathlib import Path
from typing import Union, Type

import requests
from tqdm import tqdm

from data_as_code._recipe import Recipe
from data_as_code._step import Step, _SourceStep, _SourceLocal

__all__ = [
    'source_local', 'source_http'
]


def source_local(recipe: Recipe, path: Union[Path, str], keep=False) -> Step:
    return _SourceLocal(recipe, path, keep=keep)


def source_http(url: str, keep=False) -> Type[Step]:
    v_url = url
    v_keep = keep

    class PremadeSourceHTTP(_SourceStep):
        """Retrieve file from URL via HTTP."""
        output = Path(Path(v_url).name)
        keep = v_keep
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
