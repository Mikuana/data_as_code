from pathlib import Path
from typing import List, Union

from data_as_code.recipe import Recipe
from data_as_code.artifact import Source, Intermediary, _Artifact

lineages = Union[str, List[str]]
ain = Union[Source, Intermediary]
ains = List[Union[Source, Intermediary]]
file_path = Union[str, Path]


class Lineage(object, _Artifact):
    def __init__(self, *args: str):
        self.lineage = args

    def artifact(self, recipe: Recipe) -> Union[Source, Intermediary]:
        candidates = [x.is_descendent(*self.lineage) for x in recipe.artifacts]
        if sum(candidates) == 1:
            return self.recipe.artifacts[candidates.index(True)]
        elif sum(candidates) > 1:
            # TODO: this needs to give more hints to assist resolution
            raise Exception("Lineage matches multiple candidates")
        else:
            raise Exception(
                "Lineage does not match any candidate" + '\n',
                f"{self.lineage}" + "\n",
                f"{self.recipe.artifacts}"
            )
