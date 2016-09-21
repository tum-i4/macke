"""
Generate a json file with all runtime information inside a Macke run directory
"""

from collections import OrderedDict
from os import path

from .helper import generic_main, get_klee_registry_from_mackedir


def analyse_runtime(macke_directory):
    """
    Collect and summarize the runtime information of all KLEE runs
    """

    # Read klee.json information
    klees = get_klee_registry_from_mackedir(macke_directory)

    result = OrderedDict()
    result['total'] = 0
    result['phase'] = {'1': 0, '2': 0}
    result['entrypoint'] = {}

    for _, klee in klees.items():
        # Load runtime information from run.stats
        runtime = 0.0

        run_stats_file = path.join(klee['folder'], 'run.stats')
        # Skip non existing files
        if not path.isfile(run_stats_file):
            continue

        with open(run_stats_file) as run_stats:
            # Read the entire file
            stats = run_stats.readlines()

            # Read the position of UserTime
            runtimepos = stats[0][1:-1].split(",").index("'UserTime'")

            # Read the last row - it contains the overall values
            runtime = float(stats[-1][1:-1].split(",")[runtimepos])

        result['total'] += runtime
        result['phase'][str(klee['phase'])] += runtime

        if klee['phase'] == 1:
            entry = result['entrypoint'].get(
                klee['function'], OrderedDict([('1', 0), ('2', 0)]))
            entry['1'] += runtime
            result['entrypoint'][klee['function']] = entry
        elif klee['phase'] == 2:
            entry = result['entrypoint'].get(
                klee['caller'], OrderedDict([('1', 0), ('2', 0)]))
            entry['2'] += runtime
            result['entrypoint'][klee['caller']] = entry

        result['entrypoint'] = OrderedDict(
            sorted(result['entrypoint'].items(), key=lambda t: t[0]))

    return result


def main():
    """ Entry point to run this analysis stand alone """
    generic_main(
        "Add a summary of all KLEE runtimes to the directory of a MACKE run",
        "The runtime analysis was stored in %s",
        "runtime.json", analyse_runtime
    )

if __name__ == '__main__':
    main()
