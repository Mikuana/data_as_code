from pathlib import Path
from typing import Union

from data_as_code._step import Step, _SourceLocal, _SourceHTTP
from data_as_code.recipe import Recipe

__all__ = [
    'source_local', 'source_http'
]


def source_local(recipe: Recipe, path: Union[Path, str]) -> Step:
    return _SourceLocal(recipe, path)


def source_http(recipe: Recipe, url: str) -> Step:
    return _SourceHTTP(recipe, url)
