"""
Extract all KLEE runs, that crashes
"""
from collections import OrderedDict

from ..Klee import reconstruct_from_macke_dir
from .helper import generic_main, get_klee_registry_from_mackedir


def kleecrash(macke_directory):
    """
    Extract all information about KLEE crashes in an OrderedDict
    """
    klees = reconstruct_from_macke_dir(macke_directory)

    kinfo = get_klee_registry_from_mackedir(macke_directory)

    result = []
    for klee in klees:
        if klee.did_klee_crash():
            kresult = OrderedDict(sorted(
                kinfo[klee.get_outname()].items(), key=lambda t: t[0]))
            del kresult["bcfile"]
            kresult["output"] = klee.stdoutput
            result.append(kresult)

    return result


def main():
    """ Entry point to run this analysis stand alone """
    generic_main(
        "Extract informations about all KLEE runs that crashes in a MACKE run",
        "The KLEE crashes were stored in %s",
        "kleecrash.json", kleecrash
    )

if __name__ == '__main__':
    main()
