from typing import List, Union, Tuple
from pathlib import Path
from hashlib import sha256

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
        self.name: str = name
        self.path: Path = path
        self.checksum: sha256 = checksum
        self.lineage: Union[Lineage, List[Lineage]] = lineage
        self.kind: str = kind
        self.other: dict = kwargs

    def _get_network(self, child: str = None) -> Tuple[List[Tuple[str, dict]], List[Tuple[str, str]]]:
        """
        Recurse through lineage to provide a list of names of artifacts in this
        lineage.
        """
        nodes = [(self.name, self._node_data())]
        edges = []
        if child:
            edges.append((self.name, child))

        if isinstance(self.lineage, Lineage):
            subnet = self.lineage._get_network(self.name)
            nodes += subnet[0]
            edges += subnet[1]
        elif isinstance(self.lineage, list):
            for x in self.lineage:
                subnet = x._get_network(self.name)
                nodes += subnet[0]
                edges += subnet[1]
        return nodes, edges

    def _node_data(self) -> dict:
        return {}


if __name__ == '__main__':
    z = Lineage('tom', 'y', 'abc', 'this', [
        Lineage('jerry', 'a', '123', 'that', Lineage('l', 'c', '678', 'though',
                                                     Lineage('sue', 'x', 'x', 'x', None))),
        Lineage('mary', 'v', '345', 'they', Lineage('y', 'c', '678', 'though', Lineage(
            'sue', 'a', 'a', 'a', None
        )
                                                    ))
    ])

    import matplotlib as mpl
    import matplotlib.pyplot as plt
    import networkx as nx

    # from networkx.drawing.nx_agraph import graphviz_layout as layout

    nodes, edges = z._get_network()
    G = nx.OrderedDiGraph()
    G.add_nodes_from(nodes)
    G.add_edges_from(edges)
    nx.draw(G, with_labels=True)
    plt.show()
