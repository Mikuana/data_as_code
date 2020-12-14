from typing import Union
from dataclasses import dataclass

from data_as_code import __typing as th
from data_as_code.recipe import Recipe
from data_as_code.artifact import Source, Intermediary


@dataclass
class Inputs:
    """Class for keeping track of an item in inventory."""
    recipe: Recipe

    def materialize_inputs(self):
        # noinspection PyUnresolvedReferences
        for k in self.__dataclass_fields__.keys():
            if k == 'recipe':
                continue
            self.__setattr__(k, self.artifact(self.__getattribute__(k)))

    def artifact(self, *args: str) -> Union[Source, Intermediary]:
        """
        Get Descendent

        Descend lineage names to select the Artifact which matches the specified
        chain from the available Artifacts.
        """
        lineage = [*args]
        candidates = [x.is_descendent(*lineage) for x in self.recipe.artifacts]
        if sum(candidates) == 1:
            return self.recipe.artifacts[candidates.index(True)]
        elif sum(candidates) > 1:
            # TODO: this needs to give more hints to assist resolution
            raise Exception("Lineage matches multiple candidates")
        else:
            raise Exception(
                "Lineage does not match any candidate" + '\n',
                f"{lineage}" + "\n",
                f"{self.recipe.artifacts}"
            )