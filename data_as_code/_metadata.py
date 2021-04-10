import json
from hashlib import md5
from pathlib import Path
from typing import List, Union

from data_as_code.exceptions import InvalidMetadata


class _Meta:
    def __init__(self, fingerprint: str = None, lineage: List['_Meta'] = None):
        self.lineage = lineage
        self.fingerprint = fingerprint or self.calculate_fingerprint()

    def calculate_fingerprint(self) -> str:
        return md5(json.dumps(self._meta_dict()).encode('utf8')).hexdigest()[:8]

    def _meta_dict(self) -> dict:
        raise Exception  # method stub for subclasses

    def to_dict(self) -> dict:
        d = self._meta_dict()
        d['fingerprint'] = self.fingerprint
        return d

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

    def _meta_dict(self) -> dict:
        d = {}
        if self.path:
            d['path'] = self.path.as_posix()
        if self.description:
            d['description'] = self.description
        if self.instruction:
            d['instruction'] = self.instruction
        if self.lineage:
            d['lineage'] = self.prep_lineage()
        return d


class Derived(_Meta):
    def __init__(
            self,
            checksum: str = None,
            lineage: Union[List['Metadata'], List['Derived']] = None,
            **kwargs
    ):
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

    def _meta_dict(self) -> dict:
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
        return d

    @classmethod
    def from_dict(cls, metadata: dict) -> 'Metadata':
        if metadata.get('fingerprint') is None:
            raise InvalidMetadata(
                'metadata must have a fingerprint'
            )

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


if __name__ == '__main__':
    c1 = Codified(Path(), description='xyz')
    c2 = Codified(Path(), description='abc')
    c3 = Codified(Path(), description='zzz', lineage=[c1, c2])
    # print(c3.to_dict())

    d1 = Derived('abc1')
    d2 = Derived('abc2')
    d3 = Derived('abc3', lineage=[d1, d2])
    # print(d3.to_dict())

    m1 = Metadata(c1, d1)
    m3 = Metadata(c3, d3)
    m2 = Metadata(c2, d2, lineage=[m1, m3])

    mf = Metadata.from_dict(m2.to_dict()).to_dict()
    p = Path('/home/chris/.config/JetBrains/PyCharm2020.3/scratches/scratch_1.json')
    p.write_text(json.dumps(mf, indent=2))
