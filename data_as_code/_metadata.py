"""
Data as Code Metadata

A key concept of managing *data as code* is metadata. That is to say, the data
*about* the data must be understood and captured in a way that allows the
package to evaluate data artifacts. This evaluation serves as a check for
consistency and continuity of the artifacts, and provides a means of
sophisticated handling of artifacts during data processing.

Metadata in this package is divided into three sub-categories:

#. **codified**: metadata which are entirely expressed within the code, and do not
   require actual data artifacts. In other words, codified metadata can be
   completely fabricated from a script, even for non-existent data.
#. **derived**: metadata which are collected during runtime and processing of
   data artifacts, which cannot be expressed in code without replicating the
   actual data in part, or whole. In other words, derived metadata are only
   obtainable when executing a recipe. Ideally, these metadata will are
   deterministic, and every execution of a recipe with the same **codified**
   metadata will result in the same **derived** metadata. This is not an actual
   requirement, but any non-deterministic step in a recipe will limit the more
   advanced features of this package.
#. **incidental**: metadata which are derived at runtime, but which are
   considered to be more of a side-effect than an actual derivative of the data
   artifact. An example of this is timestamps; while the start time or duration
   of recipe execution *could* be meaningful, it is effectively guaranteed to
   change with each execution, even when the resulting data artifacts are
   identical in content and context for a previous run. Because of the limited
   usefulness of these metadata, they are largely ignored by the package and
   stored primarily for user reference.

There is also special consideration for **lineage**, which is a concept that
builds metadata in a recursive manner to ensure that the context of a data
artifact is treated as a first-class citizen.
"""
import json
import logging
from hashlib import md5
from importlib import resources
from pathlib import Path
from typing import List, Union

from data_as_code._schema import validate_metadata
from data_as_code.exceptions import InvalidFingerprint

log = logging.getLogger(__name__)

_schema = json.loads(resources.read_text('data_as_code', 'schema.json'))
"""JSON schema definition which can be used to validate the structure of
Metadata that has been exported.
"""


class _Meta:
    """
    Base metadata class

    Provides the basic framework for handling of complete, and sub-category
    metadata as objects.

    :param lineage: TODO
    :param fingerprint: TODO
    """
    schema = _schema.copy()

    def __init__(
            self, lineage: Union[List['_Meta'], List[str]] = None,
            fingerprint: str = None
    ):
        if lineage:
            self.lineage = lineage
        self._expected = fingerprint

    def fingerprint(self) -> str:
        """
        View Fingerprint

        Return the 8 character fingerprint, which is a deterministic identifier
        of the metadata contained in this object.
        """
        return self.to_dict()['fingerprint']

    def _fingerprinter(self, rendered: dict) -> str:
        """
        Metadata fingerprint

        Calculate an 8 character hexadecimal string by performing an md5 hash
        sum calculation against specific attributes of the metadata class
        (rendered into a JSON string). This includes a check against an expected
        fingerprint stored in a cache - if that is provided during object
        construction - which raises an error if the calculated fingerprint does
        not match.

        This is a deterministic function, which relies upon the consistency of
        dictionaries provided by the to_dict function, which is overwritten
        in each metadata subclass type.

        :param rendered: (optional) argument to private a dictionary object
            instead of calling the dictionary output of self, which lets us
            avoid calling the dictionary output method multiple times
        :return: an 8 character hexadecimal checksum string which uniquely
            identifies the contents of a metadata object
        """
        d = rendered
        if not d:
            log.error('Attempting to calculate fingerprint for empty metadata')
        calc = md5(json.dumps(d).encode('utf8')).hexdigest()[:8]

        if self._expected:
            if self._expected != calc:
                raise InvalidFingerprint(
                    f"Expected fingerprint {self._expected}, but calculation "
                    f"of metadata fingerprint returned {calc}"
                )
            return self._expected
        else:
            return calc

    def to_dict(self) -> dict:
        """
        Render metadata to dictionary

        Used to provide consistent ordering and formatting of python objects for
        the ultimate purpose of exporting to JSON.

        :return: a specifically ordered dictionary, with keys and values
            formatted in a JSON-friendly way.
        """
        raise Exception  # exception stub for subclasses

    def prep_lineage(self) -> List[str]:
        if all([isinstance(x, str) for x in self.lineage]):
            return sorted(self.lineage)
        else:
            return sorted([x.fingerprint() for x in self.lineage])

    def sub_schema(self) -> dict:
        s = _Meta.schema.copy()
        s['required'] = s['properties'][self.__class__.__name__.lower()]['required']
        s['properties'] = s['properties'][self.__class__.__name__.lower()]['properties']
        return s


class Codified(_Meta):
    def __init__(
            self, path: Union[Path, str] = None,
            description: str = None, instruction: str = None,
            lineage: Union[List['Metadata'], List['Codified'], List[str]] = None,
            **kwargs
    ):
        self.schema = self.sub_schema()
        self.path = Path(path) if isinstance(path, str) else path
        self.description = description
        self.lineage = lineage
        if self.lineage:
            self.lineage = [
                x.codified if isinstance(x, Metadata) else x for x in lineage
            ]

        super().__init__(**kwargs)

    def to_dict(self) -> dict:
        d = {}
        if self.path:
            d['path'] = self.path.as_posix()
        if self.description:
            d['description'] = self.description
        if self.lineage:
            d['lineage'] = self.prep_lineage()

        d['fingerprint'] = self._fingerprinter(d)
        return d


class Derived(_Meta):
    lineage: Union[List['Metadata'], List['Derived']] = None

    def __init__(
            self,
            checksum: str = None,
            lineage: Union[List['Metadata'], List['Derived'], List[str]] = None,
            **kwargs
    ):
        self.schema = self.sub_schema()
        self.checksum = checksum
        super().__init__(**kwargs)

        if lineage:
            self.lineage = [x.derived if isinstance(x, Metadata) else x for x in lineage]

    def to_dict(self) -> dict:
        d = {}
        if self.checksum:
            d['checksum'] = self.checksum
        if self.lineage:
            d['lineage'] = self.prep_lineage()

        d['fingerprint'] = self._fingerprinter(d)
        return d


class Incidental(_Meta):
    def __init__(
            self,
            path: Union[Path, str] = None,
            directory: Union[Path, str] = None,
            usage: str = None,
            **kwargs
    ):
        self.path = Path(path) if isinstance(path, str) else path
        self.directory = Path(directory) if isinstance(directory, str) else directory
        self.usage = usage
        self.other = kwargs
        super().__init__(**kwargs)

    def to_dict(self) -> Union[dict, None]:
        d = {
            k: v for k, v in
            sorted(self.other.items(), key=lambda item: item[1], reverse=True)
        }
        if d:
            return d
        else:
            return


class Metadata(_Meta):
    def __init__(
            self,
            codified: Codified = None,
            derived: Derived = None,
            incidental: Incidental = None,
            lineage: List['Metadata'] = None,
            **kwargs
    ):
        self.codified = codified
        self.derived = derived
        self.incidental = incidental
        self.lineage = lineage
        super().__init__(**kwargs)

    def to_dict(self) -> Union[dict, None]:
        d = {}
        if self.codified:
            d['codified'] = self.codified.to_dict()
        if self.derived:
            d['derived'] = self.derived.to_dict()
        if self.lineage:
            d['lineage'] = sorted(
                [y.to_dict() for y in self.lineage],
                key=lambda x: x['fingerprint']
            )

        d = {k: v for k, v in d.items() if v}
        d['fingerprint'] = self._fingerprinter(d)
        validate_metadata(d)
        if d:
            return d
        else:
            return

    @classmethod
    def from_dict(cls, metadata: dict) -> 'Metadata':
        validate_metadata(metadata)

        dl = [cls.from_dict(x) for x in metadata.get('lineage', [])]
        dc = metadata.get('codified', {})
        dd = metadata.get('derived', {})
        di = metadata.get('incidental', {})
        fp = metadata.get('fingerprint')

        mc, md, mi = Codified(**dc), Derived(**dd), Incidental(**di)
        return cls(
            codified=mc, derived=md, incidental=mi,
            lineage=dl, fingerprint=fp
        )
