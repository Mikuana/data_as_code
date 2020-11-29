from typing import List, Union
from uuid import uuid4

from dac.source import Source


class Maker:
    def __init__(self, lineage: Union[str, List[str]]):
        self.guid = uuid4()
        self.lineage = [lineage] if isinstance(lineage, str) else lineage
        self.source: Source = None

    def source_descendent(self, sources: List[Source]):
        """
        Source Descendent

        Descend lineage names to select the source from available which matches
        the specified chain.
        """
        candidates = [x.is_descendent(*self.lineage) for x in sources]
        if sum(candidates) == 1:
            self.source = sources[candidates.index(True)]
        elif sum(candidates) > 1:
            raise Exception("Lineage matches multiple candidates")
        else:
            raise Exception("Lineage does not match any candidate")
