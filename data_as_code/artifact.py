from hashlib import sha256
from pathlib import Path
from typing import Union
from uuid import uuid4


class _Artifact:
    """
    Data Artifact

    An objects which represents data, and provide a direct means of
    obtaining it, typically via file path.
    """

    def __init__(self, origin, file_path: Path, **kwargs):
        self.origin = origin
        self.file_path = file_path
        self.name: str = kwargs.get('name')
        self.notes: str = kwargs.get('notes')

        self.guid = uuid4()
        h256 = sha256()
        h256.update(self.file_path.read_bytes())
        self.file_hash = h256

    def is_descendent(self, *args: str):
        origin = self
        for name in args:
            if issubclass(type(origin), _Artifact) and origin.name == name:
                origin = origin.origin
            elif isinstance(origin, str) and origin == name:
                origin = None
            else:
                return False
        return True

    def digest(self):
        return dict(
            name=self.name,
            file_path=self.file_path.as_posix(),
            file_hash=self.file_hash.hexdigest(),
            origin=self.origin.digest() if isinstance(self.origin, _Artifact) else self.origin
        )


class MockSource(_Artifact):
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
            origin=self.origin.digest() if isinstance(self.origin, _Artifact) else self.origin
        )


class Source(_Artifact):
    """
    Source

    Primary data artifact. The "original" data that is used by a recipe, before
    it has been changed in any way.
    """

    def __init__(self, origin: [str, MockSource], file_path: Path, **kwargs):
        super().__init__(origin=origin, file_path=file_path, **kwargs)


class _Intermediary(_Artifact):
    """
    Intermediary placeholder

    This is just here to allow appropriate self-referential type-hinting in the
    Intermediary artifact class.
    """
    pass


class Intermediary(_Artifact):
    """
    Intermediary

    An intermediate data artifact that is the result of applying incremental
    changes to a Source, but not yet the final data Product produced by the
    recipe. The artifact is not meant to be used outside of the recipe, and
    treated as disposable.
    """

    def __init__(self, origin: Union[Source, _Intermediary], file_path: Path, **kwargs):
        super().__init__(origin=origin, file_path=file_path, **kwargs)


class Product(_Artifact):
    """
    Product

    The ultimate data artifact produced by a recipe, which is intended for use
    outside the recipe. Includes the complete lineage as a component of the
    packaged product, and optionally includes the recipe that was used to create
    it.
    """

    def __init__(self, origin: Union[Source, Intermediary], file_path: Path, **kwargs):
        super().__init__(origin=origin, file_path=file_path, **kwargs)
