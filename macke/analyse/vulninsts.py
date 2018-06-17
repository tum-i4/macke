"""
List all vulnerable instructions found by a MACKE run
"""
import operator
from collections import OrderedDict
from os import path

from ..CallGraph import CallGraph
from .helper import generic_main, get_error_registry_for_mackedir


def vulninsts(macke_directory):
    """
    Extract informations about the vulnerable instruction as an OrderedDict
    """
    clg = CallGraph(path.join(macke_directory, "bitcode", "program.bc"))
    registry = get_error_registry_for_mackedir(macke_directory, clg)

    vulninstdict = OrderedDict()
    for vulninst, errors in sorted(
            registry.forvulninst.items(), key=operator.itemgetter(0)):
        vulninstdict[vulninst] = []
        for error in sorted(errors):
            odict = error.as_ordered_dict()
            odict.pop('vulnerableInstruction', None)
            vulninstdict[vulninst].append(odict)

    # Get all library functions
    libfuncs = clg.get_functions_with_no_caller()
    libfuncs.discard("main")

    # Classify the vulnerable instructions by type
    mainc = len(registry.get_all_vulninst_for_func("main"))
    libvulninst = set()
    for libfunc in libfuncs:
        libvulninst |= registry.get_all_vulninst_for_func(libfunc)
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
    """ Entry point to run this analysis stand alone """
    generic_main(
        "List all vulnerable instructions found by a MACKE run",
        "The vulnerable instructions were stored in %s",
        "vulninst.json", vulninsts
    )

if __name__ == '__main__':
    main()
