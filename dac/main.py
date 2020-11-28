from pathlib import Path
from typing import Union, List

from dac.retriever import Retriever
from dac.archiver import Archiver
from dac.source import RetrievedFile, UnpackedArchive


class Processor:
    def __init__(self, working_directory: Union[Path, str] = None):
        self.working_directory = working_directory

        self.retrieved: List[RetrievedFile] = list()
        self.unpacked: List[UnpackedArchive] = list()

    def retrieve(self, *args: Retriever):
        for arg in args:
            self.retrieved.append(arg.retrieve(self.working_directory))

    def unpack(self, *args: Archiver):
        for arg in args:
            for i in arg.unpack(self.working_directory):
                self.unpacked.append(i)

    def package(self):
        pass

    def distribute(self):
        pass
