import json
from hashlib import md5
from pathlib import Path
from typing import List, Union


class _Meta:
    lineage: List['_Meta'] = None

    @staticmethod
    def prep_fingerprint(d: Union[dict, list]) -> str:
        return md5(json.dumps(d).encode('utf8')).hexdigest()

    def to_dict(self) -> dict:
        return {}

    def prep_lineage(self) -> List[str]:
        return sorted([x.to_dict()['fingerprint'] for x in self.lineage])


class Codified(_Meta):
    def __init__(
            self, path: Path = None,
            description: str = None, instruction: str = None,
            lineage: Union[List['Metadata'], List['Codified']] = None,
    ):
        self.path = path
        self.description = description
        self.instruction = instruction

        if lineage:
            self.lineage = [
                x.codified if isinstance(x, Metadata) else x for x in lineage
            ]

    def to_dict(self) -> dict:
        d = {}
        if self.path:
            d['path'] = self.path.as_posix()
        if self.description:
            d['description'] = self.description
        if self.instruction:
            d['instruction'] = self.instruction
        if self.lineage:
            d['lineage'] = self.prep_lineage()

        d['fingerprint'] = self.prep_fingerprint(d)
        return d


class Derived(_Meta):
    def __init__(
            self,
            checksum: Union[str, None], algorithm: Union[str, None],
            lineage: List['Derived'] = None,
    ):
        self.checksum = checksum
        self.algorithm = algorithm

        if lineage:
            self.lineage = [x.codified if isinstance(x, Metadata) else x for x in lineage]

    def to_dict(self) -> dict:
        d = {}
        if self.checksum and self.algorithm:
            d['checksum'] = self.checksum
            d['algorithm'] = self.algorithm
        elif self.checksum or self.algorithm:
            raise Exception("must provide both checksum and algorithm, or neither")
        if self.lineage:
            d['lineage'] = self.prep_lineage()

        d['fingerprint'] = self.prep_fingerprint(d)
        return d


class Incidental(_Meta):
    def __init__(
            self, identifier: str,
            path: Union = None, directory: Path = None, **kwargs
    ):
        self.identifier = identifier
        self.path = path
        self.directory = directory
        self.other = kwargs

    def to_dict(self) -> dict:
        d = {
            k: v for k, v in
            sorted(self.other.items(), key=lambda item: item[1], reverse=True)
        }
        d['fingerprint'] = self.prep_fingerprint(d)
        return d


class Metadata(_Meta):
    def __init__(
            self,
            codified: Codified = None,
            derived: Derived = None,
            incidental: Incidental = None,
            lineage: List['Metadata'] = None
    ):
        self.codified = codified
        self.derived = derived
        self.incidental = incidental
        self.lineage = lineage

    def to_dict(self) -> dict:
        d = {}
        f = []
        if self.codified:
            d['codified'] = self.codified.to_dict()
            f.append(d['codified']['fingerprint'])
        if self.derived:
            d['derived'] = self.derived.to_dict()
            f.append(d['derived']['fingerprint'])
        if self.incidental:
            d['incidental'] = self.incidental.to_dict()
            f.append(d['incidental']['fingerprint'])

        if self.lineage:
            d['lineage'] = sorted(
                [y.to_dict() for y in self.lineage],
                key=lambda x: x['fingerprint']
            )
            f.append([x['fingerprint'] for x in d['lineage']])

        d['fingerprint'] = self.prep_fingerprint(f)
        return d
