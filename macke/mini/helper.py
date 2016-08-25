import argparse
from os import path

def parse_mackedir(description):
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
        raise ValueError("'%s' is not a directory of a MACKE run"
            % args.mackedir)
