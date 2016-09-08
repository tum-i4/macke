"""
Details about the error chains found by a MACKE run
"""
from .helper import (
    get_error_registry_for_mackedir, get_klee_registry_from_mackedir,
    generic_main)
from ..CallGraph import CallGraph
from ..Error import get_corresponding_kleedir_name
from ..ErrorChain import reconstruct_all_error_chains
from collections import OrderedDict
from statistics import mean, stdev
from os import path


def chains(macke_directory):
    klees = get_klee_registry_from_mackedir(macke_directory)

    registry = get_error_registry_for_mackedir(macke_directory)
    cg = CallGraph(path.join(macke_directory, "bitcode", "program.bc"))

    chains = reconstruct_all_error_chains(registry, cg)
    chainlengths = [len(chain)
                    for _, chains in chains.items() for chain in chains]

    # Calculate old 1-level-up statistic
    onelevelup = 0
    for caller in cg.get_flattened_inverted_topology():
        for callee in cg[caller]['calls']:
            onelevelup += len(
                registry.get_all_vulnerable_instructions_for_function(caller) &
                registry.get_all_vulnerable_instructions_for_function(callee))

    # Count the end phases
    endphaseone, endphasetwo = 0, 0
    for vulninst, chainlist in chains.items():
        for chain in chainlist:
            for candidaterror in registry.forfunction[chain[-1]]:
                if candidaterror.vulnerableInstruction == vulninst:
                    # candidaterror is exactly the error ending this chain
                    kleedir = get_corresponding_kleedir_name(
                        candidaterror.errfile)

                    if klees[kleedir]['phase'] == 1:
                        endphaseone += 1
                    elif candidaterror.errfile.endswith(".macke.err"):
                        endphasetwo += 1

    result = OrderedDict([
        ("count", len(chainlengths)),
        ("length", OrderedDict([
            ("min", min(chainlengths)),
            ("max", max(chainlengths)),
            ("avg", mean(chainlengths)),
            ("std", stdev(chainlengths) if len(chainlengths) > 2 else -1),
        ])),
        ("longerthanone", len([True for c in chainlengths if c > 1])),
        ("1-level-up", onelevelup),
        ("end-found-by-phase-one", endphaseone),
        ("end-found-by-phase-two", endphasetwo),
        ("detail", chains),
    ])
    return result


def main():
    generic_main(
        "Details about the error chains found by a MACKE run",
        "The details about the error chains were stored in %s",
        "chains.json", chains
    )

if __name__ == '__main__':
    main()
