"""
Some helping functions to reduce the duplicate code for stand alone evaluation
"""

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


def generic_main(description, feedback, filename, callback):
    mackedir = arg_parse_mackedir(description)
    store_as_json(mackedir, filename, callback(mackedir))
    if feedback:
        print(feedback % filename)
