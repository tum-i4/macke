
from collections import OrderedDict
import json
from os import listdir, path
from ..llvm_wrapper import extract_callgraph


def count_facile_chains(macke_directory):
    klees = dict()
    with open(path.join(macke_directory, 'klee.json')) as klee_json:
        klees = json.load(klee_json)

    # Just the klee runs of phase one are relevant
    klees = dict((k, v) for k, v in klees.items() if v['phase'] == 1)

    errors = dict()

    for _, klee in klees.items():
        # Find all error files in the klee folder
        errorfiles = [f for f in listdir(klee['folder']) if f.endswith(".err")]

        for errorfile in errorfiles:
            with open(path.join(klee['folder'], errorfile)) as file:
                # First line only contains reason for the error
                file.readline()

                # If the error file contains information about file and line
                # that has caused the error originally
                nextline = file.readline().strip()
                if nextline.startswith("File: "):
                    filenameline = nextline[len("File: "):]
                    linenumline = int(file.readline().strip()[len("line: "):])
                    identifier = "%s:%s" % (filenameline, linenumline)

                    # Store the error information for later
                    if klee['function'] not in errors:
                        errors[klee['function']] = set({identifier})
                    else:
                        errors[klee['function']].add(identifier)

    # Get the call graph of the analyzed program
    completegraph = extract_callgraph(path.join(macke_directory, "program.bc"))

    # Filter all functions, that can be analyzed by klee
    callgraph = dict((k, v) for k, v in completegraph.items()
                     if not v['hasfuncptrarg'] and not v['isexternal'] and (
                     not v['hasdoubleptrarg'] or k == "main"))

    total = 0
    perfunction = dict()
    perpair = dict()
    for caller, details in callgraph.items():
        inthiscaller = 0
        for callee in details['calls']:
            if callee in callgraph and caller in errors and callee in errors:
                numberOfChains = len(errors[caller] & errors[callee])
                total += numberOfChains
                inthiscaller += numberOfChains
                if caller not in perpair:
                    perpair[caller] = dict([(callee, numberOfChains)])
                else:
                    perpair[caller][callee] = numberOfChains
        perfunction[caller] = inthiscaller

    # Build the result dictionary
    result = OrderedDict()
    result['total'] = total
    result['perfunc'] = OrderedDict(
        sorted(perfunction.items(), key=lambda t: t[0]))
    result['perpair'] = OrderedDict(
        sorted(perpair.items(), key=lambda t: t[0]))

    # Dump the result to a file
    result_json = path.join(macke_directory, "facile-chains.json")
    with open(result_json, 'w') as f:
        json.dump(result, f)
    print("The runtime analysis was stored in", result_json)


def main():
    """
    Parse command line arguments and start count facile chains function
    """

    import argparse
    parser = argparse.ArgumentParser(
        description="""\
        Count all chains, that KLEE finds without prepended error summaries
        in a directory of a MACKE run
        """
    )
    parser.add_argument(
        "mackedir",
        help="The directory of a MACKE run to be analyzed")

    args = parser.parse_args()

    if (path.isdir(args.mackedir) and
            path.isfile(path.join(args.mackedir, 'klee.json'))):
        count_facile_chains(args.mackedir)
    else:
        print("ERROR: '%s' is not a directory of a MACKE run" % args.mackedir)

if __name__ == '__main__':
    main()
