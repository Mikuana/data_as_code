"""
Functions to generate premade steps

This submodule contains a set of functions with limited parameters, which are
used to generate pre-made Step classes. These are intended to handle
"undifferentiated heavy lifting", where the same basic tasks are repeated over
and over again, but to handle it in a way which brings the advantages of the
data-as-code framework, including the tracking of metadata, and caching of
artifacts.
"""
import inspect
import logging
import shutil
import urllib.error
import urllib.request
from hashlib import md5
from pathlib import Path
from typing import Union, Type

from data_as_code._metadata import Metadata
from data_as_code._step import Step, result

__all__ = [
    'source_local', 'source_http'
]


def source_local(path: Union[Path, str], keep=False) -> Type[Step]:
    """
    Source file from local system

    Read a file directly from the path specified on the local file system.

    :param path: a pathlib.Path or path-like string that can be resolved at
        execution.
    :param keep: a control of whether to copy the referenced file to the
        destination specified by the recipe.
    :return: a :class:`data_as_code.Step` class which will mange the reading of a local file
    """
    v_path = Path(path)
    v_keep = keep

    class PremadeSourceLocal(Step):
        """Source file from available file system."""
        output = v_path
        keep = v_keep

        def instructions(self):
            pass

        def _execute(self):  # TODO: this is all messed up
            if self.check_cache():
                return self
            else:
                return self._make_metadata()

        def _make_metadata(self) -> Metadata:
            rp = Path('data', self.output.name)
            if self.keep is True:
                ap = Path(self.destination, rp)
                ap.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy(self.output.absolute(), ap)
            else:
                ap = self.output.absolute()

            return Metadata(
                absolute_path=ap, relative_path=rp,
                checksum_value=md5(self.output.read_bytes()).hexdigest(),
                checksum_algorithm='md5',
                lineage=[x for x in self._ingredients],
                step_description=self.__doc__,
                step_instruction=inspect.getsource(self.instructions)
            )

    return PremadeSourceLocal


def source_http(url: str, keep=False) -> Type[Step]:
    """
    Source file from HTTP download

    Download a file from the specified URL.

    :param url: a URL which can be accessed directly via GET at execution, with
        the need for authentication
    :param keep: a control of whether to cache the downloaded file to the
        Recipe destination.
    :return: a :class:`data_as_code.Step` class which will mange the download of
        a file via HTTP
    """
    v_url = url
    v_keep = keep

    class PremadeSourceHTTP(Step):
        """Retrieve file from URL via HTTP."""
        output = result(Path(v_url).name)
        keep = v_keep

        _url = v_url
        _other_meta = dict(url=v_url)

        def instructions(self):
            try:
                logging.info('Downloading from URL: ' + self._url)
                filename, headers = urllib.request.urlretrieve(
                    self._url, self.output.as_posix()
                )
                logging.debug(f'Saved to {self.output.as_posix()}')
                logging.info(
                    f'Downloaded {humanize(int(headers.get("Content-Length")))}'
                )
            except urllib.error.HTTPError as te:
                logging.error(f'HTTP error while attempting to download: {self._url}')
                raise te

    return PremadeSourceHTTP


def humanize(size, decimal_places=0):
    for unit in ['B', 'KiB', 'MiB', 'GiB', 'TiB']:
        if size < 1024.0:
            break
        size /= 1024.0
    return f"{size:.{decimal_places}f} {unit}"
