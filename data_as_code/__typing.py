from pathlib import Path
from typing import List, Union

from data_as_code.artifact import Source, Intermediary

lineages = Union[str, List[str]]
artifacts = List[Union[Source, Intermediary]]
file_path = Union[str, Path]
