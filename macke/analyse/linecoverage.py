"""
Generate a json file with line coverage information about a MACKE run
"""

from collections import OrderedDict
from os import path

from ..llvm_wrapper import extract_lines_of_code
from ..run_istats import extract_linecoverage
from ..Fuzzer import extract_fuzzer_coverage
from .helper import generic_main, get_klee_registry_from_mackedir

def linecoverage(macke_directory):
    """
    Extract all linecoverage information in an OrderedDict
    """


    # Extract all lines of code in the unoptimized program
    funcovs = extract_lines_of_code(
        path.join(macke_directory, "bitcode", "program.bc"))

    # Collect fuzzing coverage
    # TODO: Coverage dictionary contains both lines and functions
    coverage = extract_fuzzer_coverage(macke_directory)
    #print(coverage.keys())

    # Read klee.json information
    klees = get_klee_registry_from_mackedir(macke_directory)

    # Collect all covered and uncovered lines from all run.istats
    for _, klee in klees.items():

        istatsfile = path.join(klee['folder'], "run.istats")
        if not path.isfile(istatsfile):
            istatsfile = path.join(macke_directory, 'klee',
                                   path.basename(klee['folder']), "run.istats")

        for func, info in extract_linecoverage(istatsfile).items():
            if func in coverage:
                # Merge existing information with the new information
                coverage[func]['covered'] |= info['covered']
                coverage[func]['uncovered'] |= info['uncovered']
            else:
                # Add a new entry to the overall stats
                coverage[func] = info

    # lines only covered on some runs are considered as covered
    for func in coverage:
        coverage[func]['uncovered'] -= coverage[func]['covered']

    #for file in coverage:
    #  print (str(len(cov_dict['covered'])))
    #  print (file + ": " + str(coverage[file]['covered']))
    
    # Categorize the per function informations
    perfunction = dict()
    
    for function, position in funcovs.items():
        for file, lines in position.items():
            if function not in perfunction:
                perfunction[function] = dict()
            coverageforfile = coverage.get(function, dict())
            perfunction[function][file] = OrderedDict([
                ('covered', sorted(list(
                    set(lines) & coverageforfile.get('covered', set())))),
                ('uncovered', sorted(list(
                    set(lines) & coverageforfile.get('uncovered', set())))),
                ('removed', sorted(list((set(lines) -
                                         coverageforfile.get('covered', set())) -
                                        coverageforfile.get('uncovered', set()))
                                  ))
            ])
    '''
    for filen in coverage:
        function = coverage[
        if function not in perfunction:
            perfunction[function] = dict()
    
        coverageforfile = coverage.get(file, dict())
        perfunction[function][file] = OrderedDict([
                ('covered', sorted(list(
                    set(lines) & coverageforfile.get('covered', set())))),
                ('uncovered', sorted(list(
                    set(lines) & coverageforfile.get('uncovered', set())))),
                ('removed', sorted(list((set(lines) -
                                         coverageforfile.get('covered', set())) -
                                        coverageforfile.get('uncovered', set()))
                                  ))    
    
    '''
    # Count the absolute numbers
    covered, uncovered, removed = 0, 0, 0
    for _, position in perfunction.items():
        for _, status in position.items():
            covered += len(status['covered'])
            uncovered += len(status['uncovered'])
            removed += len(status['removed'])

    # Compose everything in a sorted result
    result = OrderedDict([
        ('total', OrderedDict(
            [
                ('covered', covered),
                ('uncovered', uncovered),
                ('removed', removed)
            ])),
        ('perfunction', OrderedDict(
            sorted(perfunction.items(), key=lambda t: t[0]))),
    ])
    return result


def main():
    """ Entry point to run this analysis stand alone """
    generic_main(
        "Extract line coverage of a MACKE run",
        "The coverage analysis was stored in %s",
        "coverage.json", linecoverage
    )


if __name__ == '__main__':
    main()
