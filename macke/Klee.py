"""
Container, that store all information about a klee run
"""

from os import listdir, path
import re
import subprocess
from .config import KLEEBIN


class KleeResult:

    def __init__(self, bcfile, analyzedfunc, outdir, stdoutput, flags=None):
        # Set all atttributes given by the constructor
        self.bcfile = bcfile
        self.analyzedfunc = analyzedfunc
        self.outdir = outdir
        self.flags = [] if flags is None else flags
        self.stdoutput = stdoutput

        # Calculate some statistics
        self.errorcount = self.stdoutput.count("KLEE: ERROR:")

        m = re.search(r"KLEE: done: generated tests = (\d+)", self.stdoutput)
        self.testcount = int(m.group(1)) if m else 0

        # Grap all the error files
        self.errfiles = [path.join(self.outdir, f)
                         for f in listdir(self.outdir)
                         if f.endswith(".err")]

        # Search for error chains [(new, old)]
        self.chained = []
        for errfile in self.errfiles:
            if errfile.endswith(".macke.err"):
                with open(errfile, 'r') as f:
                    m = re.search(r"ERROR FROM (.+\.err)\n", f.readline())
                if m:
                    self.chained.append((errfile, m.group(1)))

    def __str__(self):
        return "KLEE in %s: %s" % (self.outdir, self.stdoutput)


def execute_klee(bcfile, analyzedfunc, outdir, flags=None):
    """
    Execute KLEE on bcfile with the given flag and put the output in outdir
    """

    # use empty list as default flags
    flags = [] if flags is None else flags

    # --disable-internalize can be removed after, KLEE bug #454 is fixed
    flags += ["--entry-point", "macke_%s_main" % analyzedfunc,
              "--disable-internalize"]

    # actually run KLEE
    out = subprocess.check_output([
        KLEEBIN, "--output-dir=" + outdir] + flags + [bcfile],
        stderr=subprocess.STDOUT).decode("utf-8")

    # Return a filled result container
    return KleeResult(bcfile, analyzedfunc, outdir, out, flags)


def execute_klee_targeted_search(
        bcfile, analyzedfunc, targetfunc, outdir, flags=None):
    # use empty list as default flags
    flags = [] if flags is None else flags
    flags = ["--search=ld2t", "--targeted-function=" + targetfunc] + flags
    return execute_klee(bcfile, analyzedfunc, outdir, flags)
