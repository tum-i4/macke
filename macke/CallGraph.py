"""
Class container for all call graph operations
"""

from pprint import pformat
from os import path
from . import llvm_wrapper


class CallGraph:

    def __init__(self, bitcodefile):
        assert(path.isfile(bitcodefile))
        self.graph = llvm_wrapper.extract_callgraph(bitcodefile)
        self.topology = llvm_wrapper.list_all_funcs_topological(bitcodefile)

    def __contains__(self, item):
        return item in self.graph

    def __str__(self):
        return pformat(self.graph)

    def __getitem__(self, key):
        return self.graph[key]

    def get_candidates_for_symbolic_encapsulation(self):
        """
        Returns a sort of inverted topologically ordered list of all function
        names, that can be symbolically encapsulated by MACKE
        """

        # Nested lists of circles and SCCs are simply flattened
        flattened = []
        for t in self.topology:
            if isinstance(t, str):
                flattened.append(t)
            else:
                flattened.extend(t)

        return [t for t in flattened if not self[t]['hasdoubleptrarg']]

    def get_grouped_edges_for_call_chain_propagation(self):
        """
        Returns a topologically ordered list of (caller, callee)-tuples
        nested in sublists, that can be analyzed in parallel processes
        """

        # Probably the result of this method is not the optimal solution
        # considering the number parallel executable pairs. But I don't
        # know a better algorithm to generate them. Maybe later ...

        # Regroup the topological ordered function list in independent units
        units = []
        independent = set()
        calledEarlier = set()

        for topo in reversed(self.topology):
            if isinstance(topo, str):
                if topo in calledEarlier:
                    # Add all function, that are called earlier
                    if independent:
                        units.append(sorted(list(independent)))
                    # And restart the search
                    independent = set({topo})
                else:
                    # Mark this function as indepent
                    independent.add(topo)

                # Mark all function called by now
                calledEarlier = set(self[topo]['calls'])
            else:
                # Add all previous independet functions
                if independent:
                    units.append(sorted(list(independent)))
                    independent = set()

                # Split each part of a scc in a separate run
                for t in reversed(sorted(topo)):
                    units.append([t])

        # Add all remaining elements
        if independent:
            units.append(list(independent))
            independent = set()

        # Convert the unit list of functions to a list of callers
        result = []
        for u in reversed(units):
            ps = []
            for caller in u:
                if not self[caller]['hasdoubleptrarg']:
                    for callee in sorted(self[caller]['calls']):
                        if (not self[caller]['isexternal'] and
                                not self[callee]['isexternal']):
                            ps.append((caller, callee))
            if ps:
                result.append(ps)

        # (partially) assert correctness of the result
        for r in result:
            assert(r)
            callers, callees = set(), set()
            for (caller, callee) in r:
                callers.add(caller)
                callees.add(callee)
            assert(callers.isdisjoint(callees))

        return result
