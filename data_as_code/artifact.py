from hashlib import sha256
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Union, List, Dict
from uuid import uuid4


class Artifact:
    """
    Data Artifact

    An objects which represents data, and provide a direct means of
    obtaining it, typically via file path.
    """

    def __init__(self, origins, file_path: Path, **kwargs):
        self.origins: list = origins
        self.file_path = file_path
        self.name: str = kwargs.get('name')
        self.notes: str = kwargs.get('notes')

        self.guid = uuid4()
        h256 = sha256()
        h256.update(self.file_path.read_bytes())
        self.file_hash = h256

    def is_descendent(self, *args: str) -> bool:
        if self.name == args[0]:
            if not args[1:]:
                return True
            elif len(args) == 2 and args[1] is None and self.origins == []:
                return True
            else:
                for o in self.origins:
                    if issubclass(type(o), Artifact):
                        if o.is_descendent(*args[1:]):
                            return True
        return False

    def digest(self):
        return dict(
            name=self.name,
            file_path=self.file_path.as_posix(),
            file_hash=self.file_hash.hexdigest(),
            origins=[x.digest() if isinstance(x, Artifact) else x for x in self.origins]
        )


class MockSource(Artifact):
    """
    Mock Source

    A lineage Artifact which precedes a Source, but which is not actually
    available for use by the Recipe. Allows for a more complete lineage to be
    declared, when appropriate.
    """

    def __init__(self, origin: str, name: str, notes: str):
        skwargs = dict(
            origin=origin, name=name, notes=notes,
            file_path=None, file_hash=None
        )
        super().__init__(**skwargs)

    def digest(self):
        return dict(
            name=self.name,
            origin=self.origins.digest() if isinstance(self.origins, Artifact) else self.origins
        )


class Source(Artifact):
    """
    Source

    Primary data artifact. The "original" data that is used by a recipe, before
    it has been changed in any way.
    """

    def __init__(self, origin: Union[str, MockSource], file_path: Path, **kwargs):
        super().__init__(origin=origin, file_path=file_path, **kwargs)


_th_origins = Union[Artifact, List[Artifact]]


class Intermediary(Artifact):
    """
    Intermediary

    An intermediate data artifact that is the result of applying incremental
    changes to a Source, but not yet the final data Product produced by the
    recipe. The artifact is not meant to be used outside of the recipe, and
    treated as disposable.
    """

    def __init__(self, origins: _th_origins, file_path: Path, **kwargs):
        super().__init__(origins=origins, file_path=file_path, **kwargs)


class Product(Artifact):
    """
    Product

    The ultimate data artifact produced by a recipe, which is intended for use
    outside the recipe. Includes the complete lineage as a component of the
    packaged product, and optionally includes the recipe that was used to create
    it.
    """

    def __init__(self, origins: _th_origins, file_path: Path, **kwargs):
        super().__init__(origin=origins, file_path=file_path, **kwargs)


lineages = Union[str, List[str]]
_th_artifact = Union[Source, Intermediary]
_th_artifacts = List[_th_artifact]


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
        self.artifacts: List[Artifact] = []
        self.products: List[Product] = []
        self.keep = keep

    def begin(self):
        if self.keep.workspace is False:
            self._td = TemporaryDirectory()
            self.workspace = self._td.name
        else:
            self.workspace = self.destination

    def end(self):
        if self.keep.workspace is False:
            self._td.cleanup()
        elif self.keep.artifacts is False:
            for a in self.artifacts:
                a.file_path.unlink()

    def __enter__(self):
        self.begin()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.end()

    def get_artifact(self, *args: str) -> Artifact:
        lineage = [*args]
        candidates = [x.is_descendent(*lineage) for x in self.artifacts]
        if sum(candidates) == 1:
            return self.artifacts[candidates.index(True)]
        elif sum(candidates) > 1:
            raise Exception("Lineage matches multiple candidates")
        else:
            raise Exception(
                "Lineage does not match any candidate" + '\n',
                f"{lineage}" + "\n",
                f"{self.artifacts}"
            )


class InputArtifact(Artifact):
    # noinspection PyMissingConstructor
    def __init__(self, *args: str):
        self.lineage = args
