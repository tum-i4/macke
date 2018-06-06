"""
Functions for error chain reconstruction
"""


class ErrorChain:
    def __init__(self, error):
        self.trace = error.stacktrace
        self.found_errors = [error]
        self.head_errors = [error]

    def get_support(self):
        return len(self.found_errors)

    def get_depth(self):
        return self.trace.get_depth()

    def get_num_user_funcs(self, user_funcs):
        return len(set(fun for fun, loc in self.trace.stack if fun in user_funcs))

    def filtered_trace(self, user_funcs):
        return list(filter(lambda f : f[0] in user_funcs, self.trace.stack))

    def get_head_errors(self):
        return self.head_errors

    def error_matches(self, error):
        return error.stacktrace.is_contained_in(self.trace) or self.trace.is_contained_in(error.stacktrace)

    def add_error(self, error):
        assert self.error_matches(error)
        edepth = error.stacktrace.get_depth()
        sdepth = self.get_depth()
        self.found_errors.append(error)
        if edepth == sdepth:
            self.head_errors.append(error)
        elif edepth > sdepth:
            self.head_errors.clear()
            self.head_errors = [error]
            self.trace = error.stacktrace
            return True
        return False

def reconstruct_all_error_chains(errorregistry, callgraph):
    """
    Calculate a dict of vulnerable instruction => [error chains]
    """

    result = dict()
    for vulninst, errorlist in errorregistry.forvulninst.items():
        # Get all chains for this vulnerable instruction
        chains = reconstruct_error_chain(errorlist, callgraph)

        # Sort by chain length and then alphabetically
        result[vulninst] = sorted(chains, key=lambda x: (-len(x), "@".join(x)))

    return result


### LEGACY
##def reconstruct_all_error_chains(errorregistry, callgraph):
##    """
##    Calculate a dict of vulnerable instruction => [error chains]
##    """
##
##    result = dict()
##    for vulninst, errorlist in errorregistry.forvulninst.items():
##        # Get all chains for this vulnerable instruction
##        chains = reconstruct_error_chain(errorlist, callgraph)
##
##        # Sort by chain length and then alphabetically
##        result[vulninst] = sorted(chains, key=lambda x: (-len(x), "@".join(x)))
##
##    return result
##
##
##def reconstruct_error_chain(errorlist, callgraph):
##    """
##    Calculate a list of all error chains inside a given errorlist
##    """
##    # Collect a set of affected functions
##    affected = set({error.entryfunction for error in errorlist})
##
##    # Find all heads of the chains
##    chains = [[fun] for fun in affected if not any(
##        call in affected for call in callgraph[fun]['calls'])]
##
##    # If we don't find a head for the error, it must be a circle
##    if not chains:
##        # A bit hacky, because we might circles over multiple functions
##        chains = [[fun] for fun in affected if not any(
##            call in affected and call != fun
##            for call in callgraph[fun]['calls'])]
##
##    # Extent all chains, until all callers are no longer infected
##    for calleelist in callgraph.group_independent_callees():
##        # Create storage for old and new chains
##        oldchains = list(chains)
##        newchains = list()
##
##        # Try to continue each chain
##        for chain in oldchains:
##            extended = False
##            if chain[-1] in calleelist:
##                for nextnode in callgraph[chain[-1]]['calledby']:
##                    if nextnode in affected:
##                        newchains.append(chain[:] + [nextnode])
##                        extended = True
##
##            if not extended:
##                # Leave the current chain untouched
##                newchains.append(chain[:])
##        chains = newchains
##    return chains
