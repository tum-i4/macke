"""
All interactions with KLEE
"""

import json
import operator
import re
import shutil
import subprocess
import tempfile

from collections import OrderedDict
from os import listdir, path, makedirs

from .config import KLEEBIN
from .constants import ERRORFILEEXTENSIONS, KLEEFLAGS


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
        match = re.search(
            r"KLEE: done: generated tests = (\d+)", self.stdoutput)
        self.testcount = int(match.group(1)) if match else 0

        # Grap all the error files
        self.errfiles = ([path.join(self.outdir, file)
                          for file in listdir(self.outdir)
                          if any(file.endswith(ext)
                                 for ext in ERRORFILEEXTENSIONS)]
                         if path.isdir(self.outdir) else [])

        self.errorcount = len(self.errfiles)

        # Search for error chains [(new, old)]
        self.chained = []
        for errfile in self.errfiles:
            if errfile.endswith(".macke.err"):
                with open(errfile, 'r') as file:
                    match = re.search(
                        r"ERROR FROM (.+\.err)\n", file.readline())
                if match:
                    self.chained.append((errfile, match.group(1)))

    def __str__(self):
        return "KLEE in %s: %s" % (self.outdir, self.stdoutput)

    def get_outname(self):
        """ Get the directory name of the KLEE output directory """
        return path.basename(self.outdir)

    def did_klee_crash(self):
        """ checks, if KLEE crashs during this analysis """
        return "llvm::sys::PrintStackTrace" in self.stdoutput

    def did_klee_run_out_of_time(self):
        """ checks, if KLEE runs out of time during the analysis """
        return any(message in self.stdoutput for message in [
            "KLEE: WATCHDOG: time expired",
            "KLEE: WARNING: max-instruction-time exceeded",
            "KLEE: HaltTimer invoked",
        ])

    def did_klee_run_out_of_memory(self):
        """ checks, if KLEE runs out of memory during the analysis """
        return any(message in self.stdoutput for message in [
            "not enough shared memory for counterexample",
            "Memory limit exceeded.",
            "states (over memory cap)",
            "skipping fork (memory cap exceeded)",
        ])

    def did_klee_run_out_of_ressources(self):
        """
        checks, if KLEE runs out of time or out of memory during the analysis
        """
        return (self.did_klee_run_out_of_time() or
                self.did_klee_run_out_of_memory())

    def did_klee_reach_error_summary(self, callee):
        """ checks, if the KLEE run reaches the error summary of callee """
        return "MACKE: Summery for %s reached" % callee in self.stdoutput


def reconstruct_from_macke_dir(mackedir):
    """ Reconstruct all KLEE objects of a MACKE run """
    return reconstruct_from_klee_json(path.join(mackedir, "klee.json"))


def reconstruct_from_klee_json(kleejson):
    """ Reconstruct all KLEE objects mentioned in a klee.json """
    assert kleejson.endswith("klee.json")

    klees = OrderedDict()
    with open(kleejson, 'r') as jsonfile:
        klees = json.load(jsonfile)

    result = []
    for _, kinfo in sorted(klees.items(), key=operator.itemgetter(0)):
        # Read the KLEE's output
        stdoutput = ""
        with open(path.join(kinfo["folder"], "output.txt"), 'r') as out:
            stdoutput = out.read()

        # Build a new KLEE object for the result list
        result.append(KleeResult(
            kinfo["bcfile"],
            kinfo["function"] if "function" in kinfo else kinfo["caller"],
            kinfo["folder"],
            stdoutput
        ))

    return result


def execute_klee(
        bcfile, analyzedfunc, outdir,
        flags=None, posixflags=None, posix4main=None):
    """
    Execute KLEE on bcfile with the given flag and put the output in outdir
    """

    # use empty list as default flags
    flags = [] if flags is None else flags
    flags.extend(KLEEFLAGS)

    # Build the posix flags
    posixflags = [] if posixflags is None else posixflags
    posix4main = [] if posix4main is None else posix4main

    if analyzedfunc == "main":
        # the main function is handled a little bit differently
        posixflags.extend(posix4main)
    else:
        flags += ["--entry-point", "macke_%s_main" % analyzedfunc]

    # Strange, but the posix flags must be append after bcfile
    command = ([KLEEBIN, "--output-dir=" + outdir] + flags +
               [bcfile] + posixflags)

    # Create a new, empty directory
    tmpdir = tempfile.mkdtemp(prefix="macke_tmp_")

    # actually run KLEE
    try:
        out = subprocess.check_output(
            command, stderr=subprocess.STDOUT,
            cwd=tmpdir).decode("utf-8", 'ignore')
    except subprocess.CalledProcessError as cperr:
        # If something went wrong, we still read the output for analysis
        # We might have to create the outdir though, if klee failed and didn't create it
        if not path.exists(outdir):
            makedirs(outdir)
        out = cperr.output.decode("utf-8", 'ignore')

    # Remove the temporary directory
    shutil.rmtree(tmpdir)

    # Store all the output in a textfile inside the klee directory
    with open(path.join(outdir, "output.txt"), 'w') as file:
        file.write(out)

    # Return a filled result container
    return KleeResult(bcfile, analyzedfunc, outdir, out, flags)


def execute_klee_targeted_search(
        bcfile, analyzedfunc, targetfunc, outdir,
        flags=None, posixflags=None, posix4main=None):
    """
    Execute KLEE on a bitcode file with sonar search for targetfunc call
    """

    # use empty list as default flags
    flags = [] if flags is None else flags
    flags = ["--search=sonar", "--sonar-target=function-call", "--sonar-target-info=" + targetfunc] + flags
    return execute_klee(
        bcfile, analyzedfunc, outdir, flags, posixflags, posix4main)
