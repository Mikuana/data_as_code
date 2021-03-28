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
                 lineage: list, relative_to: Path = None,
                 other: Dict[str, str] = None, fingerprint: str = None,
                 step_description: str = None, step_instruction: str = None,
                 ):
        self.path = absolute_path
        self._relative_path = relative_path
        self._relative_to = relative_to
        if self.path is None and self._relative_path and self._relative_to:
            self.path = Path(self._relative_to, self._relative_path)

        self.checksum_value = checksum_value
        self.checksum_algorithm = checksum_algorithm
        self.lineage = lineage
        self.other = other or {}
        self.step_description = step_description
        self._step_instruction = step_instruction
        self.fingerprint = fingerprint or self.calculate_fingerprint()

    def calculate_fingerprint(self) -> str:
        d = dict(
            checksum=dict(value=self.checksum_value, algorithm=self.checksum_algorithm),
            lineage=sorted([x.prep_fingerprint for x in self.lineage]),
            step_description=self.step_description, step_instruction=self._step_instruction
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
            path=self.path
        )

    def to_dict(self) -> dict:
        if self.checksum_value and self.checksum_algorithm:
            cs = dict(algorithm=self.checksum_algorithm, value=self.checksum_value)
        else:
            cs = None

        base = {
            'path': self._relative_path.as_posix() if self._relative_path else None,
            'step_description': self.step_description,
            'checksum': cs,
            'fingerprint': self.fingerprint,
            'lineage': [x.to_dict() for x in self.lineage]
        }

        base = {**{k: v for k, v in base.items() if v}, **self.other}
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
        checksum: Dict[str, str], fingerprint: str,
        lineage: List[dict] = None, path: str = None,
        relative_to: str = None, step_description=None,
        **kwargs
):
    lin = [from_dictionary(**x) for x in lineage or []]
    return Metadata(
        absolute_path=None, relative_path=Path(path) if path else None,
        checksum_value=checksum['value'], checksum_algorithm=checksum['algorithm'],
        lineage=lin, fingerprint=fingerprint, relative_to=relative_to,
        step_description=step_description, other=kwargs
    )


class Reference(Metadata):
    """
    Mock Source

    A lineage Artifact which precedes a Source, but which is not actually
    available for use by the Recipe. Allows for a more complete lineage to be
    declared, when appropriate.
    """

    def __init__(self, lineage: list, other: Dict[str, str] = None):
        super().__init__(None, None, None, None, lineage, other=other)

    def calculate_fingerprint(self) -> str:
        d = dict(
            lineage=sorted([x.prep_fingerprint for x in self.lineage])
        )
        return md5(json.dumps(d).encode('utf8')).hexdigest()


class _Meta:
    @staticmethod
    def prep_fingerprint(d: dict) -> str:
        return md5(json.dumps(d).encode('utf8')).hexdigest()


class Codified(_Meta):
    def __init__(
            self, path: Path = None, lineage: List['Codified'] = None,
            description: str = None, instruction: str = None,
    ):
        self.path = path
        self.lineage = lineage
        self.description = description
        self.instruction = instruction

    def to_dict(self) -> dict:
        d = {}
        if self.path:
            d['path'] = self.path.as_posix()
        if self.description:
            d['description'] = self.description
        if self.instruction:
            d['instruction'] = self.instruction
        if self.lineage:
            d['lineage'] = self.prep_lineage()

        d['fingerprint'] = self.prep_fingerprint(d)
        return d

    def prep_lineage(self) -> Dict[str, dict]:
        ld = [x.to_dict() for x in self.lineage]
        return {
            x['fingerprint']: x
            for x in sorted(ld, key=lambda item: item['fingerprint'])
        }


class Derived(_Meta):
    def __init__(
            self, identifier: str,
            checksum: Union[str, None], algorithm: Union[str, None],
            lineage: List['Derived'] = None,
    ):
        self.identifier = identifier
        self.checksum = checksum
        self.algorithm = algorithm
        self.lineage = lineage

    def to_dict(self) -> dict:
        d = {}
        if self.checksum and self.algorithm:
            d['checksum'] = self.checksum
            d['algorithm'] = self.algorithm
        elif self.checksum or self.algorithm:
            raise Exception("must provide both checksum and algorithm, or neither")
        if self.lineage:
            d['lineage'] = self.prep_lineage()

        d['fingerprint'] = self.prep_fingerprint(d)
        return d

    def prep_lineage(self) -> Dict[str, dict]:
        return {
            x.identifier: x.to_dict()
            for x in sorted(self.lineage, key=lambda item: item.identifier)
        }


class Incidental(_Meta):
    def __init__(
            self, identifier: str,
            path: Union = None, directory: Path = None, **kwargs
    ):
        self.identifier = identifier
        self.path = path
        self.directory = directory
        self.other = kwargs

    def to_dict(self) -> dict:
        d = {
            k: v for k, v in
            sorted(self.other.items(), key=lambda item: item[1], reverse=True)
        }
        d['fingerprint'] = self.prep_fingerprint(d)
        return d


if __name__ == '__main__':
    c1 = Codified(Path(), description='xyz')
    c2 = Codified(Path(), description='abc')
    c3 = Codified(Path(), description='zzz', lineage=[c1, c2])
    print(c3.to_dict())

    d1 = Derived('157a35fa887733e8a9d29577868553a0', 'abc1', 'md5')
    d2 = Derived('1f92255965e052ad2f4fbbbf3b118e17', 'abc2', 'md5')
    d3 = Derived('0830d648d5c6634a47dbdc7517db7b23', 'abc3', 'md5', lineage=[d1, d2])
    print(d3.to_dict())
