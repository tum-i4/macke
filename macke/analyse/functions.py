"""
Collect information about the functions in program.bc
"""
from collections import OrderedDict
from os import path

from ..CallGraph import CallGraph
from .helper import generic_main, get_error_registry_for_mackedir


def functions(macke_directory):
    """
    Extract all informations about the functions of a program as an OrderedDict
    """
    clg = CallGraph(path.join(macke_directory, "bitcode", "program.bc"))

    totalfunccount = sum(1 for _, info in clg.graph.items()
                         if not info["isexternal"])
    symenccount = sum(1 for func in clg.graph
                      if clg.is_symbolic_encapsulable(func))

    registry = get_error_registry_for_mackedir(macke_directory)

    result = OrderedDict([
        ("totalfunctioncount", totalfunccount),
        ("symbolicencapsulable", symenccount),
        ("erroneousfunctioncount", registry.count_functions_with_errors()),
        ("functionswitherrors", sorted(
            [func for func in registry.forfunction]))
    ])
    return result


def main():
    """ Entry point to run this analysis stand alone """
    generic_main(
        "Collect informations about functions in a MACKE run",
        "The function analysis was stored in %s",
        "functions.json", functions
    )

if __name__ == '__main__':
    main()
