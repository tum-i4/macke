"""
Container, that store all information about a klee run
"""

import subprocess
from .config import KLEEBIN


class KleeRound:

    def __init__(self, bcfile, outdir, flags=None, entrypoint="main"):
        self.bcfile = bcfile
        self.outdir = outdir
        self.entrypoint = entrypoint
        self.flags = [] if flags is None else flags
        self.executed = False
        self.output = "No run yet"

    def __str__(self):
        return "KLEE in %s: %s" % (self.outdir, self.output)

    def run(self):
        # assert, that this round was not run earlier
        assert not self.executed

        # Execute KLEE with all details and store the output
        self.output = subprocess.check_output([
            KLEEBIN, "--entry-point=" + self.entrypoint,
            "--output-dir=" + self.outdir] + self.flags + [self.bcfile],
            stderr=subprocess.STDOUT).decode("utf-8")

        # Mark this KLEE run as executed
        self.executed = True

    def contains_errors(self):
        return "KLEE: ERROR:" in self.output
