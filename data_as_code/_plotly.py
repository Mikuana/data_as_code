"""
Extends plotly to support arrow edges

Code initially borrowed from GitHub project https://github.com/redransil/plotly-dirgraph
"""
import math


def addEdge(start, end, edge_x, edge_y, length_frac=1, arrow_pos=None, arrow_length=0.025, arrow_angle=30, dot_size=20):
    """
    :param start: and end are lists defining start and end points.
    :param end: and end are lists defining start and end points.
    :param edge_x: x and y are lists used to construct the graph.
    :param edge_y: x and y are lists used to construct the graph.
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
    if not arrow_pos == None:

        # Find the point of the arrow; assume is at end unless told middle
        pointx = x1
        pointy = y1
        eta = math.degrees(math.atan((x1 - x0) / (y1 - y0)))

        if arrow_pos == 'middle' or arrow_pos == 'mid':
            pointx = x0 + (x1 - x0) / 2
            pointy = y0 + (y1 - y0) / 2

        # Find the directions the arrows are pointing
        signx = (x1 - x0) / abs(x1 - x0)
        signy = (y1 - y0) / abs(y1 - y0)

        # Append first arrowhead
        dx = arrow_length * math.sin(math.radians(eta + arrow_angle))
        dy = arrow_length * math.cos(math.radians(eta + arrow_angle))
        edge_x.append(pointx)
        edge_x.append(pointx - signx ** 2 * signy * dx)
        edge_x.append(None)
        edge_y.append(pointy)
        edge_y.append(pointy - signx ** 2 * signy * dy)
        edge_y.append(None)

        # And second arrowhead
        dx = arrow_length * math.sin(math.radians(eta - arrow_angle))
        dy = arrow_length * math.cos(math.radians(eta - arrow_angle))
        edge_x.append(pointx)
        edge_x.append(pointx - signx ** 2 * signy * dx)
        edge_x.append(None)
        edge_y.append(pointy)
        edge_y.append(pointy - signx ** 2 * signy * dy)
        edge_y.append(None)

    return edge_x, edge_y
