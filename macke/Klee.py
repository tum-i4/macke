"""
All interactions with KLEE
"""

import json
import operator
import re
import shutil
import subprocess
import tempfile
import signal
import time
import os

from collections import OrderedDict
from os import listdir, path, makedirs, killpg, getpgid, setsid

from .config import KLEEBIN
from .constants import ERRORFILEEXTENSIONS, KLEEFLAGS

from .Logger import Logger


# python implementation of timed check_output fails to kill klee correctly
# Thus, write a working implementation ourself using killgroup
# https://bugs.python.org/issue31935 and similar ones

def _check_output(command, cwd, timeout):
    proc = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, cwd=cwd, preexec_fn=setsid)
    try:
        output, _ = proc.communicate(None, timeout=timeout)
    except subprocess.TimeoutExpired:
        killpg(getpgid(proc.pid), signal.SIGKILL)
        # timeout for sanity check
        output, _ = proc.communicate(None, timeout=timeout)
        raise subprocess.TimeoutExpired(proc.args, timeout, output=output)

    retcode = proc.poll()

    if retcode:
        raise subprocess.CalledProcessError(retcode, proc.args, output=output)
    return output

class KleeResult:
    """
    Container, that store all information about a klee run
    """

    def __init__(self, bcfile, analyzedfunc, outdir, stdoutput, flags=None, progress=0):
        # Set all atttributes given by the constructor
        self.bcfile = bcfile
        self.analyzedfunc = analyzedfunc
        self.outdir = outdir
        self.flags = [] if flags is None else flags
        self.stdoutput = stdoutput
        self.progress = progress

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
                with open(errfile, 'r', errors='ignore') as file:
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
        if not path.isfile(path.join(kinfo["folder"], "output.txt")):
            continue
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

def parse_run_istats(istats_file):
    istats = open(istats_file)

    covered = {}

    cur_file = None

    for line in istats:
        if line.startswith("fl="):
            cur_file = line.split("=")[1].strip()
            continue

        tokens = line.split()
        if len(tokens) != 15:
            continue
        src, cov = int(tokens[1]), int(tokens[2])  # Read source-level coverage rather than LLVM level

        if (cov > 0):
            if cur_file not in covered.keys():  # The covered file is newly covered
                covered[cur_file] = {}
            covered[cur_file][src] = cov
    return covered

def compute_klee_progress(path: str):
    #progress_done = False
    tmp_istats_dir = tempfile.mkdtemp()
    os.system("cp " + os.path.join(path, "run.istats") + " " + tmp_istats_dir)
    new_covered = parse_run_istats(os.path.join(tmp_istats_dir, "run.istats"))
    klee_progress = []
    for f in new_covered.keys():
        for l in new_covered[f].keys():
            if (f, l) not in klee_progress:
                klee_progress.append((f, l))
                #progress_done = True

    shutil.rmtree(tmp_istats_dir)
    return klee_progress#(klee_progress, progress_done)

SATURATION_CHECK_PERIOD = 6
def wait_for_klee_saturation(start_time, max_time_each, path, klee_progress, plot_data_logger):
    saturated = False
    #progress_done = False

    while not saturated:
        if (time.time() - start_time) > int(max_time_each):
            Logger.log("KLEE saturated because of timeout.\n", verbosity_level="info")
            saturated = True
            continue

        if (int(max_time_each) + start_time - time.time()) > SATURATION_CHECK_PERIOD:
            # we can sleep an entire period and recheck the output
            time.sleep(12)
        else:
            # sleep what time is left and do a last check
            time.sleep(int(max_time_each) + start_time - time.time())

        if not os.path.exists(os.path.join(path, "run.istats")):
            Logger.log("Path " + os.path.join(path, "run.istats") + " does not exits (yet)\n", verbosity_level="debug")
            continue

        len_old_covered = len(klee_progress)

        klee_progress = compute_klee_progress(path)
        Logger.log("compute_klee_progress: size of progress is " + str(len(klee_progress)) + "\n",
                   verbosity_level="debug")

        if len_old_covered < len(klee_progress):
            Logger.log("Continuing KLEE. Line coverage increased from " + str(len_old_covered) + " to " +
                       str(len(klee_progress)) + "\n", verbosity_level="info")
        else:
            Logger.log("KLEE saturated. No new line-coverage found\n", verbosity_level="info")
            saturated = True
        if plot_data_logger:
            plot_data_logger.log_klee_coverage()

    return len(klee_progress)

def execute_klee(
        bcfile, analyzedfunc, outdir, timeout, flipper_mode,
        flags=None, posixflags=None, posix4main=None, no_optimize=False, afl_to_klee_dir="", plot_data_logger=None):
    """
    Execute KLEE on bcfile with the given flag and put the output in outdir
    """

    # use empty list as default flags
    flags = [] if flags is None else flags

    progress = 0

    '''
    time_prefix = "--max-time="
    # Get the timeout from the passed flags (hacky)
    for f in flags:
        if f.startswith(time_prefix):
            # double the timeout for killing to be safe with time inprecisions
            timeout = 2 * int(f[len(time_prefix):])
            break
    '''

    flags.extend(KLEEFLAGS)
    if no_optimize:
        flags.remove("--optimize")

    if timeout is None:
        flags.append("--stats-write-interval=3600")
        flags.append("--istats-write-interval=3600")
        timeout = 3600
    else:
        if not flipper_mode:
            flags.append("--stats-write-interval=" + str(timeout))
            flags.append("--istats-write-interval=" + str(timeout))
        else: # flipper
            # set write-interval to the timeout / SATURATION_CHECK_PERIOD
            if timeout > SATURATION_CHECK_PERIOD:
                flags.append("--stats-write-interval=" + str(SATURATION_CHECK_PERIOD))
                flags.append("--istats-write-interval=" + str(SATURATION_CHECK_PERIOD))
            else:
                # low timeout
                flags.append("--stats-write-interval=1")
                flags.append("--istats-write-interval=1")

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

    Logger.log("KLEE command: " + str(command) + "\n", verbosity_level="debug")

    out = ""

    # actually run KLEE
    if flipper_mode:
        # AFL->KTest conversion already done
        command += " -seed-out-dir=" + afl_to_klee_dir
        # start running KLEE with total timeout

        # init klee progress
        if not os.path.exists(os.path.join(outdir, "run.istats")):
            klee_progress = []
            initial_progress_size = 0
        else:
            # we had some previous progress
            klee_progress = compute_klee_progress(outdir)
            initial_progress_size = len(klee_progress)

            Logger.log("compute_klee_progress: initial progress size is " + str(initial_progress_size) + "\n",
                       verbosity_level="debug")

        proc = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, cwd=tmpdir, preexec_fn=setsid)

        start_time = time.time()
        if timeout > 12:
            time.sleep(12)  # Takes a lot of time for KLEE to generate anything meaningful
            # check for saturation
            progress = wait_for_klee_saturation(start_time, timeout, outdir, klee_progress, plot_data_logger) - \
                       initial_progress_size
        else:
            # low timeout, no point in checking saturation
            time.sleep(timeout)

        # klee saturated
        killpg(getpgid(proc.pid), signal.SIGKILL)
        retcode = proc.poll()
    else:
        try:
            out = _check_output(
                command, cwd=tmpdir,
                timeout=timeout).decode("utf-8", 'ignore')
            klee_progress = compute_klee_progress(outdir)
            progress = len(klee_progress)
        except subprocess.TimeoutExpired as terr:
            out = terr.output.decode("utf-8", 'ignore')
            out += "\n--- kill(9)ed by MACKE for overstepping max-time twice"
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
    return KleeResult(bcfile, analyzedfunc, outdir, out, flags, progress)


def execute_klee_targeted_search(
        bcfile, analyzedfunc, targetfunc, outdir,
        flags=None, posixflags=None, posix4main=None, no_optimize=False):
    """
    Execute KLEE on a bitcode file with sonar search for targetfunc call
    """

    # use empty list as default flags
    flags = [] if flags is None else flags
    flags = ["--search=sonar", "--sonar-target=function-call", "--sonar-target-info=" + targetfunc] + flags
    return execute_klee(
        bcfile, analyzedfunc, outdir, False, flags, posixflags, posix4main, no_optimize)
