from pathlib import Path
from typing import Union, List

from data_as_code.artifact import Artifact
from data_as_code.processor import _Retriever, Unzip, _Parser


class Processor:
    def __init__(self, working_directory: Union[Path, str] = None):
        self.working_directory = working_directory

        self.sources: List[Artifact] = list()

    def retrieve(self, *args: _Retriever):
        for arg in args:
            self.sources.append(arg.retrieve(self.working_directory))

    def unpack(self, *args: Unzip):
        for arg in args:
            arg.source_descendent(self.sources)
            for i in arg.unpack(self.working_directory):
                self.sources.append(i)

    def remap(self, *args: _Parser):
        for arg in args:
            arg.source_descendent(self.sources)
            self.sources.append(arg.remap(self.working_directory))

    def package(self):
        pass

    def distribute(self):
        pass


class Lineage:
    pass


class Recipe:
    pass


class Product:
    def __init__(self, file_path: Path, lineage: Lineage, recipe: Recipe = None):
        self.file_path = file_path
        self.lineage = lineage
        self.recipe = recipe

    def load(self):
        pass
