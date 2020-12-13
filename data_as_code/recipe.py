from tempfile import TemporaryDirectory
from data_as_code import __typing as th


class Recipe:
    artifacts: th.artifacts = None
    _temp_dir: TemporaryDirectory = None

    def __init__(self, working_directory: th.file_path = None):
        self.wd = working_directory
        self.artifacts = []

    def __enter__(self):
        if not self.wd:
            self._temp_dir = TemporaryDirectory()
            self.wd = self._temp_dir.name
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._temp_dir:
            self._temp_dir.cleanup()
