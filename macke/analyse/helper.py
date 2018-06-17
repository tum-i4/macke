"""
Some helping functions to reduce the duplicate code for stand alone evaluation
"""
import argparse
import json
from collections import OrderedDict
from os import path, listdir

from ..ErrorRegistry import ErrorRegistry

from ..Error import Error


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


def append_to_registry_from_fuzzdir(registry, fuzzdir):
    prefix = "fuzz_out_"
    for f in listdir(fuzzdir):
        if not f.startswith(prefix):
            continue
        fpath = path.join(fuzzdir, f)
        function = f[len(prefix):]
        if path.islink(fpath) or not path.isdir(fpath):
            continue

        errordir = path.join(fpath, "macke_errors")

        # sanity check
        if path.islink(errordir) or not path.isdir(errordir):
            continue
        registry.create_from_dir(errordir, function)




def get_klee_registry_from_mackedir(macke_directory):
    """
    Build an OrderedDict with informations about all KLEE runs in a MACKE run
    """
    kinfo = OrderedDict()
    with open(path.join(macke_directory, 'klee.json')) as klee_json:
        kinfo = json.load(klee_json, object_pairs_hook=OrderedDict)

    return kinfo


def get_error_registry_for_mackedir(macke_directory, callgraph):
    """
    Build an error Registry for a MACKE run
    """
    Error.set_program_functions(callgraph.get_internal_functions())
    macke_directory = path.abspath(macke_directory)
    registry = ErrorRegistry()
    klees = get_klee_registry_from_mackedir(macke_directory)

    if path.isdir(path.join(macke_directory, "fuzzer")):
        append_to_registry_from_fuzzdir(registry, path.join(macke_directory, "fuzzer"))

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
