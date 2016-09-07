"""
Some helping functions to reduce the duplicate code for stand alone evaluation
"""
from ..ErrorRegistry import ErrorRegistry
import argparse
from os import path
import json


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
    with open(jsonfile, 'w') as f:
        json.dump(content, f)


def get_klee_registry_from_mackedir(macke_directory):
    kinfo = dict()
    with open(path.join(macke_directory, 'klee.json')) as klee_json:
        kinfo = json.load(klee_json)

    return kinfo


def get_error_registry_for_mackedir(macke_directory):
    registry = ErrorRegistry()
    klees = get_klee_registry_from_mackedir(macke_directory)

    for _, klee in klees.items():
        if "function" in klee:
            registry.create_from_dir(klee['folder'], klee['function'])
        else:
            registry.create_from_dir(klee['folder'], klee['caller'])

    return registry


def generic_main(description, feedback, filename, callback):
    mackedir = arg_parse_mackedir(description)
    store_as_json(mackedir, filename, callback(mackedir))
    if feedback:
        print(feedback % filename)
