"""
Start a complete analysis with the MACKE toolchain on a given bitcode file
"""
import argparse
from .config import check_config
from .Macke import Macke


def main():
    """
    Parse command line arguments, initialize and start a complete MACKE run
    """
    parser = argparse.ArgumentParser(
        description="""\
        Run modular and compositional analysis with KLEE engine on the given
        bitcode file. Depending on the program size, this may take a while.
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
        default=300,
        help="Maximum execution time for one KLEE run"
    )

    parser.add_argument(
        '--max-instruction-time',
        nargs='?',
        type=int,
        default=30,
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

    check_config()

    args = parser.parse_args()

    # Compose KLEE flags given directly by the user
    flags_user = [
        "--max-time=%d" % args.max_time,
        "--max-instruction-time=%d" % args.max_instruction_time
    ]

    # Compose flags for analysing the main function
    flags4main = []
    if args.sym_args:
        flags4main.append("--sym-args")
        flags4main.extend(args.sym_args)
    if args.sym_files:
        flags4main.append("--sym-files")
        flags4main.extend(args.sym_files)

    print(flags4main)

    # And finally pass everything to MACKE
    m = Macke(args.bcfile.name, args.comment, args.parent_dir,
              False, flags_user, flags4main)
    m.run_complete_analysis()

if __name__ == "__main__":
    main()
