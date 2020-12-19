from hashlib import sha256
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Union, List
from uuid import uuid4


class Artifact:
    """
    Data Artifact

    An objects which represents data, and provide a direct means of
    obtaining it, typically via file path.
    """

    def __init__(self, origin, file_path: Path, rename=True, **kwargs):
        self.origin = origin
        self.file_path = file_path
        self.name: str = kwargs.get('name')
        self.notes: str = kwargs.get('notes')

        self.guid = uuid4()
        h256 = sha256()
        h256.update(self.file_path.read_bytes())
        self.file_hash = h256

        # if rename:
        #     self._rename_to_hash()

    def _rename_to_hash(self):
        self.file_path = self.file_path.rename(
            Path(
                self.file_path.parent,
                self.file_hash.hexdigest()[:8] + self.file_path.suffix
            )
        )

    def is_descendent(self, *args: str):
        origin = [self]
        # TODO: needs to be able to handle lists of origins
        for name in args:
            for o in origin:
                if issubclass(type(o), Artifact) and o.name == name:
                    origin = o.origin if isinstance(o.origin, list) else [o.origin]
                    break
                elif isinstance(origin, str) and o == name:
                    origin = None
                else:
                    return False

        return True

    def digest(self):
        return dict(
            name=self.name,
            file_path=self.file_path.as_posix(),
            file_hash=self.file_hash.hexdigest(),
            origin=self.origin.digest() if isinstance(self.origin, Artifact) else self.origin
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
            origin=self.origin.digest() if isinstance(self.origin, Artifact) else self.origin
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
        super().__init__(origin=origins, file_path=file_path, **kwargs)


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
ain = Union[Source, Intermediary]
ains = List[Union[Source, Intermediary]]


class Recipe:
    artifacts: ains = None
    _temp_dir: TemporaryDirectory = None

    def __init__(self, working_directory: Union[str, Path] = None):
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


class Input(Artifact):
    # noinspection PyMissingConstructor
    def __init__(self, *args: str):
        self.lineage = args

    def artifact(self, recipe: Recipe) -> Artifact:
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
