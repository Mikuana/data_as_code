import copy
import json
import sys
from dataclasses import dataclass
from inspect import getmembers
from pathlib import Path
from typing import Dict, Type

from jsonschema.exceptions import ValidationError

from data_as_code.exceptions import InvalidFingerprint
from data_as_code._metadata import Codified, Derived, Metadata

_full_json = Path(Path(__file__).parent, 'full.json').read_text()
_full = json.loads(_full_json)
_min_json = Path(Path(__file__).parent, 'minimal.json').read_text()
_min = json.loads(_min_json)


@dataclass
class Case:
    label: str
    error: Type[Exception] = None
    meta: dict = None


@dataclass
class Full(Case):
    def __post_init__(self):
        self.meta = copy.deepcopy(_full)


@dataclass
class Min(Case):
    def __post_init__(self):
        self.meta = copy.deepcopy(_min)


full = Full("Full featured, valid metadata")

v1 = Full("No lineage")
v1.meta.pop('lineage')
v1.meta['codified'].pop('lineage')
v1.meta['derived'].pop('lineage')
# lineage alteration changes fingerprint
v1.meta['codified']['fingerprint'] = 'b3fa65c8'
v1.meta['derived']['fingerprint'] = 'eb985999'
v1.meta['fingerprint'] = 'e19eb482'

c1 = Full("Mismatched codified fingerprint", ValidationError)
c1.meta['codified']['lineage'][0] = '00000000'

c6 = Full("Extra codified fingerprint", ValidationError)
c6.meta['codified']['lineage'].append('00000000')

c2 = Full("Mismatched derived fingerprint", ValidationError)
c2.meta['derived']['lineage'][0] = '00000000'

c5 = Full("Extra derived fingerprint", ValidationError)
c5.meta['derived']['lineage'].append('00000000')

c3 = Full("Missing checksum", ValidationError)
c3.meta['derived'].pop('checksum')

c7 = Full("Missing codified", ValidationError)
c7.meta.pop('codified')

c8 = Full("Missing derived", ValidationError)
c8.meta.pop('derived')

c4 = Full("Missing root lineage", ValidationError)
c4.meta.pop('lineage')

c9 = Min("Minimal Example")

cases: Dict[str, Case] = {
    k: v for k, v
    in getmembers(sys.modules[__name__], lambda x: issubclass(type(x), Case))
}
valid = [v for v in cases.values() if v.error is None]
invalid = [v for v in cases.values() if v.error]

m1 = Metadata(
    Codified(path='a.csv'),
    Derived(checksum='a' * 32)
)

m2 = Metadata(
    Codified('x.csv', lineage=['a5eff3ed']),
    Derived(checksum='a' * 32, lineage=['56b31c3b']),
    lineage=[m1]
)

c10 = Min("Incorrect root fingerprint", InvalidFingerprint)
c10.meta['fingerprint'] = 'abcd1234'

c11 = Min("Incorrect codified fingerprint", InvalidFingerprint)
c11.meta['codified']['fingerprint'] = 'abcd1234'

c12 = Min("Incorrect derived fingerprint", InvalidFingerprint)
c12.meta['derived']['fingerprint'] = 'abcd1234'

meta_cases = [m1, m2]
meta_cases2 = [c10, c11, c12]
