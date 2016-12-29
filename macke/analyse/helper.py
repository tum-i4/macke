"""
Some helping functions to reduce the duplicate code for stand alone evaluation
"""
import argparse
import json
from collections import OrderedDict
from os import path

from ..ErrorRegistry import ErrorRegistry


def arg_parse_mackedir(description):
    """
    Parse command line arguments for macke directory
    """

    parser = argparse.ArgumentParser(
        description=description
    )
    parser.add_argument(
        "mackedir",
        help="The directory of a MACKE run to be analyzed")

    args = parser.parse_args()

    if (path.isdir(args.mackedir) and
            path.isfile(path.join(args.mackedir, 'klee.json'))):
        return args.mackedir
    else:
        raise ValueError("'%s' is not a directory of a MACKE run" %
                         args.mackedir)


def store_as_json(macke_directory, filename, content):
    """
    Store content as json inside filename
    """
    jsonfile = path.join(macke_directory, filename)
    with open(jsonfile, 'w') as file:
        json.dump(content, file)


def get_klee_registry_from_mackedir(macke_directory):
    """
    Build an OrderedDict with informations about all KLEE runs in a MACKE run
    """
    kinfo = OrderedDict()
    with open(path.join(macke_directory, 'klee.json')) as klee_json:
        kinfo = json.load(klee_json, object_pairs_hook=OrderedDict)

    return kinfo


def get_error_registry_for_mackedir(macke_directory):
    """
    Build an error Registry for a MACKE run
    """
    registry = ErrorRegistry()
    klees = get_klee_registry_from_mackedir(macke_directory)

    for _, klee in klees.items():
        if "function" in klee:
            registry.create_from_dir(klee['folder'], klee['function'])
        else:
            registry.create_from_dir(klee['folder'], klee['caller'])

    return registry


def generic_main(description, feedback, filename, callback):
    """
    Entry point to run an analyse-script stand alone. It reads a MACKE
    directory, perform the analysis and store the result as a json file.
    """
    mackedir = arg_parse_mackedir(description)
    store_as_json(mackedir, filename, callback(mackedir))
    if feedback:
        print(feedback % filename)
