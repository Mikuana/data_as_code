from data_as_code._plotly import show_lineage
from data_as_code.metadata import Recipe, Input, Intermediary
from data_as_code.step import SourceLocal, Step, SourceHTTP

__version__ = '0.0.0'


class Recipe:
    """
    An environment where the processing of cases artifacts from source, to final
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
    A package which is the result of executing a recipe. Includes cases (in
    the form of a file), metadata (including lineage), and the recipe itself.
    """
