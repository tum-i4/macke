"""
Core class for MACKE execution.
Contains methods for both phases and some analysis
"""

import json
import shutil
import sys
from collections import OrderedDict
from datetime import datetime
from multiprocessing import Manager, Pool
from os import makedirs, path, remove, symlink
from time import sleep

from progressbar import ProgressBar, widgets

from .CallGraph import CallGraph
from .config import (CONFIGFILE, THREADNUM, get_current_git_hash,
                     get_klee_git_hash, get_llvm_opt_git_hash)
from .ErrorRegistry import ErrorRegistry
from .llvm_wrapper import (encapsulate_symbolic, optimize_redundant_globals,
                           prepend_error_from_ktest)
from .threads import thread_phase_one, thread_fuzz_phase_one, thread_phase_two

from .Fuzzer import FuzzManager

# The widgets used by the process bar
WIDGETS = [
    widgets.Percentage(),
    ' (', widgets.SimpleProgress(), ')',
    ' ', widgets.Bar("="),
    ' ', widgets.Timer(),
    ' ', widgets.ETA(),
]


class Macke:
    """
    Main container for all steps of the MACKE analysis
    """

    def __init__(self, bitcodefile, comment="",
                 parentdir="/tmp/macke", quiet=False,
                 flags_user=None, posixflags=None, posix4main=None,
                 exclude_known_from_phase_two=True, use_fuzzer=False,
                 fuzztime=1, stop_fuzz_when_done=False, generate_smart_fuzz_input=True,
                 fuzzbc=None, fuzz_input_maxlen=32):
        # Only accept valid files and directory
        assert path.isfile(bitcodefile)

        if fuzzbc is None:
            fuzzbc = bitcodefile
        else:
            assert path.isfile(fuzzbc)

        # store the path to the analyzed bitcode file
        self.bitcodefile = bitcodefile

        # Store information from command line
        self.comment = comment
        self.flags_user = flags_user if flags_user is not None else []
        self.posixflags = posixflags if posixflags is not None else []
        self.posix4main = posix4main if posix4main is not None else []
        self.exclude_known_from_phase_two = exclude_known_from_phase_two

        # generate name of directory with all run results
        self.starttime = datetime.now()
        newdirname = self.starttime.strftime("%Y-%m-%d-%H-%M-%S")
        self.rundir = path.join(parentdir, newdirname)
        self.parentdir = parentdir

        # Generate the path for the bitcode directory
        self.bcdir = path.join(self.rundir, "bitcode")

        # Generate the filename for the copy of the program
        self.program_bc = path.join(self.bcdir, "program.bc")
        self.symmains_bc = path.join(self.bcdir, "symmains.bc")

        # Generate the directory containing all klee runs
        self.kleedir = path.join(self.rundir, "klee")

        # Filename, where the index of the klee runs is stored
        self.kleejson = path.join(self.rundir, "klee.json")

        # Internal counter for the number of klee runs
        self.kleecount = 0

        # Initialize some statistic counter
        self.testcases = 0

        # Some attributes, that are filled later
        self.callgraph = None
        self.starttimephase2 = None
        self.endtime = None
        self.errorregistry = ErrorRegistry()

        # Setting quiet == True suppress all outputs
        self.quiet = quiet

        # Setting the fuzzdir
        self.use_fuzzer = use_fuzzer
        if use_fuzzer:
            self.fuzz_program_bc = path.join(self.bcdir, "fuzz.bc")
            self.fuzz_input_maxlen = fuzz_input_maxlen
            self.fuzztime = fuzztime
            self.fuzzdir = path.join(self.rundir, "fuzzer")
            self.fuzzbc = fuzzbc
            self.fuzz_smartinput = generate_smart_fuzz_input
            self.fuzz_stop_when_done = stop_fuzz_when_done


    def save_options(self, to):
        with open(to, 'w') as file:
            options = OrderedDict()

            options["exclude_known"] = self.exclude_known_from_phase_two
            options["klee-max-time"] = int(next(filter(lambda f : f.startswith("--max-time="), self.flags_user))[len("--max-time="):])
            options["use_fuzzer"] = self.use_fuzzer
            if self.use_fuzzer:
                options["fuzz-time"] = self.fuzztime
                options["fuzz-stop-when-done"] = self.fuzz_stop_when_done
                options["fuzz-smart-input"] = self.fuzz_smartinput
                options["fuzz-input-maxlen"] = self.fuzz_input_maxlen

            json.dump(options, file)

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
        with open(self.kleejson, 'a') as file:
            # Prepend separator for all but the first entry
            if self.kleecount != 1:
                file.write(", ")
            file.write(json.dumps(outjson)[1:-1])

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
        with open(path.join(self.rundir, "info.json"), 'w') as file:
            info = OrderedDict()
            info["macke-git-version-hash"] = get_current_git_hash()
            info["llvm-opt-git-version-hash"] = get_llvm_opt_git_hash()
            info["klee-git-version-hash"] = get_klee_git_hash()
            info["analyzed-bitcodefile"] = path.abspath(self.bitcodefile)
            if self.use_fuzzer:
                info["fuzzer-bitcodefile"] = path.abspath(self.fuzzbc)
            info["run-argv"] = sys.argv
            info["comment"] = self.comment
            json.dump(info, file)

        self.save_options(path.join(self.rundir, "options.json"))

        # Initialize a file for klee directory mapping
        with open(self.kleejson, 'w') as file:
            file.write("{")


        # Initialize fuzzing
        if self.use_fuzzer:
            # copy the unmodified bitcode file (fuzzer one)
            shutil.copy2(self.fuzzbc, self.fuzz_program_bc)
            builddir = path.join(self.fuzzdir, "build")
            makedirs(builddir)
            self.create_macke_last_symlink()
            self.fuzz_manager = FuzzManager(self.fuzz_program_bc, self.fuzzdir, builddir, None, self.fuzz_stop_when_done, self.fuzz_smartinput, self.fuzz_input_maxlen, self.qprint)

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

        self.qprint("Phase 1: %d of %d functions are suitable for symbolic "
                    "encapsulation" % (len(tasks), len(self.callgraph.graph)))

        self.count_phase1_functions = len(tasks)
        self.count_functions = len(self.callgraph.graph)

        self.qprint("Phase 1: Adding new entry points ...", end="", flush=True)

        # Copy the program bc before encapsulating everything symbolically
        shutil.copy2(self.program_bc, self.symmains_bc)

        # Generate one bcfile with symbolic encapsulations for each function
        for functionname in tasks:
            if functionname != "main":
                encapsulate_symbolic(self.symmains_bc, functionname)
        self.qprint(" done")


        if self.use_fuzzer:
            tasks = self.fuzz_manager.list_suitable_drivers()
            self.count_phase1_functions = len(tasks)
            self.qprint("Phase 1 - with fuzzing: %d of %d functions are suitable for fuzzing" 
                         % (len(tasks), len(self.callgraph.graph)))

        if self.use_fuzzer:
            self.qprint("Phase 1: Performing afl-fuzz runs ...")
        else:
            self.qprint("Phase 1: Performing KLEE runs ...")

        pbar = ProgressBar(
            widgets=WIDGETS, max_value=len(tasks)) if not self.quiet else None

        self.starttimephase1 = datetime.now()
        self.__execute_in_parallel_threads(tasks, 1, pbar)

        if not self.quiet:
            pbar.finish()

        self.qprint("Phase 1: Found %d unique errors(total: %d) spread over %d functions" %
                    (self.errorregistry.count_unique_errors(),
                     self.errorregistry.errorcounter,
                     self.errorregistry.count_functions_with_errors()))

        self.phase_one_summary = (self.errorregistry.count_unique_errors(), self.errorregistry.errorcounter, self.errorregistry.count_functions_with_errors())

    def run_phase_two(self):
        """
        Prepend errors from phase one to all functions and analyze with KLEE
        again, but this time with targeted search for the function calls.
        """
        self.starttimephase2 = datetime.now()

        # Get (caller,callee)-pairs grouped in serialized runs
        runs = self.callgraph.group_independent_calls(
            removemain=not bool(self.posix4main))

        # Calculate some statistics
        qualified = sum(len(run) for run in runs)
        total = sum(len(value["calls"])
                    for key, value in self.callgraph.graph.items()
                    if key != "null function")

        self.qprint("Phase 2: %d of %d calls are suitable for error chain "
                    "propagation" % (qualified, total))

        self.qprint("Phase 2: Performing KLEE runs with targeted search "
                    "if needed ...")
        totallyskipped = 0
        pbar = ProgressBar(
            widgets=WIDGETS, max_value=qualified) if not self.quiet else None

        for run in runs:
            # all pairs inside a run can be executed in parallel
            totallyskipped += self.__execute_in_parallel_threads(run, 2, pbar)

        if not self.quiet:
            pbar.finish()

        self.qprint("Phase 2: %d additional KLEE analyzes propagate %d "
                    "errors" % (qualified - totallyskipped,
                                self.errorregistry.mackerrorcounter))
        self.phase2_runs = qualified - totallyskipped
        self.propagated = self.errorregistry.mackerrorcounter

    def run_finalization(self):
        """
        Print a summary and write the result to the MACKE directory
        """
        self.endtime = datetime.now()

        self.qprint("Summary: %d tests were generated with %d KLEE runs" %
                    (self.testcases, self.kleecount))
        self.qprint("Summary: %d unique errors (in total %d) were detected spread over %d "
                    "functions" % (
                        self.errorregistry.count_unique_errors(),
                        self.errorregistry.errorcounter,
                        self.errorregistry.count_functions_with_errors()))

        # Close the json of the klee run index file
        with open(self.kleejson, 'a') as file:
            file.write("}")

        with open(path.join(self.rundir, "summary.json"), 'w') as file:
            info = OrderedDict()

            p1_uniq, p1_errc, p1_errf = self.phase_one_summary
            info["num-functions"] = self.count_functions
            info["phase-one-functions"] = self.count_phase1_functions
            info["phase-one-unique-errors"] = p1_uniq
            info["phase-one-error-count"] = p1_errc
            info["phase-one-count-error-funcs"] = p1_errf

            info["phase-two-runs"] = self.phase2_runs
            info["phase-two-propagated"] = self.propagated

            info["total-unique-errors"] = self.errorregistry.count_unique_errors()
            info["total-error-count"] = self.errorregistry.errorcounter
            info["total-count-error-funcs"] = self.errorregistry.count_functions_with_errors()

            json.dump(info, file)


        # Export all the data gathered so far to a json file
        with open(path.join(self.rundir, "timing.json"), 'w') as file:
            info = OrderedDict()

            info["start"] = self.starttime.isoformat()
            info["start-phase-one"] = self.starttimephase1.isoformat()
            info["start-phase-two"] = self.starttimephase2.isoformat()
            info["end"] = self.endtime.isoformat()

            json.dump(info, file)

        self.create_macke_last_symlink()

    def create_macke_last_symlink(self):
        """
        Create a symbolic link "macke-last" pointing the current macke outdir
        """

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
                if self.use_fuzzer:
                    pool.apply_async(thread_fuzz_phase_one, (self.fuzz_manager, resultlist, function, path.join(self.fuzzdir, "fuzz_out_" + function), self.fuzztime))
                else:
                    pool.apply_async(thread_phase_one, (
                        resultlist, function, self.symmains_bc,
                        self.get_next_klee_directory(
                            dict(phase=phase, bcfile=self.symmains_bc,
                                 function=function)),
                        self.flags_user, self.posixflags, self.posix4main
                    ))
            # You cannot skip anything in phase one -> 0 skips
        elif phase == 2:
            for (caller, callee) in run:
                kteststoprepend = (
                    self.errorregistry.to_prepend_in_phase_two(
                        caller, callee, self.exclude_known_from_phase_two))

                if kteststoprepend:
                    prepended_bcfile = get_chain_segment_bcname(
                        self.bcdir, caller, callee)
                    prepend_error_from_ktest(
                        self.symmains_bc, callee, kteststoprepend,
                        prepended_bcfile)
                    optimize_redundant_globals(prepended_bcfile)

                    pool.apply_async(thread_phase_two, (
                        resultlist, caller, callee, prepended_bcfile,
                        self.get_next_klee_directory(
                            dict(phase=phase, bcfile=prepended_bcfile,
                                 caller=caller, callee=callee)),
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
        # Put all found errors into the error registry
        self.errorregistry.create_from_dir(
            kleedone.outdir, kleedone.analyzedfunc)

        # Count the total number of test cases
        self.testcases += kleedone.testcount


def get_chain_segment_bcname(bcdir, caller, callee):
    """
    Build the path and name of a bc-file with prepended errors of callee
    """
    # "-" is a good separator, because "-" is not allowed in c function names
    return path.join(bcdir, "chain-%s-%s.bc" % (caller, callee))
