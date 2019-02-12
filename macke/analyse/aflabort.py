"""
Extract all AFL runs that aborted, because no input was non-crashing
"""

from os import path

from collections import OrderedDict
from .helper import generic_main, get_fuzz_outdirs

def aflabort(macke_directory):

    result = OrderedDict()
    aborts = []
    for (function, outpath) in get_fuzz_outdirs(macke_directory):
        outputfile = path.join(outpath, "output.txt")
        assert path.exists(outputfile)

        with open(outputfile, 'r') as f:
            for line in f:
                if "PROGRAM ABORT" in line:
                    aborts.append({ "function": function, "path": outpath, "abortline": line})

    result["count"] = len(aborts)
    result["detail"] = aborts

    return result



def main():
    """ Entry point to run this analysis stand alone """
    generic_main(
        "Extract informations about all AFL runs that aborted in a MACKE run",
        "The AFL aborts were stored in %s",
        "aflabort.json", aflabort
    )

if __name__ == '__main__':
    main()
