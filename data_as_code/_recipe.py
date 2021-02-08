import shutil

import gzip
import json
import tarfile
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Union, List

from data_as_code._metadata import Metadata, Product


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

    def _package(self):
        # move products from working folder to destination and update metadata
        fn = 'recipe'
        meta = []

        # # TODO: make tarball/gzip or zip optional
        # tp = Path(self.destination, fn + '.tar')
        # with tarfile.open(tp, "w") as tar:
        #     for p in self.products:
        #         tar.add(p.path)
        #         p = Product.repackage(p, self.destination)  # TODO: dont move
        #         meta.append(p.to_dict())
        #
        #     p = Path(self.destination, 'metadata.json')
        #     p.write_text(json.dumps(meta, indent=2))
        #     tar.add(p)
        #
        # with gzip.open(Path(tp.parent, tp.name + '.gz'), 'wb') as f_out:
        #     f_out.write(tp.read_bytes())

    def designate_product(self, product: Metadata):
        self.products.append(product)
