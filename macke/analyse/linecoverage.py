"""
Generate a json file with line coverage information about a MACKE run
"""

from .helper import get_klee_registry_from_mackedir, generic_main
from ..llvm_wrapper import extract_lines_of_code
from ..run_istats import extract_linecoverage

from collections import OrderedDict
from os import path


def linecoverage(macke_directory):
    # Read klee.json information
    klees = get_klee_registry_from_mackedir(macke_directory)

    # Extract all lines of code in the unoptimized program
    funcovs = extract_lines_of_code(
        path.join(macke_directory, "bitcode", "program.bc"))

    # Collect all covered and uncovered lines from all run.istats
    istats = dict()
    for _, klee in klees.items():
        for file, info in extract_linecoverage(
                path.join(klee['folder'], "run.istats")).items():
            if file in istats:
                # Merge existing information with the new information
                istats[file]['covered'] |= info['covered']
                istats[file]['uncovered'] |= info['uncovered']
            else:
                # Add a new entry to the overall stats
                istats[file] = info

    # lines only covered on some runs are considered as covered
    for file in istats:
        istats[file]['uncovered'] -= istats[file]['covered']

    # Categorize the per function informations
    perfunction = dict()
    for function, position in funcovs.items():
        for file, lines in position.items():
            if function not in perfunction:
                perfunction[function] = dict()
            perfunction[function][file] = OrderedDict([
                ('covered', sorted(list(
                    set(lines) & istats[file]['covered']))),
                ('uncovered', sorted(list(
                    set(lines) & istats[file]['uncovered']))),
                ('removed', sorted(list(set(lines) - istats[file]['covered'] -
                                        istats[file]['uncovered'])))
            ])

    # Count the absolute numbers
    covered, uncovered, removed = 0, 0, 0
    for _, position in perfunction.items():
        for _, status in position.items():
            covered += len(status['covered'])
            uncovered += len(status['uncovered'])
            removed += len(status['removed'])

    # Compose everything in a sorted result
    result = OrderedDict([('total', OrderedDict(
        [
            ('covered', covered),
            ('uncovered', uncovered),
            ('removed', removed)
        ])),
        ('perfunction', OrderedDict(
            sorted(perfunction.items(), key=lambda t: t[0])))
    ])
    return result


def main():
    generic_main(
        "Extract line coverage of a MACKE run",
        "The coverage analysis was stored in %s",
        "coverage.json", linecoverage
    )

if __name__ == '__main__':
    main()
