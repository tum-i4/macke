"""
All interactions with KLEE
"""

from os import listdir, path
import re
import subprocess
from .config import KLEEBIN

KLEEFLAGS = [
    "--allow-external-sym-calls",
    "--libc=uclibc",
    "--max-memory=1000",
    "--only-output-states-covering-new",
    "--optimize",
    # "--output-module",  # Helpful for debugging
    "--output-source=false",  # Removing this is helpful for debugging
    "--posix-runtime",
    "--watchdog"
]


class KleeResult:
    """
    Container, that store all information about a klee run
    """

    def __init__(self, bcfile, analyzedfunc, outdir, stdoutput, flags=None):
        # Set all atttributes given by the constructor
        self.bcfile = bcfile
        self.analyzedfunc = analyzedfunc
        self.outdir = outdir
        self.flags = [] if flags is None else flags
        self.stdoutput = stdoutput

        # Calculate some statistics
        self.errorcount = self.stdoutput.count("KLEE: ERROR:")

        match = re.search(
            r"KLEE: done: generated tests = (\d+)", self.stdoutput)
        self.testcount = int(match.group(1)) if match else 0

        # Grap all the error files
        self.errfiles = [path.join(self.outdir, file)
                         for file in listdir(self.outdir)
                         if file.endswith(".err")]

        # Search for error chains [(new, old)]
        self.chained = []
        for errfile in self.errfiles:
            if errfile.endswith(".macke.err"):
                with open(errfile, 'r') as f:
                    match = re.search(r"ERROR FROM (.+\.err)\n", f.readline())
                if match:
                    self.chained.append((errfile, match.group(1)))

    def __str__(self):
        return "KLEE in %s: %s" % (self.outdir, self.stdoutput)


def execute_klee(bcfile, analyzedfunc, outdir, flags=None, flags4main=None):
    """
    Execute KLEE on bcfile with the given flag and put the output in outdir
    """

    # use empty list as default flags
    flags = [] if flags is None else flags
    flags4main = [] if flags4main is None else flags4main
    flags.extend(KLEEFLAGS)

    if analyzedfunc != "main":
        flags += ["--entry-point", "macke_%s_main" % analyzedfunc]

        # actually run KLEE
        command = [KLEEBIN, "--output-dir=" + outdir] + flags + [bcfile]
    else:
        # the main function is handled a little bit differently
        # Strange, but the flags passed to main must be append after bcfile
        command = [
            KLEEBIN, "--output-dir=" + outdir] + flags + [bcfile] + flags4main

    try:
        out = subprocess.check_output(command,
                                      stderr=subprocess.STDOUT).decode("utf-8")
    except subprocess.CalledProcessError as cperr:
        # If something went wrong, we still read the output for analysis
        out = cperr.output.decode("utf-8")

        # Some errors are expected and should not be reported
        if not any(reason in out for reason in [
                "LLVM ERROR: not enough shared memory",
                "KLEE: WATCHDOG: time expired"]):
            # throw the error to the command line
            print()  # Empty line to seperate from previous output
            print("Error during:", command)
            print(out)

    # Return a filled result container
    return KleeResult(bcfile, analyzedfunc, outdir, out, flags)


def execute_klee_targeted_search(
        bcfile, analyzedfunc, targetfunc, outdir, flags=None, flags4main=None):
    """
    Execute KLEE on a bitcode file with targeted search for targetfunc
    """

    # use empty list as default flags
    flags = [] if flags is None else flags
    flags = ["--search=ld2t", "--targeted-function=" + targetfunc] + flags
    return execute_klee(bcfile, analyzedfunc, outdir, flags, flags4main)
