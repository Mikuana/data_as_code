from pathlib import Path
from typing import Union, List

from data_as_code.worker import _Retriever, Unzip, _Parser
from data_as_code.source import Source


class Processor:
    def __init__(self, working_directory: Union[Path, str] = None):
        self.working_directory = working_directory

        self.sources: List[Source] = list()

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
