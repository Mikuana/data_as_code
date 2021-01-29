import json
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Union, List

from data_as_code._metadata import Metadata


class Keep:
    def __init__(self, **kwargs: bool):
        self.product = kwargs.pop('product', True)
        self.metadata = kwargs.pop('metadata', True)
        self.recipe = kwargs.pop('recipe', True)
        self.artifacts = kwargs.pop('artifacts', False)
        self.workspace = kwargs.pop('workspace', False)

        if kwargs:
            raise KeyError(f"Received unexpected keywords {list(kwargs.keys())}")


class Recipe:
    workspace: Union[str, Path]
    _td: TemporaryDirectory

    def __init__(self, destination: Union[str, Path] = '.', keep=Keep()):
        self.destination = Path(destination)
        self.artifacts: List[Metadata] = []
        self.products: List[Metadata] = []
        self.keep = keep

    def begin(self):
        if self.keep.workspace is False:
            self._td = TemporaryDirectory()
            self.workspace = self._td.name
        else:
            self.workspace = self.destination

    def end(self):
        self._package()

        if self.keep.workspace is False:
            self._td.cleanup()
        elif self.keep.artifacts is False:
            for a in self.artifacts:
                a.path.unlink()

    def __enter__(self):
        self.begin()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.end()

    def get_artifact(self, *args: str) -> Metadata:
        lineage = [*args]
        candidates = [x.is_descendent(*lineage) for x in self.artifacts]
        if sum(candidates) == 1:
            return self.artifacts[candidates.index(True)]
        elif sum(candidates) > 1:
            raise Exception("Lineage matches multiple candidates")
        else:
            raise Exception(
                "Lineage does not match any candidate" + '\n',
                f"{lineage}" + "\n",
                f"{[x.name for x in self.artifacts]}"
            )

    def _package(self):
        # move products from working folder to destination and update metadata
        for p in self.products:
            p.path = p.path.rename(Path(self.destination, p.path))
            Path(p.path.parent, 'meta.json').write_text(
                json.dumps(p.to_dict(), indent=2)
            )
