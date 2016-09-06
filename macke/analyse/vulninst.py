"""
List all vulnerable instructions found by a MACKE run
"""
from .helper import get_error_registry_for_mackedir, generic_main
from ..CallGraph import CallGraph
from collections import OrderedDict
from os import path
import operator


def vulninst(macke_directory):
    registry = get_error_registry_for_mackedir(macke_directory)

    vulninstdict = OrderedDict()
    for vulninst, errors in sorted(
            registry.forvulninst.items(), key=operator.itemgetter(0)):
        vulninstdict[vulninst] = []
        for error in sorted(errors):
            odict = error.as_ordered_dict()
            odict.pop('vulnerableInstruction', None)
            vulninstdict[vulninst].append(odict)

    # Get all library functions
    cg = CallGraph(path.join(macke_directory, "bitcode", "program.bc"))
    libfuncs = cg.get_functions_without_any_caller()
    libfuncs.discard("main")

    # Classify the vulnerable instructions by type
    mainc = len(registry.get_all_vulnerable_instructions_for_function("main"))
    libvulninst = set()
    for libfunc in libfuncs:
        libvulninst |= registry.get_all_vulnerable_instructions_for_function(
            libfunc)
    libc = len(libvulninst)
    innerc = registry.count_vulnerable_instructions() - libc

    result = OrderedDict([
        ("vulninstcount", registry.count_vulnerable_instructions()),
        ("bytype", OrderedDict([
            ("main", mainc),
            ("library", libc),
            ("inner", innerc),
        ])),
        ("vulninst", vulninstdict),
    ])
    return result


def main():
    generic_main(
        "List all vulnerable instructions found by a MACKE run",
        "The vulnerable instructions were stored in %s",
        "vulninst.json", vulninst
    )

if __name__ == '__main__':
    main()
