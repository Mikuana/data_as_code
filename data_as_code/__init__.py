import json
from typing import List, Union, Tuple
from uuid import uuid4

import matplotlib.pyplot as plt
import networkx as nx

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

    def draw_lineage(self):
        nodes, edges = self._get_network()
        graph = nx.OrderedDiGraph()
        graph.add_nodes_from(nodes)
        graph.add_edges_from(edges)
        return graph
        # return nx.draw(graph, labels=nx.get_node_attributes(graph, 'name'))


#
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
    from bokeh.io import output_file, show
    from bokeh.models import (BoxSelectTool, Circle, EdgesAndLinkedNodes, HoverTool,
                              MultiLine, NodesAndLinkedEdges, Plot, Range1d, TapTool,
                              BoxZoomTool, ResetTool, Line)
    from bokeh.palettes import Spectral4
    from bokeh.plotting import from_networkx

    # Prepare Data
    # G = nx.karate_club_graph()
    G = z.draw_lineage()

    # Show with Bokeh
    plot = Plot(plot_width=400, plot_height=400,
                x_range=Range1d(-1.1, 1.1), y_range=Range1d(-1.1, 1.1))
    plot.title.text = "Graph Interaction Demonstration"

    node_hover_tool = HoverTool(tooltips=[
        ("name", "@name"), ("checksum", "@checksum"), ("path", "@path"), ("kind", "@kind")
    ])
    plot.add_tools(node_hover_tool, BoxZoomTool(), ResetTool())

    graph_renderer = from_networkx(G, nx.spring_layout, scale=1, center=(0, 0))
    graph_renderer.node_renderer.glyph = Circle(size=15, fill_color=Spectral4[0])
    graph_renderer.edge_renderer.glyph =
    plot.renderers.append(graph_renderer)

    output_file("interactive_graphs.html")
    show(plot)
