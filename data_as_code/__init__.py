from typing import List, Union, Tuple
from uuid import uuid4

import networkx as nx

from data_as_code._plotly import show_lineage
from data_as_code.metadata import Recipe, Input, Intermediary
from data_as_code.step import SourceLocal, Step, SourceHTTP

__version__ = '0.0.0'


class Recipe:
    """
    An environment where the processing of data artifacts from source, to final
    product occurs.
    """


class Step:
    """
    A process which takes one or more artifacts in a recipe, and transforms it
    into another artifact.
    """


class Artifact:
    """
    A file which is used and/or produced by a recipe.
    """


class Product:
    """
    A package which is the result of executing a recipe. Includes data (in
    the form of a file), metadata (including lineage), and the recipe itself.
    """


class Lineage:
    """
    The metadata corresponding to an Artifact which describes the series of
    Artifacts which describe the complete transformation of source data into a
    final product.
    """

    def __init__(self, name, path, checksum, kind, lineage, **kwargs):
        self.name = name
        self.path = path
        self.checksum, self.checksum_type = checksum[0], checksum[1]
        self.lineage: Union[Lineage, List[Lineage]] = lineage
        self.kind = kind
        self.other: dict = kwargs
        self.guid = uuid4().hex

    def _get_network(self, child: str = None) -> Tuple[List[Tuple[str, dict]], List[Tuple[str, str]]]:
        """
        Recurse through lineage to provide a list of names of artifacts in this
        lineage.
        """
        nodes = [(self.guid, self._node_attributes())]
        edges = []
        if child:
            edges.append((self.guid, child))

        if isinstance(self.lineage, Lineage):
            subnet = self.lineage._get_network(self.guid)
            nodes += subnet[0]
            edges += subnet[1]
        elif isinstance(self.lineage, list):
            for x in self.lineage:
                subnet = x._get_network(self.guid)
                nodes += subnet[0]
                edges += subnet[1]
        return nodes, edges

    def _node_attributes(self) -> dict:
        return dict(
            name=self.name,
            checksum=self.checksum[:8],
            path=self.path,
            kind=self.kind
        )

    def _to_dict(self) -> dict:
        return dict(
            name=self.name
        )

    def _draw_lineage(self) -> nx.DiGraph:
        nodes, edges = self._get_network()
        graph = nx.OrderedDiGraph()
        graph.add_nodes_from(nodes)
        graph.add_edges_from(edges)
        return graph

    def show_lineage(self):
        show_lineage(self._draw_lineage())


if __name__ == '__main__':
    bob = Lineage('bob', 'a', ('b', 'sha123'), 'c', None)
    z = Lineage('tom', 'y', ('b', 'sha123'), 'this', [
        Lineage('jerry', 'a', ('b', 'sha123'), 'that', Lineage('l', 'c', ('b', 'sha123'), 'though',
                                                               Lineage('sue', 'x', ('b', 'sha123'), 'x', bob))),
        Lineage('mary', 'v', ('b', 'sha123'), 'they', Lineage('y', 'c', ('b', 'sha123'), 'though', Lineage(
            'sue', 'a', ('b', 'sha123'), 'a', bob
        )
                                                              ))
    ])
    z.show_lineage()
