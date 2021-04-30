import copy
from typing import List

import jsonschema

__all__ = ['codified', 'derived', 'metadata']

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
    "anyOf": [
        {"required": ["description"]},
        {"required": ["path"]},
        {"required": ["lineage"]},
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
        "fingerprint",
        "checksum"
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

METADATA = {
    "title": "Data as Code: Metadata",
    "description": "Full metadata for a recipe artifact",
    "type": "object",
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


def validate(instance: dict, schema: dict):
    try:
        jsonschema.validate(instance, schema)
    except jsonschema.exceptions.ValidationError as e:
        raise e


def codified(meta: dict, expected_lineage: List[str] = None):
    d = {
        '$schema': SCHEMA_META,
        **copy.deepcopy(CODIFIED),
        'definitions': dict(fingerprint=FINGERPRINT.copy()),
    }
    # TODO: handle explicit signaling that lineage should not be allowed
    if expected_lineage:
        require_lineage(d, expected_lineage)

    validate(meta, d)


def derived(meta: dict, expected_lineage: List[str] = None):
    d = {
        '$schema': SCHEMA_META,
        **copy.deepcopy(DERIVED),
        'definitions': dict(fingerprint=FINGERPRINT.copy()),
    }
    if expected_lineage:
        require_lineage(d, expected_lineage)

    validate(meta, d)


def metadata(meta: dict):
    d = {
        '$schema': SCHEMA_META,
        **METADATA,
    }

    validate(meta, d)

    lineage = meta.get('lineage', [])
    codified(
        meta['codified'], [x['codified']['fingerprint'] for x in lineage]
    )
    derived(
        meta['derived'], [x['derived']['fingerprint'] for x in lineage]
    )
