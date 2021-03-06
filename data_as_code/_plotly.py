import math

import networkx as nx
from plotly import graph_objects as go


# noinspection DuplicatedCode
def add_edge(
        start, end, edge_x, edge_y, length_frac=1.0, arrow_pos=None,
        arrow_length=0.025, arrow_angle=30, dot_size=20
):
    """
    Extend plotly to support arrow edges

    Code initially borrowed from GitHub project https://github.com/redransil/plotly-dirgraph

    :param start: and end are lists defining start and end points.
    :param end: and end are lists defining start and end points.
    :param edge_x: x and y are lists used to construct the graph.
    :param edge_y: x and y are lists used to construct the graph.
    :param length_frac: ...
    :param arrow_pos: is None, 'middle' or 'end' based on where on the edge you
        want the arrow to appear.
    :param arrow_length: is the length of the arrowhead.
    :param arrow_angle: is the angle in degrees that the arrowhead makes with the edge.
    :param dot_size: is the plotly scatter dot size you are using (used to even
        out line spacing when you have a mix of edge lengths).
    """
    # Get start and end cartesian coordinates
    x0, y0 = start
    x1, y1 = end

    # Incorporate the fraction of this segment covered by a dot into total reduction
    length = math.sqrt((x1 - x0) ** 2 + (y1 - y0) ** 2)
    dot_size_conversion = .0565 / 20  # length units per dot size
    converted_dot_diameter = dot_size * dot_size_conversion
    length_frac_reduction = converted_dot_diameter / length
    length_frac = length_frac - length_frac_reduction

    # If the line segment should not cover the entire distance, get actual start and end coords
    skip_x = (x1 - x0) * (1 - length_frac)
    skip_y = (y1 - y0) * (1 - length_frac)
    x0 = x0 + skip_x / 2
    x1 = x1 - skip_x / 2
    y0 = y0 + skip_y / 2
    y1 = y1 - skip_y / 2

    # Append line corresponding to the edge
    edge_x.append(x0)
    edge_x.append(x1)
    edge_x.append(None)  # Prevents a line being drawn from end of this edge to start of next edge
    edge_y.append(y0)
    edge_y.append(y1)
    edge_y.append(None)

    # Draw arrow
    if arrow_pos is not None:

        # Find the point of the arrow; assume is at end unless told middle
        point_x = x1
        point_y = y1
        eta = math.degrees(math.atan((x1 - x0) / (y1 - y0)))

        if arrow_pos == 'middle' or arrow_pos == 'mid':
            point_x = x0 + (x1 - x0) / 2
            point_y = y0 + (y1 - y0) / 2

        # Find the directions the arrows are pointing
        sign_x = (x1 - x0) / abs(x1 - x0)
        sign_y = (y1 - y0) / abs(y1 - y0)

        # Append first arrowhead
        dx = arrow_length * math.sin(math.radians(eta + arrow_angle))
        dy = arrow_length * math.cos(math.radians(eta + arrow_angle))
        edge_x.append(point_x)
        edge_x.append(point_x - sign_x ** 2 * sign_y * dx)
        edge_x.append(None)
        edge_y.append(point_y)
        edge_y.append(point_y - sign_x ** 2 * sign_y * dy)
        edge_y.append(None)

        # And second arrowhead
        dx = arrow_length * math.sin(math.radians(eta - arrow_angle))
        dy = arrow_length * math.cos(math.radians(eta - arrow_angle))
        edge_x.append(point_x)
        edge_x.append(point_x - sign_x ** 2 * sign_y * dx)
        edge_x.append(None)
        edge_y.append(point_y)
        edge_y.append(point_y - sign_x ** 2 * sign_y * dy)
        edge_y.append(None)

    return edge_x, edge_y


def show_lineage(graph: nx.Graph):
    # Graph formatting controls
    node_color = 'grey'
    node_size = 20
    line_width = 2
    line_color = 'grey'

    label_text = [v for k, v in nx.get_node_attributes(graph, 'name').items()]
    # TODO: pretty up the tooltip. A lot.
    hover_text = [
        '<br>'.join([f"{a.title()}: {b}" for a, b in v.items()]) for k, v in graph.nodes.items()
    ]

    pos = nx.layout.spring_layout(graph)
    for node in graph.nodes:
        graph.nodes[node]['pos'] = list(pos[node])

    # Make list of nodes for plotly
    node_x, node_y = [], []
    for node in graph.nodes():
        x, y = graph.nodes[node]['pos']
        node_x.append(x)
        node_y.append(y)

    # Make a list of edges for plotly, including line segments that result in arrowheads
    edge_x, edge_y = [], []
    for edge in graph.edges():
        start = graph.nodes[edge[0]]['pos']
        end = graph.nodes[edge[1]]['pos']
        edge_x, edge_y = add_edge(start, end, edge_x, edge_y, .8, 'end', .04, 30, node_size)

    # TODO: add data for Step that generates each artifact
    # TODO: add cases for Step that generates each artifact
    edge_trace = go.Scatter(
        x=edge_x, y=edge_y, line=dict(width=line_width, color=line_color), hoverinfo='none',
        mode='lines', opacity=0.8
    )

    node_trace = go.Scatter(
        x=node_x, y=node_y, mode='markers+text', hoverinfo='text',
        marker=dict(showscale=False, color=node_color, size=node_size),
        hovertext=hover_text, text=label_text, textfont=dict(size=18, color='black'),
        textposition='top center'
    )

    fig = go.Figure(data=[edge_trace, node_trace],
                    layout=go.Layout(
                        showlegend=False,
                        hovermode='closest',
                        margin=dict(b=20, l=5, r=5, t=40),
                        xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                        yaxis=dict(showgrid=False, zeroline=False, showticklabels=False))
                    )

    # Note: if you don't use fixed ratio axes, the arrows won't be symmetrical
    fig.update_layout(yaxis=dict(scaleanchor="x", scaleratio=1), plot_bgcolor='rgb(255,255,255)')
    fig.show()
