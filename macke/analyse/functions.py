"""
Collect information about the functions in program.bc
"""
from .helper import get_error_registry_for_mackedir, generic_main
from ..CallGraph import CallGraph
from collections import OrderedDict

from os import path


def functions(macke_directory):
    cg = CallGraph(path.join(macke_directory, "bitcode", "program.bc"))

    totalfunccount = sum(1 for _, info in cg.graph.items()
                         if not info["isexternal"])
    symenccount = sum(1 for func in cg.graph
                      if cg.is_symbolic_encapsulable(func))

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
    generic_main(
        "Collect informations about functions in a MACKE run",
        "The function analysis was stored in %s",
        "functions.json", functions
    )

if __name__ == '__main__':
    main()
