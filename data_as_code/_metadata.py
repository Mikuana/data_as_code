import json
from hashlib import md5
from pathlib import Path
from typing import List, Union


class _Meta:
    lineage: List['_Meta'] = None

    def __init__(self, fingerprint: str = None):
        self.fingerprint = fingerprint

    def prep_fingerprint(self, d: Union[dict, list]) -> str:
        return self.fingerprint or md5(json.dumps(d).encode('utf8')).hexdigest()

    def to_dict(self) -> dict:
        return {}

    def prep_lineage(self) -> List[str]:
        return sorted([x.to_dict()['fingerprint'] for x in self.lineage])


class Codified(_Meta):
    def __init__(
            self, path: Union[Path, str] = None,
            description: str = None, instruction: str = None,
            lineage: Union[List['Metadata'], List['Codified']] = None,
            **kwargs
    ):
        self.path = Path(path) if isinstance(path, str) else path
        self.description = description
        self.instruction = instruction
        super().__init__(**kwargs)

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
            checksum: str = None,
            algorithm: str = None,
            lineage: Union[List['Metadata'], List['Derived']] = None,
            **kwargs
    ):
        self.checksum = checksum
        self.algorithm = algorithm
        super().__init__(**kwargs)

        if lineage:
            self.lineage = [x.derived if isinstance(x, Metadata) else x for x in lineage]

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
            self,
            path: Union[Path, str] = None,
            directory: Union[Path, str] = None,
            **kwargs
    ):
        self.path = Path(path) if isinstance(path, str) else path  # absolute path
        self.directory = Path(directory) if isinstance(path, str) else path
        self.other = kwargs
        super().__init__(**kwargs)

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
            lineage: List['Metadata'] = None,
            **kwargs
    ):
        self.codified = codified
        self.derived = derived
        self.incidental = incidental
        self.lineage = lineage
        super().__init__(**kwargs)

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

        if self.lineage:
            d['lineage'] = sorted(
                [y.to_dict() for y in self.lineage],
                key=lambda x: x['fingerprint']
            )
            f.append([x['fingerprint'] for x in d['lineage']])

        d['fingerprint'] = self.prep_fingerprint(f)
        return d

    @classmethod
    def from_dict(cls, metadata: dict) -> 'Metadata':
        dl = [cls.from_dict(x) for x in metadata.get('lineage', [])]

        dc = metadata.get('codified')
        mc = Codified(**cls._replace(dc, lineage=dl)) if dc else None

        dd = metadata.get('derived')
        md = Derived(**cls._replace(dd, lineage=dl)) if dd else None

        di = metadata.get('incidental')
        mi = Incidental(**cls._replace(di, lineage=dl)) if di else None

        return cls(codified=mc, derived=md, incidental=mi, lineage=dl)

    @staticmethod
    def _replace(x: dict, **kwargs) -> dict:
        """Wrapper to merge dictionaries and overwrite where necessary"""
        return {**x, **kwargs}
