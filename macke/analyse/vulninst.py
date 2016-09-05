"""
List all vulnerable instructions found by a MACKE run
"""
from .helper import get_error_registry_for_mackedir, generic_main
from collections import OrderedDict
import operator


def vulninst(macke_directory):
    registry = get_error_registry_for_mackedir(macke_directory)

    vulninstdict = OrderedDict()
    for vulninst, errors in sorted(
            registry.forvulninst.items(), key=operator.itemgetter(0)):
        vulninstdict[vulninst] = []
        for error in sorted(errors):
            odict = error.as_ordered_dict()
            del odict['vulnerableInstruction']
            vulninstdict[vulninst].append(odict)

    result = OrderedDict([
        ("vulninstcount", registry.count_vulnerable_instructions()),
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
