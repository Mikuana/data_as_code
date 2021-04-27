import copy
from pathlib import Path
from typing import List

__all__ = ['codified']

SCHEMA_META = "https://json-schema.org/draft/2020-12/schema"

FINGERPRINT = {
    "description": "derived deterministic identifier of the metadata",
    "type": "string",
    "pattern": "^[a-f0-9]{8}$",
    "examples": [
        "a6e33a13",
        "8719003a"
    ]
}

CODIFIED = {
    "title": "Data as Code: Codified Metadata",
    "description": "Metadata which is defined by the step definition of a recipe",
    "type": "object",
    "properties": {
        "fingerprint": {
            "$ref": "#/definitions/fingerprint"
        },
        "description": {
            "description": "docstring description of step that produced data",
            "type": "string"
        },
        "path": {
            "description": "a relative path to a file which contains the referenced data",
            "type": "string",
            "examples": [
                "data/my_file.csv",
                "data/that_file.parquet"
            ]
        },
        "lineage": {
            "description": "list of fingerprints for codified nodes of lineage",
            "type": "array",
            "items": {
                "$ref": "#/definitions/fingerprint"
            },
            "minItems": 1,
            "uniqueItems": True
        }
    },
    "required": [
        "fingerprint"
    ],
    "additionalProperties": False
}

DERIVED = {
    "title": "Data as Code: Derived Metadata",
    "description": "metadata derived from artifacts during recipe execution",
    "type": "object",
    "properties": {
        "fingerprint": {
            "$ref": "#/definitions/fingerprint"
        },
        "checksum": {
            "description": "md5 checksum of the file",
            "type": "string",
            "pattern": "^[a-f0-9]{32}$"
        },
        "lineage": {
            "description": "list of fingerprints for derived nodes of lineage",
            "type": "array",
            "items": {
                "$ref": "#/definitions/fingerprint"
            },
            "minItems": 1,
            "uniqueItems": True
        }
    },
    "required": [
        "fingerprint"
    ],
    "additionalProperties": False
}

LINEAGE = {
    "description": "lineage description",
    "type": "array",
    "items": {
        "$ref": "#"
    },
    "minItems": 1,
    "uniqueItems": True
}

BASE = {
    # **FRAME,
    "definitions": {
        "fingerprint": FINGERPRINT
    },
    "properties": {
        "fingerprint": {
            "$ref": "#/definitions/fingerprint"
        },
        "codified": CODIFIED,
        "derived": DERIVED,
        "lineage": LINEAGE
    },
    "required": [
        "fingerprint",
        "codified",
        "derived"
    ],
    "additionalProperties": False
}


def require_lineage(schema: dict, expected_lineage: List[str]):
    schema['required'] += ['lineage']
    schema['properties']['lineage']['items'] = {
        "description": "expected fingerprint array",
        "type": "string",
        "enum": expected_lineage,
    }
    schema['properties']['lineage']['minItems'] = len(expected_lineage)
    schema['properties']['lineage']['maxItems'] = len(expected_lineage)
    return schema


# noinspection PyTypeChecker
def codified(expected_lineage: List[str] = None) -> dict:
    d = {
        '$schema': SCHEMA_META,
        '$id': f"data_as_code/{Path(__file__).stem}/codified",
        **copy.deepcopy(CODIFIED),
        'definitions': dict(fingerprint=FINGERPRINT.copy()),
    }
    if expected_lineage:
        require_lineage(d, expected_lineage)
    return d


def derived(expected_lineage: List[str] = None) -> dict:
    d = {
        '$schema': SCHEMA_META,
        '$id': f"data_as_code/{Path(__file__).stem}/derived",
        **copy.deepcopy(DERIVED),
        'definitions': dict(fingerprint=FINGERPRINT.copy()),
    }
    if expected_lineage:
        require_lineage(d, expected_lineage)
    return d


if __name__ == '__main__':
    import json

    print(json.dumps(derived(['abcd1234', 'fghy1234']), indent=2))
    print(json.dumps(derived(), indent=2))
