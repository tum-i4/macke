"""
Extract all KLEE runs, that crashes
"""
from .helper import get_klee_registry_from_mackedir, generic_main
from ..Klee import reconstruct_from_macke_dir
from collections import OrderedDict


def kleecrash(macke_directory):
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
    generic_main(
        "Extract informations about all KLEE runs that crashes in a MACKE run",
        "The KLEE crashes were stored in %s",
        "kleecrash.json", kleecrash
    )

if __name__ == '__main__':
    main()
