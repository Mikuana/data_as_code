import copy
import json
import sys
from dataclasses import dataclass
from inspect import getmembers
from pathlib import Path
from typing import Dict, Type

from jsonschema.exceptions import ValidationError

from data_as_code._metadata import Codified, Derived, Metadata

_full_json = Path(Path(__file__).parent, 'full.json').read_text()
_full = json.loads(_full_json)


@dataclass
class Case:
    label: str
    error: Type[Exception] = None

    def __post_init__(self):
        self.meta = copy.deepcopy(_full)


full = Case("Full featured, valid metadata")

v1 = Case("No lineage")
v1.meta.pop('lineage')
v1.meta['codified'].pop('lineage')
v1.meta['derived'].pop('lineage')
v1.meta['fingerprint'] = 'eb34488f'  # lineage alteration changes fingerprint

c1 = Case("Mismatched codified fingerprint", ValidationError)
c1.meta['codified']['lineage'][0] = '00000000'

c6 = Case("Extra codified fingerprint", ValidationError)
c6.meta['codified']['lineage'].append('00000000')

c2 = Case("Mismatched derived fingerprint", ValidationError)
c2.meta['derived']['lineage'][0] = '00000000'

c5 = Case("Extra derived fingerprint", ValidationError)
c5.meta['derived']['lineage'].append('00000000')

c3 = Case("Missing checksum", ValidationError)
c3.meta['derived'].pop('checksum')

c7 = Case("Missing codified", ValidationError)
c7.meta.pop('codified')

c8 = Case("Missing derived", ValidationError)
c8.meta.pop('derived')

c4 = Case("Missing root lineage", ValidationError)
c4.meta.pop('lineage')

cases: Dict[str, Case] = {
    k: v for k, v
    in getmembers(sys.modules[__name__], lambda x: isinstance(x, Case))
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

meta_cases = [m1, m2]
