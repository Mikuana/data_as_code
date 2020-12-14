from typing import Union

from data_as_code.artifact import _Artifact, Recipe, Source, Intermediary


class Lineage(_Artifact):
    # noinspection PyMissingConstructor
    def __init__(self, *args: str):
        self.lineage = args

    def artifact(self, recipe: Recipe) -> Union[Source, Intermediary]:
        candidates = [x.is_descendent(*self.lineage) for x in recipe.artifacts]
        if sum(candidates) == 1:
            return recipe.artifacts[candidates.index(True)]
        elif sum(candidates) > 1:
            # TODO: this needs to give more hints to assist resolution
            raise Exception("Lineage matches multiple candidates")
        else:
            raise Exception(
                "Lineage does not match any candidate" + '\n',
                f"{self.lineage}" + "\n",
                f"{recipe.artifacts}"
            )
