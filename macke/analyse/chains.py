"""
Details about the error chains found by a MACKE run
"""
from collections import OrderedDict
from os import path
from statistics import mean, stdev

from ..CallGraph import CallGraph
from ..ErrorChain import reconstruct_all_error_chains
from .helper import generic_main, get_error_registry_for_mackedir


def chains(macke_directory):
    """
    Extract the information about the error chains as an OrderedDict
    """

    clg = CallGraph(path.join(macke_directory, "bitcode", "program.bc"))
    registry = get_error_registry_for_mackedir(macke_directory, clg)

    funcs = set(clg.get_flattened_inverted_topology())

    errchains = registry.get_chains()
    chainlengths = [c.get_num_user_funcs(funcs) for c in errchains]

    # Count the end phases and group chains by vulninst
    detail_dict = dict()
    endphaseone, endphasetwo = 0, 0
    for chain in errchains:
        vulninst = chain.get_vulnerable_instruction()
        if vulninst not in detail_dict:
            detail_dict[vulninst] = []
        detail_dict[vulninst].append(list(map(lambda x : x[0], chain.filtered_trace(funcs)[::-1])))
        if any(err.errfile.endswith(".macke.err") for err in chain.get_head_errors()):
            endphasetwo += 1
        else:
            endphaseone += 1

    for chains in detail_dict.values():
        chains.sort(key = lambda x: (-len(x), "@".join(x)))


    result = OrderedDict([
        ("count", len(chainlengths)),
        ("length", OrderedDict([
            ("min", min(chainlengths) if chainlengths else -1),
            ("max", max(chainlengths) if chainlengths else -1),
            ("avg", mean(chainlengths) if chainlengths else -1),
            ("std", stdev(chainlengths) if len(chainlengths) > 2 else -1),
        ])),
        ("longerthanone", len([True for c in chainlengths if c > 1])),
        ("end-found-by-phase-one", endphaseone),
        ("end-found-by-phase-two", endphasetwo),
        ("detail", detail_dict)
    ])
    return result
    ## LEGACY
    #errchains = reconstruct_all_error_chains(registry, clg)
    #chainlengths = [len(chain)
    #                for _, chainlist in errchains.items()
    #                for chain in chainlist]

    ## Calculate old 1-level-up statistic
    #onelevelup = 0
    #for caller in clg.get_flattened_inverted_topology():
    #    for callee in clg[caller]['calls']:
    #        onelevelup += len(
    #            registry.get_all_vulninst_for_func(caller) &
    #            registry.get_all_vulninst_for_func(callee))

    ## Count the end phases
    #endphaseone, endphasetwo = 0, 0
    #for vulninst, chainlist in errchains.items():
    #    for chain in chainlist:
    #        # candidaterror are all errors, that end this chain
    #        # normally, this is just one error, but circles can have several
    #        if any(candidaterror.vulnerable_instruction == vulninst and
    #               candidaterror.errfile.endswith(".macke.err")
    #               for candidaterror in registry.forfunction[chain[-1]]):
    #            endphasetwo += 1
    #        else:
    #            endphaseone += 1
    # ("1-level-up", onelevelup),


def main():
    """ Entry point to run this analysis stand alone """
    generic_main(
        "Details about the error chains found by a MACKE run",
        "The details about the error chains were stored in %s",
        "chains.json", chains
    )

if __name__ == '__main__':
    main()
