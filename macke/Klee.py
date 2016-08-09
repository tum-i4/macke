"""
Container, that store all information about a klee run
"""

import re
import subprocess
from .config import KLEEBIN


class KleeResult:

    def __init__(self, bcfile, outdir, stdoutput, flags=None):
        # Set all atttributes given by the constructor
        self.bcfile = bcfile
        self.outdir = outdir
        self.flags = [] if flags is None else flags
        self.stdoutput = stdoutput

        # Calculate some statistics
        self.errorcount = self.stdoutput.count("KLEE: ERROR:")

        m = re.search(r"KLEE: done: generated tests = (\d+)", self.stdoutput)
        self.testcount = int(m.group(1)) if m else 0

    def __str__(self):
        return "KLEE in %s: %s" % (self.outdir, self.stdoutput)


def execute_klee(bcfile, outdir, flags=None):
    """
    Execute KLEE on bcfile with the given flag and put the output in outdir
    """

    # use empty list as default flags
    flags = [] if flags is None else flags

    # actually run KLEE
    out = subprocess.check_output([
        KLEEBIN, "--output-dir=" + outdir] + flags + [bcfile],
        stderr=subprocess.STDOUT).decode("utf-8")

    # Return a filled result container
    return KleeResult(bcfile, outdir, out, flags)