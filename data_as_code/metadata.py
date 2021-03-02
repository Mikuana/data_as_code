import json
from hashlib import md5
from pathlib import Path
from typing import Dict, List, Tuple, Union


class Metadata:
    """
    The metadata corresponding to an Artifact which describes the series of
    Artifacts which describe the complete transformation of source cases into a
    final product.

    :param absolute_path: ...
    :param checksum_value: ...
    :param checksum_algorithm: ...
    :param lineage: ...
    """

    # TODO: path param must be required, or else use of self.path must account for None
    def __init__(self, absolute_path: Union[Path, None], relative_path: Union[Path, None],
                 checksum_value: Union[str, None], checksum_algorithm: Union[str, None],
                 lineage: list, role: str, relative_to: Path = None,
                 other: Dict[str, str] = None, fingerprint: str = None
                 ):
        self.absolute_path = absolute_path
        self.relative_path = relative_path
        self._relative_to = relative_to
        self.checksum_value = checksum_value
        self.checksum_algorithm = checksum_algorithm
        self.lineage = lineage
        self.other = other or {}
        self.role = role
        self.fingerprint = fingerprint or self.calculate_fingerprint()

    def calculate_fingerprint(self) -> str:
        d = dict(
            path=self.absolute_path.as_posix(),  # TODO: handle when None
            checksum=dict(value=self.checksum_value, algorithm=self.checksum_algorithm),
            lineage=sorted([x.fingerprint for x in self.lineage])
        )
        d = {
            **d,
            **{k: v for k, v in sorted(self.other.items(), key=lambda item: item[1])}
        }
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
            checksum=self.checksum_value[:5],
            path=self.absolute_path
        )

    def to_dict(self, relative_root: Path) -> dict:
        base = dict(
            path=self.absolute_path.relative_to(relative_root).as_posix(), role=self.role,
            checksum=dict(algorithm=self.checksum_algorithm, value=self.checksum_value),
            fingerprint=self.fingerprint
        )

        if self.lineage:
            base['lineage'] = [x.to_dict(relative_root) for x in self.lineage]

        base = {**base, **self.other}
        return base

    def show_lineage(self):
        """
        Show plotly network graph of lineage

        Note: Requires plotly and networkx packages to be installed.
        """
        # TODO: add import failure notice and point to Lineage extras
        from data_as_code._plotly import show_lineage
        import networkx as nx

        nodes, edges = self.get_network()
        graph = nx.OrderedDiGraph()
        graph.add_nodes_from(nodes)
        graph.add_edges_from(edges)
        show_lineage(graph)


def from_dictionary(
        path: str, checksum: Dict[str, str], fingerprint: str,
        role: str, lineage: List[dict] = None, **kwargs
):
    return Metadata(
        absolute_path=None, relative_path=Path(path),
        checksum_value=checksum['value'], checksum_algorithm=checksum['algorithm'],
        lineage=[from_dictionary(**x) for x in lineage or []], role=role,
        fingerprint=fingerprint, other=kwargs
    )


class Reference(Metadata):
    """
    Mock Source

    A lineage Artifact which precedes a Source, but which is not actually
    available for use by the Recipe. Allows for a more complete lineage to be
    declared, when appropriate.
    """

    def __init__(self, lineage: list, other: Dict[str, str] = None):
        super().__init__(None, None, None, None, lineage, 'reference', other=other)

    def calculate_fingerprint(self) -> str:
        d = dict(
            lineage=sorted([x.fingerprint for x in self.lineage])
        )
        return md5(json.dumps(d).encode('utf8')).hexdigest()
