import json
import sys
from dataclasses import dataclass
from inspect import getmembers
from pathlib import Path
from typing import Dict, Type

from jsonschema.exceptions import ValidationError


@dataclass
class Case:
    label: str
    error: Type[Exception] = None

    def __post_init__(self):
        p = Path(Path(__file__).parent, 'full.json')
        self.meta = json.loads(p.read_text())


full = Case("Full featured, valid metadata")

c1 = Case("Mismatched codified fingerprint", ValidationError)
c1.meta['codified']['lineage'][0] = '00000000'

c2 = Case("Mismatched derived fingerprint", ValidationError)
c2.meta['derived']['lineage'][0] = '00000000'

cases: Dict[str, Case] = {
    k: v for k, v
    in getmembers(sys.modules[__name__], lambda x: isinstance(x, Case))
}
valid = [v for v in cases.values() if v.error is None]
invalid = [v for v in cases.values() if v.error]
