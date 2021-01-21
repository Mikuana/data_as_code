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
    A file which corresponds to a node, and is used by a recipe.
    """


class Node:
    """
    The metadata which describes an artifact, which is a distinct point in the
    lineage of a data product, which exists between steps
    """


class Product:
    """
    A package which is the result of executing a recipe. Includes data (in
    the form of a file), metadata (including lineage), and the recipe itself.
    """


class Lineage:
    """
    The series of nodes which describe the complete transformation of
    source data into a final product.
    """
