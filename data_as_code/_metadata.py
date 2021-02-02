import json
from hashlib import sha256, md5
from pathlib import Path
from typing import Dict, List, Tuple

import networkx as nx

from data_as_code._plotly import show_lineage


class Metadata:
    """
    The metadata corresponding to an Artifact which describes the series of
    Artifacts which describe the complete transformation of source cases into a
    final product.

    :param name: ...
    :param path: ...
    :param checksum_value: ...
    :param checksum_algorithm: ...
    :param kind: ...
    :param lineage: ...
    :param other: ...
    """

    def __init__(self, name: str, path: Path, checksum_value: str,
                 checksum_algorithm: str, kind: str, lineage: list,
                 other: Dict[str, str] = None, relative_to: Path = None):
        self.name = name
        self.path = path
        self._relative_to = relative_to
        self.checksum_value = checksum_value
        self.checksum_algorithm = checksum_algorithm
        self.kind = kind
        self.lineage = lineage
        self.other = other
        self.fingerprint = self.calculate_fingerprint()

    def calculate_fingerprint(self) -> str:
        d = dict(
            name=self.name, path=self.path.as_posix(),
            checksum=dict(value=self.checksum_value, algorithm=self.checksum_algorithm),
            kind=self.kind,
            lineage=sorted([x.fingerprint for x in self.lineage]),
            other=self.other
        )
        return md5(json.dumps(d).encode('utf8')).hexdigest()

    def get_network(self, child: str = None) -> Tuple[List[Tuple[str, dict]], List[Tuple[str, str]]]:
        """
        Recurse through lineage to provide a list of names of artifacts in this
        lineage.
        """
        nodes = [(self.fingerprint, self.node_attributes())]
        edges = []
        if child:
            edges.append((self.fingerprint, child))

        for x in self.lineage:
            subnet = x.get_network(self.fingerprint)
            nodes += subnet[0]
            edges += subnet[1]
        return nodes, edges

    def node_attributes(self) -> dict:
        return dict(
            name=self.name,
            checksum=self.checksum_value[:5],
            path=self.path,
            kind=self.kind
        )

    def to_dict(self) -> dict:
        base = dict(
            name=self.name,
            path=self._path_prep().as_posix(),
            checksum=dict(algorithm=self.checksum_algorithm, value=self.checksum_value),
            kind=self.kind
        )

        if self.lineage:
            base['lineage'] = [x.to_dict() for x in self.lineage]

        if self.other:
            base = {**base, **self.other}
        return base

    def _path_prep(self) -> Path:
        rt = self._relative_to
        return self.path.relative_to(rt) if rt else self.path

    def draw_lineage_graph(self) -> nx.DiGraph:
        nodes, edges = self.get_network()
        graph = nx.OrderedDiGraph()
        graph.add_nodes_from(nodes)
        graph.add_edges_from(edges)
        return graph

    def show_lineage(self):
        show_lineage(self.draw_lineage_graph())

    def is_descendent(self, *args: str) -> bool:
        if self.name == args[0]:
            if not args[1:]:
                return True
            elif len(args) == 2 and args[1] is None and self.lineage == []:
                return True
            else:
                for o in self.lineage:
                    if issubclass(type(o), Metadata):
                        if o.is_descendent(*args[1:]):
                            return True
        return False


def from_objects(n: str, p: Path, cs: sha256, k: str, lin: List[dict] = None):
    return Metadata(n, p, cs.hexdigest(), cs.name, k, lin or [])


def from_dictionary(name: str, path: str, checksum: Dict[str, str], kind: str, lineage: List[dict] = None):
    return Metadata(
        name, Path(path),
        checksum['value'], checksum['algorithm'], kind,
        [from_dictionary(**x) for x in lineage or []]
    )


class Reference(Metadata):
    """
    Mock Source

    A lineage Artifact which precedes a Source, but which is not actually
    available for use by the Recipe. Allows for a more complete lineage to be
    declared, when appropriate.
    """

    def __init__(self, name: str, lineage: list, other: Dict[str, str] = None):
        super().__init__(name, None, None, None, 'reference', lineage, other)

    def calculate_fingerprint(self) -> str:
        d = dict(
            name=self.name, kind=self.kind,
            lineage=sorted([x.fingerprint for x in self.lineage]),
            other=self.other
        )
        return md5(json.dumps(d).encode('utf8')).hexdigest()


class Input(Metadata):
    # noinspection PyMissingConstructor
    def __init__(self, *args: str):
        self.lineage = args


class Product(Metadata):
    """
    A package which is the result of executing a recipe. Includes cases (in
    the form of a file), metadata (including lineage), and the recipe itself.
    """

    def __init__(self, name: str, path: Path, checksum_value: str,
                 checksum_algorithm: str, lineage: list,
                 other: Dict[str, str] = None):
        kind = 'product'
        super().__init__(
            name, path, checksum_value, checksum_algorithm, kind, lineage, other
        )

    @classmethod
    def repackage(cls, metadata: Metadata, destination: Path):
        p = metadata.path.rename(Path(destination, metadata.path.name))
        p = p.relative_to(destination)
        return cls(
            metadata.name, p, metadata.checksum_value, metadata.checksum_algorithm,
            metadata.lineage, metadata.other
        )
