"""
Class container for all call graph operations
"""

from pprint import pformat
from . import llvm_wrapper


class CallGraph:

    def __init__(self, bitcodefile):
        self.graph = llvm_wrapper.extract_callgraph(bitcodefile)
        self.topology = llvm_wrapper.list_all_funcs_topological(bitcodefile)

    def __contains__(self, item):
        return item in self.graph

    def __str__(self):
        return pformat(self.graph)

    def get_candidates_for_symbolic_encapsulation(self):
        """
        Returns a sort of inverted topologically ordered list of all function
        names, that can be symbolically encapsulated by MACKE
        """
        flattened = []
        for t in self.topology:
            if isinstance(t, str):
                flattened.append(t)
            else:
                flattened.extend(t)

        return [t for t in flattened if not self.graph[t]['hasdoubleptrarg']]
