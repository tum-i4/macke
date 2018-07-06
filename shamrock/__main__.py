"""
Start a complete analysis with the MACKE toolchain on a given bitcode file
"""
import argparse

from macke.config import check_config
from .shamrock import Shamrock


def main():
    """
    Parse command line arguments, initialize and start a complete MACKE run
    """
    parser = argparse.ArgumentParser(
        description="""\
        Run KLEE and some additional analysis on the given bitcode file.
        """
    )

    parser.add_argument(
        'bcfile',
        metavar=".bc-file",
        type=argparse.FileType('r'),
        help="Bitcode file, that will be analyzed"
    )

    parser.add_argument(
        '--comment',
        nargs='?',
        default="",
        help="Additional comment, that will be stored in the output directory")

    parser.add_argument(
        '--parent-dir',
        nargs='?',
        default="/tmp/macke",
        help="The output directory of the run is put inside this directory")

    parser.add_argument(
        '--max-time',
        nargs='?',
        type=int,
        default=120,
        help="Maximum execution time for one KLEE run"
    )

    parser.add_argument(
        '--max-instruction-time',
        nargs='?',
        type=int,
        default=12,
        help="Maximum execution time KLEE can spend on one instruction"
    )

    parser.add_argument(
        '--sym-args',
        nargs=3,
        metavar=("<min-argvs>", "<max-argvs>", "<max-len>"),
        help="Symbolic arguments passed to main function"
    )

    parser.add_argument(
        '--sym-files',
        nargs=2,
        metavar=("<no-sym-files>", "<sym-file-len>"),
        help="Symbolic file argument passed to main function"
    )

    parser.add_argument(
        '--sym-stdin',
        type=int,
        metavar="<stdin-size>",
        help="Use symbolic stdin with size <stdin-size>"
    )

    parser.add_argument(
        '--libraries',
        type=lambda s : s.split(','),
        default=None,
        help="Libraries that are needed for linking (fuzzing only)"
    )

    parser.add_argument(
        '--quiet',
        dest='quiet',
        action='store_true'
    )
    parser.set_defaults(quiet=False)

    check_config()

    args = parser.parse_args()

    # Compose KLEE flags given directly by the user
    flags_user = [
        "--max-time=%d" % args.max_time,
        "--max-instruction-time=%d" % args.max_instruction_time
    ]

    # Compose flags for analysing the main function
    posix4main = []
    if args.sym_args:
        posix4main.append("--sym-args")
        posix4main.extend(args.sym_args)

    posixflags = []
    if args.sym_files:
        posixflags.append("--sym-files")
        posixflags.extend(args.sym_files)

    if args.sym_stdin:
        posixflags.append("-sym-stdin")
        posixflags.append(str(args.sym_stdin))

    # And finally pass everything to shamrock
    shamrock = Shamrock(args.bcfile.name, args.comment, args.parent_dir, args.quiet,
                        flags_user, posixflags, posix4main, args.libraries)
    shamrock.run_complete_analysis()


if __name__ == "__main__":
    main()
