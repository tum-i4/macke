"""
Class container for all call graph operations
"""

from pprint import pformat
from os import path
from . import llvm_wrapper


class CallGraph:
    """
    All information about the callgraph from a specific bitcode file
    """

    def __init__(self, bitcodefile):
        assert path.isfile(bitcodefile)
        self.graph = llvm_wrapper.extract_callgraph(bitcodefile)
        self.topology = llvm_wrapper.list_all_funcs_topological(bitcodefile)

    def __contains__(self, item):
        return item in self.graph

    def __str__(self):
        return pformat(self.graph)

    def __getitem__(self, key):
        return self.graph[key]

    def list_symbolic_encapsulable(self, removemain=True):
        """
        Returns a sort of inverted topologically ordered list of all function
        names, that can be symbolically encapsulated by MACKE
        """

        # Nested lists of circles and SCCs are simply flattened
        flattened = []
        for topo in self.topology:
            if isinstance(topo, str):
                flattened.append(topo)
            else:
                flattened.extend(topo)

        return [t for t in flattened if (not self[t]['hasdoubleptrarg'] or (
            not removemain and t == "main"))]

    def group_independent_calls(self, removemain=True):
        """
        Returns a topologically ordered list of (caller, callee)-tuples
        nested in sublists, that can be analyzed in parallel processes
        """

        # Probably the result of this method is not the optimal solution
        # considering the number parallel executable pairs. But I don't
        # know a better algorithm to generate them. Maybe later ...

        units = self.group_independent_functions()

        # Convert the unit list of functions to a list of callers
        result = []
        for unit in units:
            pairs = []
            for callee in unit:
                for caller in self[callee]['calledby']:
                    if ((not removemain and caller == "main") or
                            (not self[caller]['hasdoubleptrarg'] and
                             not self[caller]['isexternal'] and
                             not self[callee]['isexternal'])):
                        pairs.append((caller, callee))
            if pairs:
                result.append(sorted(pairs))

        # (partially) assert correctness of the result
        for res in result:
            assert res
            callers, callees = set(), set()
            for (caller, callee) in res:
                callers.add(caller)
                callees.add(callee)
            assert callers.isdisjoint(callees)

        return result

    def group_independent_functions(self):
        """
        Group the topological ordered function list in independent units
        """
        units = []
        independent = set()
        earlier_calls = set()

        for topo in self.topology:
            if isinstance(topo, str):
                if topo in earlier_calls:
                    # Add all function, that are called earlier
                    if independent:
                        units.append(sorted(list(independent)))
                    # And restart the search
                    independent = set()
                    earlier_calls = set()

                # Mark this function as indepent
                independent.add(topo)
                # Mark all function called by now
                earlier_calls |= set(self[topo]['calledby'])

            else:
                # Add all previous independent functions
                if independent:
                    units.append(sorted(list(independent)))
                    independent = set()

                # Split each part of a scc in a separate run
                for arc in sorted(topo):
                    units.append([arc])

        # Add all remaining elements
        if independent:
            units.append(list(independent))

        return units
