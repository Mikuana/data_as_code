from typing import List, Union, Tuple, Dict
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
        self.guid = uuid4().hex

        self.name = name
        self.path = path
        self.kind = kind
        self.checksum: Dict[str, str] = checksum
        self.other: Dict[str, str] = kwargs

        self.lineage: Union[Lineage, List[Lineage]] = lineage

    def _get_network(self, child: str = None) -> Tuple[List[Tuple[str, dict]], List[Tuple[str, str]]]:
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
        nodes = [(self.checksum['value'], self._node_attributes())]
        edges = []
        if child:
            edges.append((self.checksum['value'], child))

        if isinstance(self.lineage, Lineage):
            subnet = self.lineage._get_network(self.checksum['value'])
            nodes += subnet[0]
            edges += subnet[1]
        elif isinstance(self.lineage, list):
            for x in self.lineage:
                subnet = x._get_network(self.checksum['value'])
                nodes += subnet[0]
                edges += subnet[1]
        return nodes, edges

    def _node_attributes(self) -> dict:
        return dict(
            name=self.name,
            checksum=self.checksum['value'][:8],
            path=self.path,
            kind=self.kind
        )

    def _to_dict(self) -> dict:
        base = dict(
            name=self.name,
            path=self.path,
            checksum=self.checksum,
            kind=self.kind,
        )

        if isinstance(self.lineage, Lineage):
            base['lineage'] = self.lineage._to_dict()
        elif isinstance(self.lineage, list):
            base['lineage'] = [x._to_dict() for x in self.lineage]

        return {**base, **self.other}

    @classmethod
    def _from_dict(cls, lineage: dict):
        if lineage.get('lineage'):
            nested = [cls._from_dict(x) for x in lineage.get('lineage')]
        else:
            nested = None

        return cls(
            name=lineage['name'],
            path=lineage['path'],
            checksum=lineage['checksum'],
            kind=lineage['kind'],
            lineage=nested
        )

    def _draw_lineage(self) -> nx.DiGraph:
        nodes, edges = self._get_network()
        graph = nx.OrderedDiGraph()
        graph.add_nodes_from(nodes)
        graph.add_edges_from(edges)
        return graph

    def show_lineage(self):
        show_lineage(self._draw_lineage())
