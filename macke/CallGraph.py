"""
Class container for all call graph operations
"""

from queue import Queue
from pprint import pformat


class CallGraph:

    def __init__(self, jsonrepr):
        self.graph = jsonrepr

    def __contains__(self, item):
        return item in self.graph

    def __str__(self):
        return pformat(self.graph)

    def get_candidates_for_symbolic_encapsulation(self):
        """
        Returns a sort of inverted topologically ordered list of all function
        names, that can be symbolically encapsulated by MACKE
        """
        suitable = {
            k for k, v in self.graph.items()
            if (
                k != "null function" and not k.startswith("llvm.") and
                v['calls'] != ['external node'] and not v['hasdoubleptrarg'])
        }

        ##########
        # Try to topoligally sort as much as possible
        ##########

        # Initialize the search
        worklist = Queue()
        done = set({'external node'})  # Trick: external nodes are already done
        toposort = []

        # Only start the search, if a main function exists
        if "main" in self.graph:
            worklist.put("main")

        # The BFS loop
        while not worklist.empty():
            func = worklist.get()

            # shift the func to toposort list, if it is suitable
            if func in suitable:
                toposort.append(func)
                suitable.remove(func)

            for call in self.graph[func]['calls']:
                # At all new calls to the search list
                if call not in done:
                    done.add(call)
                    worklist.put(call)

        # Everything not sorted topologically, is sorted alphabetically
        return list(reversed(toposort)) + sorted(suitable)
