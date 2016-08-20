"""
Core class for MACKE execution.
Contains methods for both phases and some analysis
"""

from collections import OrderedDict
from datetime import datetime
import json
from multiprocessing import Pool, Manager
from os import makedirs, path, symlink, remove
import shutil
import sys
from time import sleep
from progressbar import ProgressBar, widgets
from .CallGraph import CallGraph
from .config import CONFIGFILE, THREADNUM, get_current_git_hash
from .Klee import execute_klee, execute_klee_targeted_search
from .llvm_wrapper import (
    encapsulate_symbolic, optimize_redundant_globals, prepend_error)

WIDGETS = [
    widgets.Percentage(),
    ' (', widgets.SimpleProgress(), ')',
    ' ', widgets.Bar(),
    ' ', widgets.Timer(),
    ' ', widgets.ETA(),
]


class Macke:
    """
    Main container for all steps of the MACKE analysis
    """

    def __init__(self, bitcodefile, comment="",
                 parentdir="/tmp/macke", quiet=False,
                 flags_user=None, posixflags=None, posix4main=None):
        # Only accept valid files and directory
        assert path.isfile(bitcodefile)

        # store the path to the analyzed bitcode file
        self.bitcodefile = bitcodefile

        # Store information from command line
        self.comment = comment
        self.flags_user = flags_user if flags_user is not None else []
        self.posixflags = posixflags if posixflags is not None else []
        self.posix4main = posix4main if posix4main is not None else []

        # generate name of directory with all run results
        self.starttime = datetime.now()
        newdirname = self.starttime.strftime("%Y-%m-%d-%H-%M-%S")
        self.rundir = path.join(parentdir, newdirname)
        self.parentdir = parentdir

        # Generate the path for the bitcode directory
        self.bcdir = self.rundir

        # Generate the filename for the copy of the program
        self.program_bc = path.join(self.bcdir, "program.bc")
        self.symmains_bc = path.join(self.bcdir, "symmains.bc")
        self.prepend_bc = path.join(self.bcdir, "prepend.bc")

        # Generate the directory containing all klee runs
        self.kleedir = path.join(self.rundir, "klee")

        # Filename, where the index of the klee runs is stored
        self.kleejson = path.join(self.rundir, "klee.json")

        # Internal counter for the number of klee runs
        self.kleecount = 0

        # Initialize some statistic counter
        self.testcases = 0
        self.errfunccount = 0
        self.errtotalcount = 0
        self.timeout = 0
        self.outofmemory = 0

        # Map of function -> [kleeruns triggering an error]
        self.errorkleeruns = {}

        # Information about the error chains
        self.errorchains = dict()
        self.errorchainheads = set()

        # Some attributes, that are filled later
        self.callgraph = None
        self.chainsfrommain = 0
        self.starttimephase2 = None
        self.endtime = None

        # Setting quiet == True suppress all outputs
        self.quiet = quiet

    def get_next_klee_directory(self, info):
        """
        Get the name for the next KLEE output directory and register the name
        with the given info for klee.json. KLEE cannot generate this names on
        his own, because multiple instances are executed in parallel.
        """

        self.kleecount += 1
        kleeout = "klee-out-%d" % self.kleecount
        kleepath = path.join(self.kleedir, kleeout)

        # Add the new file also to the klee index
        infojson = dict(info)
        infojson['folder'] = kleepath
        outjson = dict()
        outjson[kleeout] = OrderedDict(
            sorted(infojson.items(), key=lambda t: t[0]))
        with open(self.kleejson, 'a') as f:
            # Prepend separator for all but the first entry
            if self.kleecount != 1:
                f.write(", ")
            f.write(json.dumps(outjson)[1:-1])

        return kleepath

    def run_complete_analysis(self):
        """
        Run all consecutive steps of the analysis
        """

        self.run_initialization()
        self.run_phase_one()
        self.run_phase_two()
        self.run_finalization()

    def run_initialization(self):
        """
        Initialize the MACKE output directory
        """

        # Create an some empty directories
        makedirs(self.bcdir)
        makedirs(self.kleedir)

        # Copy the unmodified bitcode file
        shutil.copy2(self.bitcodefile, self.program_bc)

        # Copy macke's config file
        shutil.copy2(CONFIGFILE, self.rundir)

        # Store some basic information about the current run
        with open(path.join(self.rundir, "info.json"), 'w') as f:
            info = OrderedDict()
            info["macke-git-version-hash"] = get_current_git_hash()
            info["analyzed-bitcodefile"] = path.abspath(self.bitcodefile)
            info["run-argv"] = sys.argv
            info["comment"] = self.comment
            json.dump(info, f)

        # Initialize a file for klee directory mapping
        with open(self.kleejson, 'w') as f:
            f.write("{")

        # Print some information for the user
        self.qprint(
            "Start analysis of %s in %s" % (self.bitcodefile, self.rundir))

    def run_phase_one(self):
        """
        Encapsulate all functions symbolically and for each of them
        start a parallel KLEE run.
        """

        # Generate a call graph
        self.callgraph = CallGraph(self.bitcodefile)

        # Fill a list of functions for the symbolic encapsulation
        tasks = self.callgraph.list_symbolic_encapsulable(
            removemain=not bool(self.posix4main))

        # Fill storage for errors in klee runs with all suitable functions
        for task in tasks:
            self.errorkleeruns[task] = list()

        self.qprint("Phase 1: %d of %d functions are suitable for symbolic "
                    "encapsulation" % (len(tasks), len(self.callgraph.graph)))

        # Copy the program bc before encapsulating everything symbolically
        shutil.copy2(self.program_bc, self.symmains_bc)

        # Generate one bcfile with symbolic encapsulations for each function
        for functionname in tasks:
            if functionname != "main":
                encapsulate_symbolic(self.symmains_bc, functionname)

        bar = ProgressBar(
            widgets=WIDGETS, max_value=len(tasks)) if not self.quiet else None
        self.__execute_in_parallel_threads(tasks, 1, bar)

        if not self.quiet:
            bar.finish()

        self.qprint("Phase 1: Found %d errors spread over %d functions" %
                    (self.errtotalcount, self.errfunccount))

    def run_phase_two(self):
        """
        Prepend errors from phase one to all functions and analyze with KLEE
        again, but this time with targeted search for the function calls.
        """
        self.starttimephase2 = datetime.now()

        # Prepare the bitcode file for error prepending
        shutil.copy2(self.symmains_bc, self.prepend_bc)

        # Get (caller,callee)-pairs grouped in serialized runs
        runs = self.callgraph.group_independent_calls(
            removemain=not bool(self.posix4main))

        # Store old counter to calculate progress in phase two
        olderrfunccount = self.errfunccount

        # Calculate some statistics
        qualified = sum(len(run) for run in runs)
        total = sum(len(value["calls"])
                    for key, value in self.callgraph.graph.items()
                    if key != "null function")

        self.qprint("Phase 2: %d of %d calls are suitable for error chain "
                    "propagation" % (qualified, total))

        totallyskipped = 0
        bar = ProgressBar(
            widgets=WIDGETS, max_value=qualified) if not self.quiet else None

        for run in runs:
            callees = set({callee for _, callee in run})
            for callee in callees:
                if callee in self.errorkleeruns and self.errorkleeruns[callee]:
                    prepend_error(self.prepend_bc, callee,
                                  self.errorkleeruns[callee])
            optimize_redundant_globals(self.prepend_bc)

            # all pairs inside a run can be executed in parallel
            totallyskipped += self.__execute_in_parallel_threads(run, 2, bar)

        if not self.quiet:
            bar.finish()

        self.errorchains = self.reconstruct_error_chains()
        self.chainsfrommain = (sum(1 for c in self.errorchains if (
            len(c) > 1 and path.dirname(c[0]) in self.errorkleeruns['main']))
            if 'main' in self.errorkleeruns else 0)

        self.qprint("Phase 2: %d additional KLEE analyses were started" %
                    (qualified - totallyskipped))
        self.qprint("Phase 2: %d error-chains were found through %d "
                    "previously not affected functions" %
                    (len(self.errorchains),
                     self.errfunccount - olderrfunccount))
        self.qprint("Phase 2: %d chains start in main" % self.chainsfrommain)

    def run_finalization(self):
        """
        Print a summary and write the result to the MACKE directory
        """
        self.endtime = datetime.now()

        self.qprint("Summary: %d tests were generated with %d KLEE runs" %
                    (self.testcases, self.kleecount))
        self.qprint("Summary: %d errors were detected spread over %d "
                    "functions" % (self.errtotalcount, self.errfunccount))

        # Close the json of the klee run index file
        with open(self.kleejson, 'a') as f:
            f.write("}")

        # Export all the data gathered so far to a json file
        with open(path.join(self.rundir, "result.json"), 'w') as f:
            info = OrderedDict()

            info["start"] = self.starttime.isoformat()
            info["start-phase-two"] = self.starttimephase2.isoformat()
            info["end"] = self.endtime.isoformat()
            info["testcases"] = self.testcases
            info["numberOfFunctionsWithErrors"] = self.errfunccount
            info["totalNumberOfErrors"] = self.errtotalcount
            info["functionToKleeRunWithErrorMap"] = OrderedDict(
                sorted(self.errorkleeruns.items(), key=lambda t: t[0]))
            info["klee-timeouts"] = self.timeout
            info["klee-outofmemory"] = self.outofmemory
            info["errorchains"] = self.errorchains
            info["chainsfrommain"] = self.chainsfrommain

            json.dump(info, f)

        # link the current directory as macke-last
        symlinkname = path.join(self.parentdir, "macke-last")
        try:
            remove(symlinkname)
        except OSError:
            pass
        symlink(self.rundir, symlinkname)

    def qprint(self, *args, **kwargs):
        """
        Call pythons print, if MACKE is not set to be quiet
        """
        if not self.quiet:
            print(*args, **kwargs)

    def delete_directory(self):
        """
        Delete the directory of the current run
        """
        shutil.rmtree(self.rundir, ignore_errors=True)

    def __execute_in_parallel_threads(self, run, phase, pbar):
        """
        Wrapper for executing a given list of runs with a parallel thread pool
        """

        assert phase == 1 or phase == 2

        if not self.quiet:
            # Store the state of the progressbar before running anything
            donebefore = pbar.value if pbar is not None else 0

        # Create a pool with a fixed number of parallel processes
        # Either use the configured number of thread or one for each cpu thread
        pool = Pool(THREADNUM)
        # Managed (synchronized) storage for the result of the runs
        manager = Manager()
        kleedones = manager.list()

        # Dispense the KLEE runs on the workers in the pool
        skipped = self.__put_phase_threads_into_pool(
            phase, pool, run, kleedones)

        # close the pool after all KLEE runs are registered
        pool.close()

        if not self.quiet:
            # Keeping track of the progress until everything is done
            while (len(kleedones) + skipped) != len(run):
                pbar.update(donebefore + len(kleedones) + skipped)
                sleep(0.3)
            # One final update
            pbar.update(donebefore + len(kleedones) + skipped)

        # At this point, all threads must be finished
        pool.join()

        # Store the klees with error for next runs
        self.register_passed_klee_runs(kleedones)

        return skipped

    def __put_phase_threads_into_pool(self, phase, pool, run, resultlist):
        """
        Store a given run for one phase with the required arguments
        into the thread pool
        """
        assert phase == 1 or phase == 2

        skipped = 0

        if phase == 1:
            for function in run:
                pool.apply_async(thread_phase_one, (
                    resultlist, function, self.symmains_bc,
                    self.get_next_klee_directory(
                        dict(phase=phase, function=function)),
                    self.flags_user, self.posixflags, self.posix4main
                ))
            # You cannot skip anything in phase one -> 0 skips
        elif phase == 2:
            for (caller, callee) in run:
                if callee in self.errorkleeruns:
                    pool.apply_async(thread_phase_two, (
                        resultlist, caller, callee, self.prepend_bc,
                        self.get_next_klee_directory(
                            dict(phase=phase, caller=caller, callee=callee)),
                        self.flags_user, self.posixflags, self.posix4main
                    ))
                else:
                    skipped += 1
        return skipped

    def register_passed_klee_runs(self, kleedones):
        """
        Extract and register the results of completed KLEE runs
        """
        for k in kleedones:
            self.register_passed_klee_run(k)

    def register_passed_klee_run(self, kleedone):
        """
        Extract and register the results of a completed KLEE run
        """
        # Just give it a shorter name
        k = kleedone

        # fill some counters
        self.testcases += k.testcount
        self.errfunccount += (
            k.errorcount != 0 and not self.errorkleeruns.get(k.analyzedfunc))
        self.errtotalcount += k.errorcount

        # Check for termination reasons
        if "KLEE: WATCHDOG: time expired" in k.stdoutput:
            self.timeout += 1

        if "LLVM ERROR: not enough shared memory" in k.stdoutput:
            self.outofmemory += 1

        # Create an empty entry, if function is not inside the map
        if k.analyzedfunc not in self.errorkleeruns:
            self.errorkleeruns[k.analyzedfunc] = []

        # store runs uncovering errors for phase two
        if k.errorcount != 0:
            self.errorkleeruns[k.analyzedfunc].append(k.outdir)

        # All new errors are potential heads of error chains
        for errfile in k.errfiles:
            self.errorchainheads.add(errfile)

        # store all error chains
        for new, old in k.chained:
            self.errorchains[new] = old
            # the old error is no longer a head
            if old in self.errorchainheads:
                self.errorchainheads.remove(old)

    def reconstruct_error_chains(self):
        """
        Unfold the compact internal representation to a list of error chains
        """
        result = []

        for head in self.errorchainheads:
            chain = [head]
            probe = head
            while probe in self.errorchains:
                probe = self.errorchains[probe]
                chain.append(probe)
            if len(chain) > 1:
                result.append(chain)

        # Longest chains are reported first
        result.sort(key=lambda x: (len(x), x[0]), reverse=True)
        return result


def thread_phase_one(
        resultlist, functionname, symmains_bc, outdir,
        flags, posixflags, posix4main):
    """
    This function is executed by the parallel processes in phase one
    """
    # Just run KLEE on it
    resultlist.append(execute_klee(
        symmains_bc, functionname, outdir, flags, posixflags, posix4main))


def thread_phase_two(
        resultlist, caller, callee, prepended_bc, outdir,
        flags, posixflags, posix4main):
    """
    This function is executed by the parallel processes in phase two
    """
    # And run klee on it
    resultlist.append(execute_klee_targeted_search(
        prepended_bc, caller, callee, outdir, flags, posixflags, posix4main))
