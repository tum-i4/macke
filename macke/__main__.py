"""
Start a complete analysis with the MACKE toolchain on a given bitcode file
"""
import argparse
import sys

from .config import check_config
from .cgroups import initialize_cgroups, validate_cgroups
from .Macke import Macke


def str2bool(v):
    if v.lower() in ("yes", "true", "y", "t", "1"):
        return True
    if v.lower() in ("no", "false", "n", "f", "0"):
        return False
    raise argparse.ArgumentTypeError("Expected boolean value.")


def cgroups_command_check():
    """
    Parse command lines for cgroups initializer
    This duplicate parsing is required because bcfile is a 
    required argument in the other parser and thus initializing would
    not be possible without supplying it.
    """
    parser = argparse.ArgumentParser(
        description="""\
        Run modular and compositional analysis with KLEE engine on the given
        bitcode file. Depending on the program size, this may take a while.
        """
    )

    # CGroups arguments
    parser.add_argument(
        '--initialize-cgroups',
        dest='initialize_cgroups',
        action='store_true',
        help="Initialize cgroups for fuzzing (might need root access)"
    )
    parser.set_defaults(initialize_cgroups=False)

    parser.add_argument(
        '--cgroups-usergroup',
        default=None,
        help="<user>:<group> which owns the cgroup (and will use mackefuzzer)"
    )

    parser.add_argument(
        '--ignore-swap',
        dest='ignore_swap',
        action='store_true',
        help="Ignore missing swap limitations"
    )
    parser.set_defaults(ignore_swap=False)

    args, unknown = parser.parse_known_args()

    if args.initialize_cgroups:
        if args.cgroups_usergroup is None:
            print("Missing --cgroups-usergroup argument")
            sys.exit(1)
        check_config()
        if initialize_cgroups(args.cgroups_usergroup, args.ignore_swap):
            sys.exit(0)
        else:
            sys.exit(1)

def main():
    """
    Parse command line arguments, initialize and start a complete MACKE run
    """

    cgroups_command_check()

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

    #TODO: add argument for flipper mode

    parser.add_argument(
        '--use-fuzzer',
        type=str2bool,
        default=False,
        help="Toggle to use experimental fuzzing feature"
    )

    parser.add_argument(
        '--fuzz-time',
        type=int,
        default=10,
        help="Time to fuzz a single function (in minutes)"
    )

    parser.add_argument(
        '--stop-fuzz-when-done',
        type=str2bool,
        default=False,
        help="Toggle to stop fuzzer when it determines, that it is done"
    )

    parser.add_argument(
        '--generate-smart-fuzz-input',
        type=str2bool,
        default=True,
        help="Toggle to generate better input for the fuzzing engine"
    )

    parser.add_argument(
        '--fuzz-input-maxlen',
        type=int,
        default=32,
        help="Maximum array argument length for pregenerated inputs"
    )

    parser.add_argument(
        '--fuzz-bc',
        metavar=".bc-file",
        type=argparse.FileType('r'),
        help="Bitcode file, that will be used for fuzzing"
    )


    parser.add_argument(
        '--exclude-known',
        type=str2bool,
        default=True,
        help="Toggle to exclude known from phase two"
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

    parser.add_argument(
        '--ignore-swap',
        dest='ignore_swap',
        action='store_true',
        help="Ignore missing swap limitations"
    )
    parser.set_defaults(ignore_swap=False)

    check_config()

    args = parser.parse_args()


    if args.use_fuzzer and not validate_cgroups(args.ignore_swap):
        print("CGroups are not initialized correctly, please run macke --initialize-cgroups --cgroups-usergroup=<user>:<group>")
        sys.exit(1)

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

    fuzzbc = args.fuzz_bc.name if args.fuzz_bc is not None else None

    # And finally pass everything to MACKE
    macke = Macke(args.bcfile.name, args.comment, args.parent_dir,
                  args.quiet, flags_user, posixflags, posix4main, libraries=args.libraries, exclude_known_from_phase_two=args.exclude_known, use_fuzzer=args.use_fuzzer, fuzztime=args.fuzz_time, stop_fuzz_when_done=args.stop_fuzz_when_done, generate_smart_fuzz_input=args.generate_smart_fuzz_input, fuzzbc=fuzzbc, fuzz_input_maxlen=args.fuzz_input_maxlen)
    macke.run_complete_analysis()

if __name__ == "__main__":
    main()
