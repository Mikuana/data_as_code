import json
import logging
from hashlib import md5
from importlib import resources
from pathlib import Path
from typing import List, Union

from data_as_code._schema import validate_metadata

log = logging.getLogger(__name__)

_schema = json.loads(resources.read_text('data_as_code', 'schema.json'))
"""JSON schema definition which can be used to validate the structure of
Metadata that has been exported.
"""


class _Meta:
    schema = _schema.copy()

    def __init__(
            self, lineage: Union[List['_Meta'], List[str]] = None,
            fingerprint: str = None
    ):
        if lineage:
            self.lineage = lineage
        self._cached_fingerprint = fingerprint  # TODO: check against calculation

    def fingerprint(self) -> str:
        if self._cached_fingerprint:
            # TODO: enable this to work the way I want it to
            # assert self._cached_fingerprint == self._calculate_fingerprint(),  \
            #     "calculated fingerprint does not match cached. You're wrong"
            return self._cached_fingerprint
        else:
            self._cached_fingerprint = self._calculate_fingerprint()
            return self._cached_fingerprint

    def _calculate_fingerprint(self):
        d = self._meta_dict()
        if not d:
            log.error('Attempting to calculate fingerprint for empty metadata')
        return md5(json.dumps(self._meta_dict()).encode('utf8')).hexdigest()[:8]

    def _meta_dict(self) -> dict:
        raise Exception  # method stub for subclasses

    def to_dict(self) -> dict:
        d = self._meta_dict()
        d['fingerprint'] = self.fingerprint()
        return d

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

    def _meta_dict(self) -> dict:
        d = {}
        if self.path:
            d['path'] = self.path.as_posix()
        if self.description:
            d['description'] = self.description
        if self.lineage:
            d['lineage'] = self.prep_lineage()
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

    def _meta_dict(self) -> dict:
        d = {}
        if self.checksum:
            d['checksum'] = self.checksum
        if self.lineage:
            d['lineage'] = self.prep_lineage()
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
        d = super().to_dict()
        validate_metadata(d)
        if d:
            return d
        else:
            return

    def _meta_dict(self) -> dict:
        d = {
            'codified': self.codified.to_dict() if self.codified else None,
            'derived': self.derived.to_dict() if self.derived else None,
        }
        if self.lineage:
            d['lineage'] = sorted(
                [y.to_dict() for y in self.lineage],
                key=lambda x: x['fingerprint']
            )

        return {k: v for k, v in d.items() if v}

    @classmethod
    def from_dict(cls, metadata: dict) -> 'Metadata':
        validate_metadata(metadata)

        dl = [cls.from_dict(x) for x in metadata.get('lineage', [])]
        dc = metadata.get('codified', {})
        dd = metadata.get('derived', {})
        di = metadata.get('incidental', {})

        assert len(dl) == len(dc.get('lineage', [])), \
            "length of Metadata lineage node is not equal to the length " \
            "of lineage fingerprints array in the Codified lineage sub-node"

        s1 = set([x.codified.fingerprint() for x in dl])
        s2 = set(dc.get('lineage', []))
        diff = sorted(s1.symmetric_difference(s2))

        assert not diff, \
            "the following fingerprints are present in either " \
            "the Metadata lineage codified sub-node, or in the " \
            "Codified lineage fingerprints array, but not both\n" \
            f"{diff}"

        if dd:
            assert len(dl) == len(dd.get('lineage', [])), \
                "length of Metadata lineage node is not equal to the" \
                "length of lineage fingerprints array in the derived " \
                "lineage sub-node"

            s1 = set([x.derived.fingerprint() for x in dl])
            s2 = set(dd.get('lineage', []))
            diff = sorted(s1.symmetric_difference(s2))
            assert not diff, \
                "the following fingerprints are present in either " \
                "the Metadata lineage derived sub-node, or in the " \
                "derived lineage fingerprints array, but not both\n" \
                f"{diff}"

        mc, md, mi = Codified(**dc), Derived(**dd), Incidental(**di)
        return cls(codified=mc, derived=md, incidental=mi, lineage=dl)
