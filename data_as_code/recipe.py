import json
import gzip
import shutil
import subprocess
import sys
import tarfile
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Union, List

from data_as_code.metadata import Metadata


class Keep:
    def __init__(self, **kwargs: bool):
        self.product = kwargs.pop('product', True)
        self.metadata = kwargs.pop('metadata', True)
        self.recipe = kwargs.pop('recipe', True)
        self.archive = kwargs.pop('archive', True)
        self.destination = kwargs.pop('destination', False)
        self.artifacts = kwargs.pop('artifacts', False)
        self.workspace = kwargs.pop('workspace', False)

        if kwargs:
            raise KeyError(f"Received unexpected keywords {list(kwargs.keys())}")


class Recipe:
    workspace: Union[str, Path]
    _td: TemporaryDirectory

    def __init__(self, destination: Union[str, Path] = '.', keep=Keep()):
        self.destination = Path(destination)
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

    def __enter__(self):
        self.begin()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.end()

    def _package(self):
        structure = {
            'env/requirements.txt': self._package_env,
            'data/': self._package_data,
            'metadata/': self._package_metadata,
            'recipe.py': self._package_recipe
        }
        for k, v in structure.items():
            # noinspection PyArgumentList
            v(k)

        if self.keep.archive is True:
            tp = Path(self.destination.as_posix() + '.tar')
            with tarfile.open(tp, "w") as tar:
                for file in self.destination.rglob('*'):
                    tar.add(file, file.relative_to(self.destination))

            with gzip.open(tp.as_posix() + '.gz', 'wb') as f_out:
                f_out.write(tp.read_bytes())
            tp.unlink()

        if self.keep.destination is False:
            shutil.rmtree(self.destination)

    def designate_product(self, product: Metadata):
        self.products.append(product)

    def _package_env(self, target: str):
        reqs = subprocess.check_output([sys.executable, '-m', 'pip', 'freeze'])
        p = Path(self.destination, target)
        p.parent.mkdir(exist_ok=True, parents=True)
        p.write_bytes(reqs)

    def _package_recipe(self, target: str):
        Path(self.destination, target).write_bytes(Path(__file__).read_bytes())

    def _package_data_prep(self, target: str):
        p = Path(self.destination, target)
        for prod in self.products:
            pp = Path(p, prod.path.relative_to(prod._relative_to))
            pp.parent.mkdir(parents=True, exist_ok=True)
            yield prod, pp

    def _package_data(self, target: str):
        for prod, pp in self._package_data_prep(target):
            shutil.copy(prod.path, pp)

    def _package_metadata(self, target: str):
        for prod, pp in self._package_data_prep(target):
            d = prod.to_dict()
            j = json.dumps(d, indent=2)
            Path(pp.as_posix() + '.json').write_text(j)
