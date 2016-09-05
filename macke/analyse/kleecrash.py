"""
Extract all KLEE runs, that crashes
"""
from .helper import generic_main
from collections import OrderedDict
import json
import operator
from os import path


def kleecrash(macke_directory):
    klees = dict()
    with open(path.join(macke_directory, 'klee.json')) as klee_json:
        klees = json.load(klee_json)

    result = []
    for _, kinfo in sorted(klees.items(), key=operator.itemgetter(0)):
        with open(path.join(kinfo['folder'], "output.txt"), 'r') as output:
            content = output.read()
            if "llvm::sys::PrintStackTrace" in content:
                kresult = OrderedDict(sorted(
                    kinfo.items(), key=lambda t: t[0]))
                kresult["output"] = content
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
