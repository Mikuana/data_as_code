from pathlib import Path
from typing import Union

from data_as_code.recipe import Recipe
from data_as_code.step import Step, _SourceLocal, _SourceHTTP

__all__ = [
    'source_local', 'source_http'
]


def source_local(recipe: Recipe, path: Union[Path, str], **kwargs) -> Step:
    return _SourceLocal(recipe, path, **kwargs)


def source_http(recipe: Recipe, url: str, **kwargs) -> Step:
    return _SourceHTTP(recipe, url, **kwargs)
