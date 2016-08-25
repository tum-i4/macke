"""
Generate a json file with all runtime information inside a Macke run directory
"""

from .helper import parse_mackedir
from ..llvm_wrapper import extract_lines_of_code
from ..run_istats import extract_linecoverage

from collections import OrderedDict
import json
from os import path
from pprint import pprint


def linecoverage(macke_directory):
    # Read klee.json information
    klees = dict()
    with open(path.join(macke_directory, 'klee.json')) as klee_json:
        klees = json.load(klee_json)

    # Extract all lines of code in the unoptimized program
    funcovs = extract_lines_of_code(path.join(macke_directory, "program.bc"))

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
                ('covered', sorted(list(set(lines) & istats[file]['covered']))),
                ('uncovered', sorted(list(
                    set(lines) & istats[file]['uncovered']))),
                ('removed', sorted(list(set(lines)
                    - istats[file]['covered'] - istats[file]['uncovered'])))
            ])

    # Count the absolute numbers
    covered, uncovered, removed = 0, 0, 0
    for _, position in perfunction.items():
        for _, status in position.items():
            covered += len(status['covered'])
            uncovered += len(status['uncovered'])
            removed += len(status['removed'])

    # Compose everything in a sorted result
    result = OrderedDict([('total', OrderedDict([
            ('covered', covered),
            ('uncovered', uncovered),
            ('removed', removed)])
        ),
        ('perfunction', OrderedDict(
            sorted(perfunction.items(), key=lambda t: t[0])))
    ])

    coverage_json = path.join(macke_directory, "coverage.json")
    with open(coverage_json, 'w') as f:
        json.dump(result, f)

    print("The coverage analysis was stored in", coverage_json)


def main():
    linecoverage(parse_mackedir("Extract line coverage of a MACKE run"))

if __name__ == '__main__':
    main()
