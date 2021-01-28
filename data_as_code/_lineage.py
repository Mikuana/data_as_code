import json
from hashlib import sha256, md5
from pathlib import Path
from typing import Dict, List, Tuple

import networkx as nx

from data_as_code import show_lineage


class Lineage:
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
                 other: Dict[str, str] = None):
        self.name = name
        self.path = path
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
        # TODO: guid is lost on lineage write to JSON, and this causes reloaded
        # lineage to think multiple references to the same file are different.
        # Use checksum to identify nodes instead of guid
        # TODO: this makes it really easy to blow up the network graph with
        # divide by zero errors. Should probably handle this in the recipe to
        # prevent people from making a great big circle.
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
            path=self.path.as_posix(),
            checksum=dict(algorithm=self.checksum_algorithm, value=self.checksum_value),
            kind=self.kind
        )

        if self.lineage:
            base['lineage'] = [x.to_dict() for x in self.lineage]

        if self.other:
            base = {**base, **self.other}
        return base

    def draw_lineage_graph(self) -> nx.DiGraph:
        nodes, edges = self.get_network()
        graph = nx.OrderedDiGraph()
        graph.add_nodes_from(nodes)
        graph.add_edges_from(edges)
        return graph

    def show_lineage(self):
        show_lineage(self.draw_lineage_graph())


def from_objects(n: str, p: Path, cs: sha256, k: str, lin: List[dict] = None):
    return Lineage(n, p, cs.hexdigest(), cs.name, k, lin or [])


def from_dictionary(name: str, path: str, checksum: Dict[str, str], kind: str, lineage: List[dict] = None):
    return Lineage(
        name, Path(path),
        checksum['value'], checksum['algorithm'], kind,
        [from_dictionary(**x) for x in lineage or []]
    )
